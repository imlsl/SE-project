from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
import json
import os
from pathlib import Path

from app.database import get_db
from app.admin_logger import admin_logger, log_file
from app.models.user import (
    DBUser, UserRole, UserProfileResponse, ROLE_CN_MAP,
    AdminCreateUserRequest, AdminUpdateUserRequest, SystemUptimeResponse
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

# 系统运行时间存储文件 - 使用绝对路径
BASE_DIR = Path(__file__).parent.parent.parent  # 回到项目根目录
UPTIME_DIR = BASE_DIR / "data"
UPTIME_FILE = UPTIME_DIR / "system_uptime.json"

# 确保 data 目录存在
try:
    UPTIME_DIR.mkdir(exist_ok=True)
except Exception as e:
    print(f"创建目录失败: {e}")

def load_server_start_time():
    """从文件加载服务器启动时间"""
    
    if UPTIME_FILE.exists():
        try:
            with open(UPTIME_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
                return datetime.fromisoformat(data['server_start_time'])
        except Exception as e:
            print(f"读取启动时间文件失败: {e}")
    
    # 文件不存在，创建并保存当前时间
    current_time = datetime.now()
    save_server_start_time(current_time)
    return current_time

def save_server_start_time(start_time):
    """保存服务器启动时间到文件"""
    try:
        # 确保目录存在
        UPTIME_DIR.mkdir(exist_ok=True)
        
        data = {'server_start_time': start_time.isoformat()}
        with open(UPTIME_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存启动时间失败: {e}")
        return False

# 初始化服务器启动时间
SERVER_START_TIME = load_server_start_time()

def get_admin_user(x_username: str = Header(...), db: Session = Depends(get_db)):
    """获取当前用户并校验是否为管理员"""
    user = db.query(DBUser).filter(DBUser.username == x_username).first()
    if not user:
        raise HTTPException(status_code=401, detail="未认证或用户不存在")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="权限不足：仅限系统管理员操作")
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
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    new_user = DBUser(
        username=request.username, 
        password=request.password, 
        role=request.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    role_cn = ROLE_CN_MAP.get(new_user.role, new_user.role.value)
    admin_logger.info(f"管理员 '{admin.username}' 创建了新用户 '{new_user.username}' (角色: {role_cn})")
    
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
    
    if request.username and request.username != target_user.username:
        conflict_user = db.query(DBUser).filter(DBUser.username == request.username).first()
        if conflict_user:
            raise HTTPException(status_code=400, detail="该用户名已被占用")
        target_user.username = request.username
        
    if request.password:
        target_user.password = request.password
    if request.role:
        target_user.role = request.role
        
    db.commit()
    db.refresh(target_user)
    
    role_cn = ROLE_CN_MAP.get(target_user.role, target_user.role.value)
    admin_logger.info(f"管理员 '{admin.username}' 更新了用户 '{target_user.username}' (角色: {role_cn})")
    
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
    
    admin_logger.info(f"管理员 '{admin.username}' 删除了用户 '{username}'")
    
    return {"message": f"用户 '{username}' 成功删除"}


# 5. 获取指定用户的最近登录时间 (GET /admin/users/{username}/last-login)
@router.get("/{username}/last-login")
async def get_user_last_login(
    username: str, 
    db: Session = Depends(get_db), 
    admin: DBUser = Depends(get_admin_user)
):
    """获取指定用户的最近登录时间"""
    target_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"username": target_user.username, "last_login": target_user.last_login}
    
# 6. 获取系统运行时间 (GET /admin/users/system/uptime)
@router.get("/system/uptime", response_model=SystemUptimeResponse)
async def get_system_uptime(
    admin: DBUser = Depends(get_admin_user)
):
    """获取系统运行时间"""
    global SERVER_START_TIME
    
    now = datetime.now()
    uptime = now - SERVER_START_TIME
    uptime_days = uptime.days
    
    return SystemUptimeResponse(
        server_start_time=SERVER_START_TIME.strftime("%Y-%m-%d %H:%M:%S"),
        uptime_days=uptime_days,
        current_time=now.strftime("%Y-%m-%d %H:%M:%S"),
        file_path=str(UPTIME_FILE),
        file_exists=UPTIME_FILE.exists()
    )

# 7. 重置系统运行时间 (POST /admin/users/system/reset-uptime)
@router.post("/system/reset_uptime")
async def reset_system_uptime(
    admin: DBUser = Depends(get_admin_user)
):
    """重置系统运行时间"""
    global SERVER_START_TIME
    SERVER_START_TIME = datetime.now()
    save_server_start_time(SERVER_START_TIME)
    return {
        "message": "系统运行时间已重置",
        "new_start_time": SERVER_START_TIME.strftime("%Y-%m-%d %H:%M:%S")
    }

# 8. 获取系统日志 (GET /admin/users/system/logs)
@router.get("/system/logs")
async def get_system_logs(
    limit: int = 100, 
    admin: DBUser = Depends(get_admin_user)
):
    """获取最新系统日志"""
    try:
        if not os.path.exists(log_file):
            return []
        
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # 返回最近的 limit 条日志（忽略末尾可能存在的空行）
        return [line.strip() for line in lines[-limit:] if line.strip()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志失败: {str(e)}")


# 9. 清除系统日志 (DELETE /admin/users/system/logs)
@router.delete("/system/logs")
async def clear_system_logs(admin: DBUser = Depends(get_admin_user)):
    """清除系统日志"""
    try:
        if os.path.exists(log_file):
            # 以只写模式打开文件并清空内容
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("")
            admin_logger.info(f"管理员 '{admin.username}' 清空了系统日志")
            return {"message": "系统日志已成功清空"}
        else:
            return {"message": "查无日志文件，无需清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空日志失败: {str(e)}")
