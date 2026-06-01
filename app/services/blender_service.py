import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BACKEND_ROOT / ".env"
DATA_DIR = BACKEND_ROOT / "data"
EXPORT_DIR = DATA_DIR / "exports"
TASKS_FILE = DATA_DIR / "blender_tasks.json"

load_dotenv(ENV_PATH)

logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    return value or default


class BlenderService:
    """后端与 Blender 中已安装的 SCGS 插件之间的桥接服务。

    这里默认调用用户 Blender 里的真实 SCGS 插件，不依赖仓库中的样例插件目录。
    如真实插件的模块名或算子名不同，仍可通过 .env 覆盖默认配置。
    """

    TASKS: dict[str, dict[str, Any]] = {}
    _loaded = False

    @classmethod
    def config(cls) -> dict[str, str]:
        return {
            "blender_url": _env("BLENDER_URL"),
            "plugin_module": _env("BLENDER_PLUGIN_MODULE", "SCGS"),
            "generate_operator": _env("BLENDER_GENERATE_OPERATOR", "sna.city_generation"),
            "edit_operator": _env("BLENDER_EDIT_OPERATOR", "sna.city_edit"),
            "operator_filter": _env("BLENDER_OPERATOR_FILTER", "sna"),
        }

    @classmethod
    async def diagnostics(cls) -> dict[str, Any]:
        """检查 Blender、SCGS 插件启用状态，以及可用的 bpy.ops 算子。"""
        cfg = cls.config()
        blender_executable = cfg["blender_url"]
        result: dict[str, Any] = {
            "config": cfg,
            "blender_found": bool(blender_executable and Path(blender_executable).exists()),
            "blender_started": False,
            "plugin_enabled": False,
            "addons": [],
            "operators": [],
            "warnings": [],
            "error": "",
            "stdout_tail": "",
            "stderr_tail": "",
        }

        if not result["blender_found"]:
            result["error"] = f"未找到 Blender 可执行文件: {blender_executable or '(BLENDER_URL 为空)'}"
            cls._save_last_diagnostics(result)
            return result

        script = cls._diagnostics_script(cfg)
        process = await cls._run_script(script, blender_executable)
        result["stdout_tail"] = process["stdout"][-4000:]
        result["stderr_tail"] = process["stderr"][-4000:]

        parsed = cls._extract_result_json(process["stdout"])
        if parsed:
            result.update(parsed)
            result["blender_started"] = process["returncode"] == 0 or parsed.get("blender_started", False)
        else:
            result["blender_started"] = process["returncode"] == 0
            result["error"] = (process["stderr"] or process["stdout"] or "Unable to parse Blender diagnostics output")[-2000:]

        cls._save_last_diagnostics(result)
        return result

    @classmethod
    async def trigger_scene_generation(cls, parameters: dict[str, Any]) -> str:
        """启动后台生成任务，并持久化任务状态。"""
        cls._ensure_loaded()
        task_id = str(uuid.uuid4())
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = EXPORT_DIR / f"output_{task_id}.blend"
        task = {
            "task_id": task_id,
            "status": "processing",
            "parameters": cls._standardize_parameters(parameters),
            "warnings": [],
            "error": "",
            "stdout": "",
            "stderr": "",
            "output_path": str(output_path.resolve()),
            "download_url": "",
            "created_at": cls._now(),
            "updated_at": cls._now(),
        }
        cls.TASKS[task_id] = task
        cls._save_tasks()
        asyncio.create_task(cls._run_blender_task(task_id))
        return task_id

    @classmethod
    async def check_generation_status(cls, task_id: str) -> dict[str, Any]:
        cls._ensure_loaded()
        task = cls.TASKS.get(task_id)
        if not task:
            output_path = EXPORT_DIR / f"output_{task_id}.blend"
            if output_path.exists():
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "download_url": f"/blender/download/{task_id}",
                    "output_path": str(output_path.resolve()),
                }
            return {"task_id": task_id, "status": "not_found", "error": "Task not found"}

        if task.get("status") == "processing" and Path(task.get("output_path", "")).exists():
            task["status"] = "completed"
            task["download_url"] = f"/blender/download/{task_id}"
            task["updated_at"] = cls._now()
            cls._save_tasks()

        return {
            "task_id": task_id,
            "status": task.get("status", "processing"),
            "download_url": task.get("download_url", ""),
            "output_path": task.get("output_path", ""),
            "warnings": task.get("warnings", []),
            "error": task.get("error", ""),
            "stdout": task.get("stdout", ""),
            "stderr": task.get("stderr", ""),
            "created_at": task.get("created_at", ""),
            "updated_at": task.get("updated_at", ""),
        }

    @classmethod
    def output_path_for(cls, task_id: str) -> Path:
        cls._ensure_loaded()
        task = cls.TASKS.get(task_id, {})
        return Path(task.get("output_path") or EXPORT_DIR / f"output_{task_id}.blend")

    @classmethod
    async def _run_blender_task(cls, task_id: str) -> None:
        cls._ensure_loaded()
        task = cls.TASKS[task_id]
        cfg = cls.config()
        blender_executable = cfg["blender_url"]

        if not blender_executable or not Path(blender_executable).exists():
            cls._mark_failed(task_id, f"Blender executable not found: {blender_executable or '(empty BLENDER_URL)'}")
            return

        if not cfg["generate_operator"]:
            cls._mark_failed(
                task_id,
                "未配置 BLENDER_GENERATE_OPERATOR。默认应为 sna.city_generation，可调用 /blender/diagnostics 查看候选算子。",
            )
            return

        script = cls._generation_script(cfg, task["parameters"], task["output_path"])
        process = await cls._run_script(script, blender_executable)
        stdout_text = process["stdout"]
        stderr_text = process["stderr"]

        task["stdout"] = stdout_text[-3000:]
        task["stderr"] = stderr_text[-3000:]
        task["updated_at"] = cls._now()

        parsed = cls._extract_result_json(stdout_text)
        if parsed:
            task["warnings"] = parsed.get("warnings", task.get("warnings", []))

        if process["returncode"] == 0 and Path(task["output_path"]).exists():
            task["status"] = "completed"
            task["download_url"] = f"/blender/download/{task_id}"
            task["error"] = ""
            cls._save_tasks()
            return

        error = ""
        if parsed and parsed.get("error"):
            error = parsed["error"]
        else:
            error = (stderr_text + "\n" + stdout_text).strip() or f"Blender exited with code {process['returncode']}"
        cls._mark_failed(task_id, error[-3000:], stdout_text, stderr_text)

    @classmethod
    async def _run_script(cls, script_content: str, blender_executable: str) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            def run_blender() -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [blender_executable, "-b", "-P", script_path],
                    capture_output=True,
                    text=False,
                )

            process = await asyncio.to_thread(run_blender)
            return {
                "returncode": process.returncode,
                "stdout": process.stdout.decode("utf-8", errors="replace") if process.stdout else "",
                "stderr": process.stderr.decode("utf-8", errors="replace") if process.stderr else "",
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("运行 Blender 脚本失败")
            return {"returncode": 99, "stdout": "", "stderr": str(exc)}
        finally:
            try:
                os.remove(script_path)
            except OSError:
                pass

    @staticmethod
    def _diagnostics_script(cfg: dict[str, str]) -> str:
        return f"""
import json
import traceback

cfg = json.loads({json.dumps(json.dumps(cfg, ensure_ascii=False), ensure_ascii=False)})
result = {{
    "blender_started": True,
    "plugin_enabled": False,
    "addons": [],
    "operators": [],
    "warnings": [],
    "error": "",
}}

try:
    import bpy
    import addon_utils

    result["addons"] = sorted([
        getattr(addon, "__name__", "")
        for addon in addon_utils.modules()
        if getattr(addon, "__name__", "")
    ])[:500]

    module = cfg.get("plugin_module", "")
    if module:
        try:
            bpy.ops.preferences.addon_enable(module=module)
            result["plugin_enabled"] = True
        except Exception as exc:
            result["warnings"].append(f"SCGS 插件启用失败（模块 {{module}}）: {{exc}}")
    else:
        result["warnings"].append("BLENDER_PLUGIN_MODULE 为空，诊断仅列出当前 Blender 可见算子。")

    search_terms = [
        cfg.get("operator_filter", ""),
        cfg.get("plugin_module", ""),
        cfg.get("generate_operator", "").split(".")[0],
        cfg.get("edit_operator", "").split(".")[0],
    ]
    search_terms = [term.lower() for term in search_terms if term]

    def op_matches(full_name):
        if not search_terms:
            return True
        for term in search_terms:
            if full_name.startswith(term + "."):
                return True
            if len(term) > 4 and term in full_name:
                return True
        return False

    operators = []
    for namespace in dir(bpy.ops):
        if namespace.startswith("_"):
            continue
        namespace_obj = getattr(bpy.ops, namespace)
        for op_name in dir(namespace_obj):
            if op_name.startswith("_"):
                continue
            full_name = f"{{namespace}}.{{op_name}}"
            haystack = full_name.lower()
            if op_matches(haystack):
                operators.append(full_name)
    result["operators"] = sorted(set(operators))[:500]
except Exception as exc:
    result["error"] = str(exc)
    result["traceback"] = traceback.format_exc()

print("BLENDER_BRIDGE_RESULT=" + json.dumps(result, ensure_ascii=False))
"""

    @staticmethod
    def _generation_script(cfg: dict[str, str], params: dict[str, Any], output_path: str) -> str:
        return f"""
import json
import os
import traceback

cfg = json.loads({json.dumps(json.dumps(cfg, ensure_ascii=False), ensure_ascii=False)})
params = json.loads({json.dumps(json.dumps(params, ensure_ascii=False), ensure_ascii=False)})
output_path = {json.dumps(output_path)}
result = {{"warnings": [], "error": ""}}

def set_if_exists(owner, name, value):
    if value in (None, ""):
        return False
    if hasattr(owner, name):
        try:
            setattr(owner, name, value)
            return True
        except Exception as exc:
            result["warnings"].append(f"Could not set {{name}}: {{exc}}")
    return False

def call_operator(operator_name):
    if not operator_name or "." not in operator_name:
        raise RuntimeError("算子名称无效，应为 namespace.operator 格式")
    namespace, op_name = operator_name.split(".", 1)
    namespace_obj = getattr(bpy.ops, namespace, None)
    if namespace_obj is None:
        raise RuntimeError(f"未找到算子命名空间: {{namespace}}")
    operator = getattr(namespace_obj, op_name, None)
    if operator is None:
        raise RuntimeError(f"未找到算子: {{operator_name}}")
    return operator()

def apply_selected_asset(scene, asset):
    plugin_name = str(asset.get("plugin_name") or asset.get("name") or "").strip()
    plugin_type = str(asset.get("plugin_type") or asset.get("type") or "").strip()
    material_target = str(asset.get("material_target") or "Road").strip()
    if not plugin_name or not plugin_type:
        result["warnings"].append(f"Skipped asset with missing plugin fields: {{asset}}")
        return

    if plugin_type == "Texture":
        set_if_exists(scene, "sna_street_asset_type", "Texture")
        set_if_exists(scene, "sna_road_materials_type_", material_target)
        for op_name in ["sna.material_filter_f04c3", "sna.road_materials_filter_6a3ec"]:
            try:
                call_operator(op_name)
            except Exception as exc:
                result["warnings"].append(f"Asset filter {{op_name}} failed for {{plugin_name}}: {{exc}}")
        if not set_if_exists(scene, "sna_road_materials_browser", plugin_name):
            result["warnings"].append(f"Road material property unavailable for {{plugin_name}}")
            return
    else:
        set_if_exists(scene, "sna_street_asset_type", plugin_type)
        try:
            call_operator("sna.filter_street_assets_c5c0e")
        except Exception as exc:
            result["warnings"].append(f"Asset filter failed for {{plugin_name}}: {{exc}}")
        if not set_if_exists(scene, "sna_street_asset_browser", plugin_name):
            result["warnings"].append(f"Street asset property unavailable for {{plugin_name}}")
            return

    try:
        applied = call_operator("sna.road_apply_5c3ab")
        result.setdefault("applied_assets", []).append(plugin_name)
        if "CANCELLED" in str(applied):
            result["warnings"].append(f"Asset apply cancelled for {{plugin_name}}: {{applied}}")
    except Exception as exc:
        result["warnings"].append(f"Could not apply asset {{plugin_name}}: {{exc}}")

try:
    import bpy

    module = cfg.get("plugin_module", "")
    if module:
        try:
            bpy.ops.preferences.addon_enable(module=module)
        except Exception as exc:
            result["warnings"].append(f"SCGS 插件启用失败（模块 {{module}}）: {{exc}}")
    else:
        result["warnings"].append("BLENDER_PLUGIN_MODULE 为空，将使用当前 Blender 已加载状态。")

    scene = bpy.context.scene
    if params.get("manual_vertices") and params.get("manual_edges"):
        params["road_type"] = "4"

    param_to_props = {{
        "description": ["description", "city_description", "sna_description", "prompt", "instruction"],
        "instruction": ["instruction", "ai_instruction", "sna_ai_instruction", "edit_instruction"],
        "template_id": ["template_id", "template", "sna_template_selection"],
        "road_type": ["road_type", "sna_road_type"],
        "weather": ["weather", "sna_weather"],
        "manual_vertices": ["manual_vertices", "sna_manual_vertices"],
        "manual_edges": ["manual_edges", "sna_manual_edges"],
        "style": ["style", "city_style"],
        "scale": ["scale", "city_scale"],
    }}
    unsupported = []
    for key, prop_names in param_to_props.items():
        value = params.get(key)
        if value in (None, ""):
            continue
        if not any(set_if_exists(scene, prop_name, value) for prop_name in prop_names):
            unsupported.append(key)
    if unsupported:
        result["warnings"].append("以下参数未找到对应的场景属性: " + ", ".join(unsupported))

    operator_result = call_operator(cfg.get("generate_operator", ""))
    result["operator_result"] = list(operator_result) if isinstance(operator_result, set) else str(operator_result)
    if "CANCELLED" in result["operator_result"]:
        raise RuntimeError(f"生成算子已取消: {{result['operator_result']}}")

    for asset in params.get("selected_assets") or []:
        try:
            apply_selected_asset(scene, asset)
        except Exception as exc:
            result["warnings"].append(f"Asset application failed: {{asset}}: {{exc}}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_path)
    result["output_path"] = output_path
except Exception as exc:
    result["error"] = str(exc)
    result["traceback"] = traceback.format_exc()

print("BLENDER_BRIDGE_RESULT=" + json.dumps(result, ensure_ascii=False))
if result["error"]:
    raise SystemExit(2)
"""

    @staticmethod
    def _standardize_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
        description = parameters.get("description") or parameters.get("instruction") or parameters.get("city_name") or ""
        template_id = parameters.get("template_id")
        if template_id in (None, "") and str(description).strip().isdigit():
            template_id = str(description).strip()
        manual_vertices = str(parameters.get("manual_vertices") or "")
        manual_edges = str(parameters.get("manual_edges") or "")
        road_type = str(parameters.get("road_type") or "")
        if manual_vertices and manual_edges:
            road_type = "4"

        return {
            "description": str(description or ""),
            "instruction": str(parameters.get("instruction") or ""),
            "template_id": str(template_id or ""),
            "road_type": road_type,
            "weather": str(parameters.get("weather") or ""),
            "manual_vertices": manual_vertices,
            "manual_edges": manual_edges,
            "layout_points": parameters.get("layout_points") or [],
            "selected_assets": parameters.get("selected_assets") or [],
            "style": str(parameters.get("style") or "default"),
            "scale": parameters.get("scale", 1.0),
        }

    @classmethod
    def _mark_failed(cls, task_id: str, error: str, stdout: str = "", stderr: str = "") -> None:
        cls._ensure_loaded()
        task = cls.TASKS.setdefault(task_id, {"task_id": task_id, "created_at": cls._now()})
        task["status"] = "failed"
        task["error"] = error
        if stdout:
            task["stdout"] = stdout[-3000:]
        if stderr:
            task["stderr"] = stderr[-3000:]
        task["updated_at"] = cls._now()
        cls._save_tasks()

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._loaded:
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        if TASKS_FILE.exists():
            try:
                cls.TASKS = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            except Exception:
                logger.exception("读取 Blender 任务持久化文件失败")
                cls.TASKS = {}
        cls._loaded = True

    @classmethod
    def _save_tasks(cls) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.write_text(json.dumps(cls.TASKS, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _save_last_diagnostics(result: dict[str, Any]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "blender_diagnostics.json").write_text(
            json.dumps({**result, "checked_at": BlenderService._now()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _extract_result_json(stdout_text: str) -> dict[str, Any] | None:
        marker = "BLENDER_BRIDGE_RESULT="
        for line in reversed(stdout_text.splitlines()):
            if line.startswith(marker):
                try:
                    return json.loads(line[len(marker):])
                except json.JSONDecodeError:
                    return None
        return None

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"
