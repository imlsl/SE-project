from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models.user import (
    LoginRequest, LoginResponse, UserRole, DBUser, RegisterRequest,
    UserProfileResponse, UserProfileUpdateRequest, ChangePasswordRequest
)
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

# 使用 FastAPI 自带的 Bearer 令牌提取器，完美自动解析前端请求头中的 "Authorization: Bearer <token>"
security = HTTPBearer()

# 角色对应的插件系统入口跳转URL
ROLE_REDIRECT_URLS = {
    UserRole.ADMIN: "/admin/dashboard",
    UserRole.ANALYST: "/plugin/analysis-tool",
    UserRole.MODELER: "/plugin/blender-generator"
}

# --- 身份验证依赖项 (Depends) ---
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    根据前端传来的 Bearer Token 查找并返回数据库中的用户
    """
    token = credentials.credentials
    
    # 提取登录时埋在 token 里的用户名
    # 前端登录后会把返回的 token (形如 mock-jwt-token-username) 存入 localStorage，并在 profile 页面发请求时带上
    username = None
    if token.startswith("mock-jwt-token-"):
        username = token.replace("mock-jwt-token-", "")
    else:
        # 兼容性兜底：如果前端直接传了用户名作为纯字符串 token，尝试直接使用它
        username = token

    if not username:
        raise HTTPException(status_code=401, detail="无效的认证凭证 (Invalid token format)")

    # 从数据库中查询该用户
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="认证失败，用户不存在 (User not found)")
        
    return user


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录接口"""
    user = db.query(DBUser).filter(DBUser.username == request.username).first()
    if not user or user.password != request.password:
        # 当凭证错误时，抛出包含 detail 的 HTTPException
        # FastAPI 会自动将其转为 {"detail": "..."}，完美契合前端的 errorData.detail 逻辑
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user_role = user.role
    redirect_url = ROLE_REDIRECT_URLS[user_role]
    
    # 动态生成专属于该用户的 mock token：把用户名拼在后面
    # 这样当前端把这个 token 存到本地并在请求 profile 时带过来时，后端 get_current_user 就能完美识别当前是谁在操作
    mock_token = f"mock-jwt-token-{user.username}"
    
    return LoginResponse(
        token=mock_token,
        role=user_role,
        redirect_url=redirect_url
    )

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册接口"""
    existing_user = db.query(DBUser).filter(DBUser.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在 (Username already exists)")
    
    new_user = DBUser(username=request.username, password=request.password, role=request.role)
    db.add(new_user)
    db.commit()
    
    # 返回一个带 message 字段的字典，完美契合前端的 data.message 逻辑
    return {"message": "注册成功 (Registration successful)"}


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: DBUser = Depends(get_current_user)):
    """获取用户资料"""
    return current_user


@router.put("/profile")
async def update_profile(
    request: UserProfileUpdateRequest, 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """更新用户资料"""
    if request.full_name is not None:
        current_user.full_name = request.full_name
    if request.email is not None:
        current_user.email = request.email
    if request.phone is not None:
        current_user.phone = request.phone
    
    db.commit()
    db.refresh(current_user)
    
    # 适配 profile.html 提交表单时的 showMessage(data.message, 'success') 逻辑
    return {
        "message": "修改资料成功",
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest, 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """修改密码"""
    if current_user.password != request.old_password:
        raise HTTPException(status_code=400, detail="旧密码错误 (Incorrect old password)")
    
    if request.old_password == request.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")
        
    current_user.password = request.new_password
    db.commit()
    
    # 对应 profile.html 密码修改成功后的提示消息
    return {"message": "密码修改成功，请重新登录"}