from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import (
    DBUser, UserRole, UserProfileResponse, 
    AdminCreateUserRequest, AdminUpdateUserRequest
)

from app.api.auth import get_current_user 

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

# --- 权限校验依赖：确保只有系统管理员可以访问 ---
def get_admin_user(x_username: str = Header(..., description="模拟当前登录用户的用户名"), db: Session = Depends(get_db)):
    """获取当前用户并校验是否为管理员"""
    user = db.query(DBUser).filter(DBUser.username == x_username).first()
    if not user:
        raise HTTPException(status_code=401, detail="未认证或用户不存在 (User not found)")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足：仅限系统管理员操作 (Forbidden)")
    return user


# 1. 获取所有用户 (GET /admin/users)
@router.get("", response_model=List[UserProfileResponse])
async def get_all_users(
    db: Session = Depends(get_db), 
    admin: DBUser = Depends(get_admin_user)
):
    """获取所有用户列表"""
    users = db.query(DBUser).all()
    return users


# 2. 创建用户 (POST /admin/users)
@router.post("", response_model=UserProfileResponse)
async def create_user(
    request: AdminCreateUserRequest, 
    db: Session = Depends(get_db), 
    admin: DBUser = Depends(get_admin_user)
):
    """管理员直接创建新用户"""
    existing_user = db.query(DBUser).filter(DBUser.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在 (Username already exists)")
    
    new_user = DBUser(
        username=request.username, 
        password=request.password, 
        role=request.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# 3. 更新用户 (PUT /admin/users/{username})
@router.put("/{username}", response_model=UserProfileResponse)
async def update_user_by_name(
    username: str, 
    request: AdminUpdateUserRequest, 
    db: Session = Depends(get_db), 
    admin: DBUser = Depends(get_admin_user)
):
    target_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 如果修改了用户名，需要检查是否与其他用户冲突
    if request.username and request.username != target_user.username:
        conflict_user = db.query(DBUser).filter(DBUser.username == request.username).first()
        if conflict_user:
            raise HTTPException(status_code=400, detail="该用户名已被占用 (Username already taken)")
        target_user.username = request.username
        
    if request.password:
        target_user.password = request.password
    if request.role:
        target_user.role = request.role
        
    db.commit()
    db.refresh(target_user)
    return target_user


# 4. 删除用户 (DELETE /admin/users/{username})
@router.delete("/{username}")
async def delete_user_by_name(
    username: str, 
    db: Session = Depends(get_db), 
    admin: DBUser = Depends(get_admin_user)
):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")
        
    target_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    db.delete(target_user)
    db.commit()
    return {"message": "用户删除成功", "deleted_username": username}