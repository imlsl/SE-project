import asyncio
import logging
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv


env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(env_path)

BLENDER_URL = os.getenv("BLENDER_URL")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_BLEND = PROJECT_ROOT / "SCGS" / "assets" / "ICity start.blend"

logger = logging.getLogger(__name__)


class BlenderService:
    TASKS = {}

    @staticmethod
    async def trigger_scene_generation(parameters: dict) -> str:
        """Start a Blender background generation task."""
        logger.info("Triggering Blender generation with parameters: %s", parameters)
        task_id = str(uuid.uuid4())
        output_path = os.path.abspath(f"data/exports/output_{task_id}.blend")
        BlenderService.TASKS[task_id] = {
            "status": "processing",
            "parameters": parameters,
            "error": "",
            "output_path": output_path,
        }
        asyncio.create_task(BlenderService._run_blender_task(task_id, parameters))
        return task_id

    @staticmethod
    async def _run_blender_task(task_id: str, parameters: dict):
        blender_executable = BLENDER_URL

        if not blender_executable or not os.path.exists(blender_executable):
            error = f"Blender executable not found at: {blender_executable}"
            logger.error(error)
            BlenderService._mark_failed(task_id, error)
            return

        os.makedirs("data/exports", exist_ok=True)
        output_blend = os.path.abspath(f"data/exports/output_{task_id}.blend")
        BlenderService.TASKS[task_id]["output_path"] = output_blend

        raw_instruction = str(parameters.get("instruction") or parameters.get("city_name") or "")
        instruction_value = BlenderService._normalize_instruction(raw_instruction)
        style_value = str(parameters.get("style", "default"))
        scale_value = str(parameters.get("scale", 1.0))

        script_content = f"""
import bpy
import os
import sys
import traceback

project_root = {repr(str(PROJECT_ROOT))}
base_blend = {repr(str(BASE_BLEND))}
output_blend = {repr(output_blend)}
instruction_param = {repr(instruction_value)}
style_param = {repr(style_value)}
scale_param = {repr(scale_value)}

try:
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    if os.path.exists(base_blend):
        bpy.ops.wm.open_mainfile(filepath=base_blend)
        print(f"Loaded base scene: {{base_blend}}")
    else:
        print(f"Base scene not found, continuing with current scene: {{base_blend}}")

    try:
        bpy.ops.preferences.addon_enable(module="SCGS")
        print("SCGS addon enabled")
    except Exception as addon_error:
        print(f"SCGS addon enable failed: {{addon_error}}")

    instruction = instruction_param or "生成风格{{}}比例{{}}".format(style_param, scale_param)
    if hasattr(bpy.context.scene, "sna_ai_instruction"):
        bpy.context.scene.sna_ai_instruction = instruction
    if hasattr(bpy.context.scene, "sna_template_selection") and instruction.strip().isdigit():
        bpy.context.scene.sna_template_selection = instruction.strip()

    if instruction.strip().isdigit() and hasattr(bpy.ops.sna, "apply_template"):
        result = bpy.ops.sna.apply_template()
        print(f"Apply template result: {{result}}")
        if "CANCELLED" in result:
            raise RuntimeError(f"Template operator cancelled for instruction: {{instruction}}")
    elif hasattr(bpy.ops.sna, "process_ai_instruction"):
        before_objects = len(bpy.data.objects)
        result = bpy.ops.sna.process_ai_instruction()
        after_objects = len(bpy.data.objects)
        print(f"AI instruction result: {{result}}; objects before={{before_objects}}, after={{after_objects}}")
        if "CANCELLED" in result:
            raise RuntimeError(f"AI instruction operator cancelled for instruction: {{instruction}}")
    elif hasattr(bpy.ops.sna, "start_5209e"):
        result = bpy.ops.sna.start_5209e()
        print(f"Start generation result: {{result}}")
    else:
        raise RuntimeError("SCGS generation operator not found")

    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"Saved blend file: {{output_blend}}")
    sys.exit(0)
except Exception as exc:
    print(f"Error during plugin execution: {{exc}}")
    traceback.print_exc()
    sys.exit(2)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            def run_blender():
                return subprocess.run(
                    [blender_executable, "-b", "-P", script_path],
                    capture_output=True,
                    text=False,
                )

            process = await asyncio.to_thread(run_blender)
            stdout_text = process.stdout.decode("utf-8", errors="ignore") if process.stdout else ""
            stderr_text = process.stderr.decode("utf-8", errors="ignore") if process.stderr else ""

            if process.returncode == 0 and os.path.exists(output_blend):
                logger.info("Task %s completed. Saved to %s", task_id, output_blend)
                BlenderService.TASKS[task_id]["status"] = "completed"
                BlenderService.TASKS[task_id]["stdout"] = stdout_text[-2000:]
                return

            error = (stderr_text + "\n" + stdout_text).strip() or f"Blender exited with code {process.returncode}"
            logger.error("Task %s failed: %s", task_id, error)
            BlenderService._mark_failed(task_id, error[-3000:])
        except Exception as exc:
            logger.error("Failed to start Blender process: %s", exc, exc_info=True)
            BlenderService._mark_failed(task_id, str(exc))
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

    @staticmethod
    async def check_generation_status(task_id: str) -> dict:
        """Return Blender generation task status."""
        logger.info("Checking status for task: %s", task_id)
        task = BlenderService.TASKS.get(task_id)
        output_blend = task.get("output_path") if task else f"data/exports/output_{task_id}.blend"

        if task and task.get("status") == "failed":
            return {
                "task_id": task_id,
                "status": "failed",
                "error": task.get("error", "Blender generation failed"),
            }

        if os.path.exists(output_blend):
            return {
                "task_id": task_id,
                "status": "completed",
                "download_url": f"/blender/download/{task_id}",
            }

        return {
            "task_id": task_id,
            "status": "processing",
        }

    @staticmethod
    def _mark_failed(task_id: str, error: str):
        task = BlenderService.TASKS.setdefault(task_id, {})
        task["status"] = "failed"
        task["error"] = error

    @staticmethod
    def _normalize_instruction(instruction: str) -> str:
        """Convert loose UI text into the config grammar supported by the SCGS plugin."""
        text = (instruction or "").strip()
        if not text:
            return ""

        if text.isdigit():
            return text

        if re.search(r"(树木|tree)\s*[：:=,，]?\s*[1-4]", text, re.IGNORECASE):
            return text
        if re.search(r"(道路|road)\s*[：:=,，]?\s*[1-4]", text, re.IGNORECASE):
            return text
        if re.search(r"(座椅|bench)\s*[：:=,，]?\s*[1-4]", text, re.IGNORECASE):
            return text

        lowered = text.lower()
        if any(keyword in lowered for keyword in ["模板0", "template0", "现代", "科技", "路灯", "lamp", "light"]):
            return "树木1，道路2，座椅1"
        if any(keyword in lowered for keyword in ["模板1", "template1", "古典", "classic"]):
            return "树木2，道路1，座椅2"
        if any(keyword in lowered for keyword in ["模板2", "template2", "绿色", "生态", "绿化", "步道", "green", "eco"]):
            return "树木3，道路3，座椅3"
        if any(keyword in lowered for keyword in ["模板3", "template3", "工业", "industrial"]):
            return "树木1，道路4，座椅1"
        if any(keyword in lowered for keyword in ["模板4", "template4", "台湾", "taiwan"]):
            return "树木4，道路2，座椅4"

        numbers = re.findall(r"[1-4]", text)
        if len(numbers) >= 3:
            return f"树木{numbers[0]}，道路{numbers[1]}，座椅{numbers[2]}"

        return text
