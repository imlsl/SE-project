import logging
import asyncio
import os
import uuid
import tempfile
import subprocess
from dotenv import load_dotenv

# 加载 .env 文件，使用绝对路径确保能找到
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
load_dotenv(env_path)

# 在 .env 中替换为你电脑上实际的 Blender 可执行文件路径
# 例如: BLENDER_URL="D:/Blender/Blender Foundation/Blender 4.1/blender.exe"
BLENDER_URL = os.getenv("BLENDER_URL")

logger = logging.getLogger(__name__)

class BlenderService:
    @staticmethod
    async def trigger_scene_generation(parameters: dict) -> str:
        """
        与Blender城城市生成插件系统交互接口
        通过调用Blender CLI无头模式(-b)和自定义Python脚本(-P)实现，无须修改插件源码。
        """
        logger.info(f"Triggering Blender generation with parameters: {parameters}")
        task_id = str(uuid.uuid4())
        
        # 异步启动Blender后台进程
        asyncio.create_task(BlenderService._run_blender_task(task_id, parameters))
        
        return task_id

    @staticmethod
    async def _run_blender_task(task_id: str, parameters: dict):
        
        blender_executable = BLENDER_URL
        
        if not blender_executable or not os.path.exists(blender_executable):
            logger.error(f"Blender executable not found at: {blender_executable}")
        
        # 确保输出目录存在
        os.makedirs("data/exports", exist_ok=True)
        output_blend = os.path.abspath(f"data/exports/output_{task_id}.blend")
        
        # 组装要在Blender内部执行的过渡脚本
        # 逻辑：1.重置场景/引入环境 2.操作插件的UI属性/参数 3.执行插件对应的bpy.ops 4.保存
        script_content = f"""
import bpy
import sys

try:
    # 启用你要调用的 SCGS 插件
    bpy.ops.preferences.addon_enable(module='SCGS')

    # 将前端传进来的参数赋予 SCGS 的属性 (此处以AI指令算子为例)
    instruction_param = {repr(parameters.get('instruction', ''))}
    if instruction_param:
        instruction = instruction_param
    else:
        instruction = "生成风格{{}}比例{{}}".format("{parameters.get('style', '')}", "{parameters.get('scale', 1.0)}")
    
    if hasattr(bpy.context.scene, 'sna_ai_instruction'):
        bpy.context.scene.sna_ai_instruction = instruction

    # 调用 SCGS 的场景生成/AI处理执行算子
    if hasattr(bpy.ops.sna, 'process_ai_instruction'):
        bpy.ops.sna.process_ai_instruction()
    elif hasattr(bpy.ops.sna, 'start_5209e'):
        bpy.ops.sna.start_5209e()
        
    print("Generation operator finished.")

except Exception as e:
    print(f"Error during plugin execution: {{e}}")

# 强制保存模型
bpy.ops.wm.save_as_mainfile(filepath={repr(output_blend)})
sys.exit(0)
"""
        # 将上述脚本写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix=".py", delete=False, encoding='utf-8') as script_file:
            script_file.write(script_content)
            script_path = script_file.name
            
        try:
            # 使用 asyncio.to_thread 和 subprocess.run 替代 create_subprocess_exec
            # 这样可以绕过 Windows 上部分 EventLoop 不支持子进程的限制
            def run_blender():
                return subprocess.run(
                    [blender_executable, "-b", "-P", script_path],
                    capture_output=True,
                    text=False
                )
            
            process = await asyncio.to_thread(run_blender)
            
            if process.returncode == 0:
                logger.info(f"Task {task_id} completed. Saved to {output_blend}")
            else:
                stderr_text = process.stderr.decode('utf-8', errors='ignore') if process.stderr else "Unknown Error"
                logger.error(f"Task {task_id} failed: {stderr_text}")
        except Exception as ex:
            logger.error(f"Failed to start Blender process: {ex}", exc_info=True)
        finally:
            os.remove(script_path)

    @staticmethod
    async def check_generation_status(task_id: str) -> dict:
        """
        检查场景生成任务状态
        """
        logger.info(f"Checking status for task: {task_id}")
        output_blend = f"data/exports/output_{task_id}.blend"
        
        if os.path.exists(output_blend):
            return {
                "task_id": task_id,
                "status": "completed",
                "download_url": f"/blender/download/{task_id}"
            }
            
        return {
            "task_id": task_id,
            "status": "processing"
        }
