from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime
from datetime import datetime
from app.database import Base

class UserRole(str, Enum):
    ADMIN = "system_admin"
    ANALYST = "industry_analyst"
    MODELER = "scene_modeler"

ROLE_CN_MAP = {
    UserRole.ADMIN: "系统管理员",
    UserRole.ANALYST: "行业分析师",
    UserRole.MODELER: "场景建模师"
}

# --- SQLAlchemy 模型 (用于数据库映射) ---
class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(128), nullable=False) 
    role = Column(SQLEnum(UserRole), nullable=False)
    full_name = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    last_login = Column(DateTime, nullable=True)

# --- Pydantic 模型 (用于API数据验证) ---
class User(BaseModel):
    username: str
    role: UserRole

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    role: UserRole
    redirect_url: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: UserRole

class UserProfileResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True 

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    role: UserRole

class AdminUpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class SystemUptimeResponse(BaseModel):
    server_start_time: str
    uptime_days: int
    current_time: str
    file_path: str
    file_exists: bool

class SystemSettingsRequest(BaseModel):
    renderQuality: str
    backupInterval: str
    enableAnalytics: bool

class SystemSettingsResponse(SystemSettingsRequest):
    updated_at: Optional[str] = None

class ApiStatsResponse(BaseModel):
    total_calls: int
    users_count: int
    scenes_count: int
    generated_at: str
