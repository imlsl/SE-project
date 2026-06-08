from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.blender_service import BlenderService


router = APIRouter(prefix="/blender", tags=["blender"])


class SceneGenerationRequest(BaseModel):
    city_name: str = ""
    description: str = ""
    scale: float = 1.0
    style: str = "default"
    instruction: str = ""
    template_id: str = ""
    road_type: str = ""
    weather: str = ""
    manual_vertices: str = ""
    manual_edges: str = ""
    layout_points: list[dict[str, Any]] = []
    selected_assets: list[dict[str, Any]] = []
    scene_id: Optional[int] = None


class SceneEditRequest(BaseModel):
    source_task_id: str
    instruction: str = ""
    description: str = ""
    scene_id: Optional[int] = None


@router.get("/diagnostics")
async def blender_diagnostics():
    """检查 Blender 启动状态、SCGS 插件启用状态，以及候选 bpy.ops 算子。"""
    return await BlenderService.diagnostics()


@router.post("/generate")
async def generate_scene(request: SceneGenerationRequest):
    """启动 SCGS 城市场景生成任务。"""
    task_id = await BlenderService.trigger_scene_generation(request.model_dump())
    return {
        "message": "Scene generation task started successfully",
        "task_id": task_id,
        "status_url": f"/blender/status/{task_id}",
        "download_url": f"/blender/download/{task_id}",
    }


@router.post("/edit")
async def edit_scene(request: SceneEditRequest):
    """基于已完成的 Blender 生成任务启动 SCGS 场景编辑任务。"""
    try:
        task_id = await BlenderService.trigger_scene_edit(request.source_task_id, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "message": "场景编辑任务已成功启动",
        "task_id": task_id,
        "source_task_id": request.source_task_id,
        "status_url": f"/blender/status/{task_id}",
        "download_url": f"/blender/download/{task_id}",
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询 Blender/SCGS 生成任务的持久化状态。"""
    return await BlenderService.check_generation_status(task_id)


@router.get("/download/{task_id}")
async def download_scene(task_id: str):
    """下载生成完成的 .blend 文件。"""
    file_path = BlenderService.output_path_for(task_id)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Model file not found or generation not completed.")

    return FileResponse(
        path=str(file_path),
        filename=f"city_scene_{task_id}.blend",
        media_type="application/octet-stream",
    )
