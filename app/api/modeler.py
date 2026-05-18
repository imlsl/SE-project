from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.user import DBUser, UserRole
from app.models.scene import DBScene, SceneCreateRequest, SceneResponse, LLMCommandRequest

router = APIRouter(prefix="/modeler", tags=["scene-modeler"])

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