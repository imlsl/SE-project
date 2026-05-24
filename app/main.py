from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, blender, admin, analyst, modeler
from app.admin_logger import admin_logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # 系统启动操作 (Server Startup Ops)
    # ==========================================
    admin_logger.info("============== 系统已启动 (System Server Started) ==============")
    
    yield
    
    # ==========================================
    # 系统关闭操作 (Server Shutdown Ops)
    # ==========================================
    admin_logger.info("============== 系统已关闭 (System Server Shutdown) ==============")


app = FastAPI(title="Smart City Generation System API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(blender.router)
app.include_router(admin.router)
app.include_router(analyst.router)
app.include_router(modeler.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart City Generation System Backend!"}
