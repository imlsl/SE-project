from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "system_admin"
    ANALYST = "industry_analyst"
    MODELER = "scene_modeler"

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
