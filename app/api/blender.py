from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from app.services.blender_service import BlenderService

router = APIRouter(prefix="/blender", tags=["blender"])

class SceneGenerationRequest(BaseModel):
    city_name: str = ""
    scale: float = 1.0
    style: str = "default"
    instruction: str = ""

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

@router.get("/download/{task_id}")
async def download_scene(task_id: str):
    """
    下载生成的城市场景模型文件
    """
    file_path = os.path.abspath(f"data/exports/output_{task_id}.blend")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Model file not found or generation not completed.")
        
    return FileResponse(
        path=file_path, 
        filename=f"city_scene_{task_id}.blend",
        media_type="application/octet-stream"
    )
