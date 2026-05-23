from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.database import Base

class UserRole(str, Enum):
    ADMIN = "system_admin"
    ANALYST = "industry_analyst"
    MODELER = "scene_modeler"

# --- SQLAlchemy 模型 (用于数据库映射) ---
class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(128), nullable=False) 
    role = Column(SQLEnum(UserRole), nullable=False)
    
    # ====== 新增字段以适配前端 profile.html ======
    full_name = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)

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

    class Config:
        from_attributes = True 

# ====== 修改：接收前端传递的个人资料更新数据 ======
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

