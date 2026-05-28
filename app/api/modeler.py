from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json
from pathlib import Path

from app.database import get_db
from app.models.user import DBUser, UserRole
from app.models.scene import (
    DBScene, SceneCreateRequest, SceneResponse, LLMCommandRequest,
    AssetItem, AssetCreateRequest, LayoutApplyRequest, SketchProcessRequest,
    SceneUpdateRequest
)

router = APIRouter(prefix="/modeler", tags=["scene-modeler"])

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_FILE = DATA_DIR / "modeler_assets.json"
DEFAULT_ASSETS = [
    {"id": "building-modern", "name": "现代建筑", "icon": "fa-building", "type": "model"},
    {"id": "road-asphalt", "name": "柏油路面", "icon": "fa-road", "type": "texture"},
    {"id": "led-lamp", "name": "LED路灯", "icon": "fa-lightbulb", "type": "model"},
    {"id": "green-belt", "name": "绿化带", "icon": "fa-tree", "type": "model"},
    {"id": "sidewalk", "name": "人行道", "icon": "fa-walking", "type": "texture"},
    {"id": "traffic-sign", "name": "交通标志", "icon": "fa-traffic-light", "type": "model"},
]

def load_assets():
    if ASSETS_FILE.exists():
        try:
            with open(ASSETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_ASSETS
    return DEFAULT_ASSETS

def save_assets(assets):
    DATA_DIR.mkdir(exist_ok=True)
    with open(ASSETS_FILE, "w", encoding="utf-8") as f:
        json.dump(assets, f, indent=2, ensure_ascii=False)

def get_modeler_user(x_username: str = Header(...), db: Session = Depends(get_db)):
    """权限校验：仅限场景建模师"""
    user = db.query(DBUser).filter(DBUser.username == x_username).first()
    if not user or user.role != UserRole.MODELER:
        raise HTTPException(status_code=403, detail="权限不足：仅限场景建模师操作")
    return user


@router.get("/scenes", response_model=List[SceneResponse])
async def list_scenes(
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的场景列表"""
    scenes = db.query(DBScene).filter(DBScene.owner_id == current_user.id).order_by(DBScene.id.desc()).all()
    
    return [
        SceneResponse(
            id=s.id,
            name=s.name,
            lastModified=s.last_modified.strftime("%Y-%m-%d"),
            status=s.status
        ) for s in scenes
    ]


@router.post("/scenes", response_model=SceneResponse)
async def create_scene(
    request: SceneCreateRequest,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db)
):
    """新建场景"""
    new_scene = DBScene(
        name=request.name,
        status="draft",
        owner_id=current_user.id
    )
    db.add(new_scene)
    db.commit()
    db.refresh(new_scene)

    return SceneResponse(
        id=new_scene.id,
        name=new_scene.name,
        lastModified=new_scene.last_modified.strftime("%Y-%m-%d"),
        status=new_scene.status
    )

@router.put("/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: int,
    request: SceneUpdateRequest,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db)
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
        status=scene.status
    )


@router.delete("/scenes/{scene_id}")
async def delete_scene(
    scene_id: int,
    current_user: DBUser = Depends(get_modeler_user),
    db: Session = Depends(get_db)
):
    """删除场景"""
    scene = db.query(DBScene).filter(DBScene.id == scene_id, DBScene.owner_id == current_user.id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在或无权删除")
    
    db.delete(scene)
    db.commit()
    return {"message": "场景已成功删除"}


@router.post("/blender/llm-command")
async def process_llm_command(
    request: LLMCommandRequest,
    current_user: DBUser = Depends(get_modeler_user)
):
    """
    处理前端发来的自然语言指令，转化为 Blender 插件所需的参数。
    这里是您实现大模型 (LLM) 集成生成 Smart City 参数的核心入口。
    """
    command = request.command
    # 这里可以接入您的 LLM API (例如解析 "在十字路口添加智能路灯")
    # 模拟 LLM 解析结果并返回给前端桥接器：
    
    mock_llm_response = {
        "status": "success",
        "parsed_intent": "ADD_ASSET",
        "parameters": {
            "asset_type": "model",
            "asset_name": "smart_lamp_v2",
            "location": "intersection",
            "quantity": 4
        },
        "blender_script": "bpy.ops.mesh.primitive_cube_add(location=(0,0,0)) # 伪代码"
    }
    return mock_llm_response

@router.get("/assets", response_model=List[AssetItem])
async def list_assets(current_user: DBUser = Depends(get_modeler_user)):
    """获取建模师资产库。"""
    return load_assets()

@router.post("/assets", response_model=AssetItem)
async def create_asset(
    request: AssetCreateRequest,
    current_user: DBUser = Depends(get_modeler_user)
):
    """登记一个新资产，供前端资产库刷新和上传按钮使用。"""
    assets = load_assets()
    asset_id = f"{request.type}-{int(datetime.utcnow().timestamp())}"
    asset = {
        "id": asset_id,
        "name": request.name,
        "type": request.type,
        "icon": request.icon,
    }
    assets.insert(0, asset)
    save_assets(assets)
    return asset

@router.post("/layout/apply")
async def apply_layout(
    request: LayoutApplyRequest,
    current_user: DBUser = Depends(get_modeler_user)
):
    """接收前端点集布局，返回可交给 Blender 的道路/节点参数。"""
    if not request.points:
        raise HTTPException(status_code=400, detail="布局点集不能为空")
    return {
        "status": "success",
        "node_count": len(request.points),
        "road_count": max(len(request.points) - 1, 0),
        "parameters": {
            "points": [point.model_dump() for point in request.points],
            "layout_type": "polyline"
        }
    }

@router.post("/sketch/process")
async def process_sketch(
    request: SketchProcessRequest,
    current_user: DBUser = Depends(get_modeler_user)
):
    """处理草图文件名并返回提取出的示例点集。"""
    if not request.file_name:
        raise HTTPException(status_code=400, detail="草图文件名不能为空")
    points = [{"x": 10, "y": 20}, {"x": 50, "y": 80}, {"x": 120, "y": 60}]
    return {
        "status": "success",
        "file_name": request.file_name,
        "points": points,
        "road_count": 2
    }
