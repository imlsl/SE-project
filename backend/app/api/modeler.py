from datetime import datetime
from pathlib import Path
from typing import List
import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scene import (
    AssetCreateRequest,
    AssetItem,
    DBScene,
    LLMCommandRequest,
    LayoutApplyRequest,
    SceneCreateRequest,
    SceneResponse,
    SceneUpdateRequest,
)
from app.models.user import DBUser, UserRole


router = APIRouter(prefix="/modeler", tags=["scene-modeler"])

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_FILE = DATA_DIR / "modeler_assets.json"

DEFAULT_ASSETS = [
    {
        "id": "tree-1",
        "name": "Default Tree",
        "icon": "fa-tree",
        "type": "model",
        "plugin_type": "Tree",
        "plugin_name": "Tree1_Tree_ICity_Default",
    },
    {
        "id": "bench-1",
        "name": "Default Bench",
        "icon": "fa-chair",
        "type": "model",
        "plugin_type": "Bench",
        "plugin_name": "Bench1_Bench_ICity_Default",
    },
    {
        "id": "light-1",
        "name": "Default Light",
        "icon": "fa-lightbulb",
        "type": "model",
        "plugin_type": "Light",
        "plugin_name": "Light1_Light_ICity_Default",
    },
    {
        "id": "road-clean-1",
        "name": "Clean Road 1",
        "icon": "fa-road",
        "type": "texture",
        "plugin_type": "Texture",
        "plugin_name": "ICity_Road 1 clean_Default",
        "material_target": "Road",
    },
    {
        "id": "road-clean-3",
        "name": "Clean Road 3",
        "icon": "fa-road",
        "type": "texture",
        "plugin_type": "Texture",
        "plugin_name": "ICity_Road 3 clean_Default",
        "material_target": "Road",
    },
    {
        "id": "road-dirty-8",
        "name": "Dirty Road 8",
        "icon": "fa-road",
        "type": "texture",
        "plugin_type": "Texture",
        "plugin_name": "ICity_Road 8 dirty_Default",
        "material_target": "Road",
    },
]


def load_assets() -> list[dict]:
    if ASSETS_FILE.exists():
        try:
            with ASSETS_FILE.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return DEFAULT_ASSETS
    return DEFAULT_ASSETS


def save_assets(assets: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with ASSETS_FILE.open("w", encoding="utf-8") as file:
        json.dump(assets, file, indent=2, ensure_ascii=False)


def normalize_asset(asset: dict) -> dict:
    normalized = dict(asset)
    normalized.setdefault("plugin_type", normalized.get("type", "model"))
    normalized.setdefault("plugin_name", normalized.get("name", ""))
    normalized.setdefault("material_target", "Road" if normalized.get("type") == "texture" else None)
    return normalized


def get_modeler_user(x_username: str = Header(...), db: Session = Depends(get_db)) -> DBUser:
    user = db.query(DBUser).filter(DBUser.username == x_username).first()
    if not user or user.role != UserRole.MODELER:
        raise HTTPException(status_code=403, detail="权限不足：仅限场景建模师操作")
    return user


@router.get("/scenes", response_model=List[SceneResponse])
async def list_scenes(
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的场景列表"""
    scenes = db.query(DBScene).filter(DBScene.owner_id == current_user.id).order_by(DBScene.id.desc()).all()
    
    return [
        SceneResponse(
            id=scene.id,
            name=scene.name,
            lastModified=scene.last_modified.strftime("%Y-%m-%d"),
            status=scene.status,
        )
        for scene in scenes
    ]


@router.post("/scenes", response_model=SceneResponse)
async def create_scene(
    request: SceneCreateRequest,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db),
):
    """新建场景"""
    new_scene = DBScene(name=request.name, status="draft", owner_id=current_user.id)
    db.add(new_scene)
    db.commit()
    db.refresh(new_scene)

    return SceneResponse(
        id=new_scene.id,
        name=new_scene.name,
        lastModified=new_scene.last_modified.strftime("%Y-%m-%d"),
        status=new_scene.status,
    )


@router.put("/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: int,
    request: SceneUpdateRequest,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db),
):
    """更新场景名称或发布状态。"""
    scene = db.query(DBScene).filter(DBScene.id == scene_id, DBScene.owner_id == current_user.id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或无权修改")
    if request.name:
        scene.name = request.name
    if request.status:
        if request.status not in {"draft", "published"}:
            raise HTTPException(status_code=400, detail="场景状态仅支持 draft 或 published")
        scene.status = request.status
    scene.last_modified = datetime.utcnow()
    db.commit()
    db.refresh(scene)
    return SceneResponse(
        id=scene.id,
        name=scene.name,
        lastModified=scene.last_modified.strftime("%Y-%m-%d"),
        status=scene.status,
    )


@router.delete("/scenes/{scene_id}")
async def delete_scene(
    scene_id: int,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db),
):
    """删除场景"""
    scene = db.query(DBScene).filter(DBScene.id == scene_id, DBScene.owner_id == current_user.id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或无权修改")

    db.delete(scene)
    db.commit()
    return {"message": "场景已成功删除"}


@router.post("/blender/llm-command")
async def process_llm_command(
    request: LLMCommandRequest,
    current_user: DBUser = Depends(get_modeler_user),
):
    """
    处理前端发来的自然语言指令，转化为 Blender 插件所需的参数。
    这里是实现大模型 (LLM) 集成生成 Smart City 参数的核心入口。
    """
    return {
        "status": "success",
        "parsed_intent": "ADD_ASSET",
        "parameters": {
            "asset_type": "model",
            "asset_name": "smart_lamp_v2",
            "location": "intersection",
            "quantity": 4,
        },
        "blender_script": "bpy.ops.mesh.primitive_cube_add(location=(0,0,0))",
    }


@router.get("/assets", response_model=List[AssetItem])
async def list_assets(current_user: DBUser = Depends(get_modeler_user)):
    return [normalize_asset(asset) for asset in load_assets()]


@router.post("/assets", response_model=AssetItem)
async def create_asset(
    request: AssetCreateRequest,
    current_user: DBUser = Depends(get_modeler_user),
):
    """登记一个新资产，供前端资产库刷新和上传按钮使用。"""
    assets = load_assets()
    asset_id = f"{request.type}-{int(datetime.utcnow().timestamp())}"
    asset = {
        "id": asset_id,
        "name": request.name,
        "type": request.type,
        "icon": request.icon,
        "plugin_type": request.plugin_type or request.type,
        "plugin_name": request.plugin_name or request.name,
        "material_target": request.material_target,
    }
    assets.insert(0, asset)
    save_assets(assets)
    return asset


@router.post("/layout/apply")
async def apply_layout(
    request: LayoutApplyRequest,
    current_user: DBUser = Depends(get_modeler_user),
):
    """接收前端点集布局，返回可交给 Blender 的道路/节点参数。"""
    if len(request.points) < 2:
        raise HTTPException(status_code=400, detail="布局至少需要两个点")

    manual_vertices = ",".join(f"({point.x},{point.y},0)" for point in request.points)
    manual_edges = ",".join(f"({idx},{idx + 1})" for idx in range(len(request.points) - 1))
    return {
        "status": "success",
        "node_count": len(request.points),
        "road_count": max(len(request.points) - 1, 0),
        "manual_vertices": manual_vertices,
        "manual_edges": manual_edges,
        "parameters": {
            "points": [point.model_dump() for point in request.points],
            "layout_type": "polyline",
            "manual_vertices": manual_vertices,
            "manual_edges": manual_edges,
        },
    }
