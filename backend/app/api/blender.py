from fastapi import APIRouter
from pydantic import BaseModel
from app.services.blender_service import BlenderService

router = APIRouter(prefix="/blender", tags=["blender"])

class SceneGenerationRequest(BaseModel):
    city_name: str
    scale: float
    style: str  # 例如: "cyberpunk", "modern", "low-poly"

@router.post("/generate")
async def generate_scene(request: SceneGenerationRequest):
    """
    触发Blender城市场景生成插件任务
    """
    task_id = await BlenderService.trigger_scene_generation(request.dict())
    return {"message": "Scene generation task started successfully", "task_id": task_id}

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    查询Blender场景生成任务状态
    """
    status = await BlenderService.check_generation_status(task_id)
    return status
