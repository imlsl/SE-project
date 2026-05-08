from fastapi import APIRouter, HTTPException
from typing import Dict
from app.models.user import LoginRequest, LoginResponse, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

# 模拟用户数据库
MOCK_USERS: Dict[str, UserRole] = {
    "admin": UserRole.ADMIN,
    "analyst": UserRole.ANALYST,
    "modeler": UserRole.MODELER,
}

# 角色对应的插件系统入口跳转URL
ROLE_REDIRECT_URLS = {
    UserRole.ADMIN: "/admin/dashboard",
    UserRole.ANALYST: "/plugin/analysis-tool",
    UserRole.MODELER: "/plugin/blender-generator"
}

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录接口 (多角色)
    系统管理员 (system_admin)
    行业分析师 (industry_analyst)
    场景建模师 (scene_modeler)
    """
    if request.username not in MOCK_USERS or request.password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_role = MOCK_USERS[request.username]
    redirect_url = ROLE_REDIRECT_URLS[user_role]
    
    return LoginResponse(
        token="mock-jwt-token-123",
        role=user_role,
        redirect_url=redirect_url
    )
