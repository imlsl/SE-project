from enum import Enum
from pydantic import BaseModel
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
    password = Column(String(128), nullable=False) # 实际应用中需要存储哈希密码
    role = Column(SQLEnum(UserRole), nullable=False)

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

