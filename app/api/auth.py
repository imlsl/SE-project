from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.user import LoginRequest, LoginResponse, UserRole, DBUser, RegisterRequest
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# 角色对应的插件系统入口跳转URL
ROLE_REDIRECT_URLS = {
    UserRole.ADMIN: "/admin/dashboard",
    UserRole.ANALYST: "/plugin/analysis-tool",
    UserRole.MODELER: "/plugin/blender-generator"
}

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口 (连接 MySQL 数据库)
    系统管理员 (system_admin)
    行业分析师 (industry_analyst)
    场景建模师 (scene_modeler)
    """
    # 从 MySQL 数据库中查询该用户名是否存在
    user = db.query(DBUser).filter(DBUser.username == request.username).first()
    
    # 验证用户是否存在以及密码是否一致（注：生产环境请使用由 passlib 等库验证哈希加密后的密码）
    if not user or user.password != request.password:
        raise HTTPException(status_code=401, detail="无效的凭证(Invalid credentials)")
    
    user_role = user.role
    redirect_url = ROLE_REDIRECT_URLS[user_role]
    
    return LoginResponse(
        token="mock-jwt-token-123",
        role=user_role,
        redirect_url=redirect_url
    )

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册接口
    """
    # 检查用户名是否已存在
    existing_user = db.query(DBUser).filter(DBUser.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在 (Username already exists)")
    
    # 创建新用户
    new_user = DBUser(
        username=request.username,
        password=request.password,
        role=request.role
    )
    db.add(new_user)
    db.commit()
    
    return {"message": "注册成功 (Registration successful)"}
