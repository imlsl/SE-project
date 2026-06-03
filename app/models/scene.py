from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base
from app.models.user import UserRole

# ==========================================
# 数据库模型 (SQLAlchemy)
# ==========================================
class DBScene(Base):
    """场景项目数据库模型"""
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="draft") # draft(草稿) 或 published(已发布)
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(Integer, index=True) # 关联到 DBUser.id

# ==========================================
# API 验证模型 (Pydantic)
# ==========================================

# --- 行业分析师大盘模型 ---
class MetricItem(BaseModel):
    value: int
    trend: str
    status: str

class ActivityItem(BaseModel):
    time: str
    action: str
    type: str

class IndustryDashboardResponse(BaseModel):
    totalProjects: int
    activeScenes: int
    totalReports: int
    accuracy: str
    metrics: Dict[str, MetricItem]
    activities: List[ActivityItem]

# --- 场景建模师模型 ---
class SceneCreateRequest(BaseModel):
    name: str

class SceneResponse(BaseModel):
    id: int
    name: str
    lastModified: str  # 格式化后的日期字符串
    status: str

class LLMCommandRequest(BaseModel):
    command: str

class AssetItem(BaseModel):
    id: str
    name: str
    icon: str
    type: str
    plugin_type: Optional[str] = None
    plugin_name: Optional[str] = None
    material_target: Optional[str] = None

class AssetCreateRequest(BaseModel):
    name: str
    type: str = "model"
    icon: str = "fa-cube"
    plugin_type: Optional[str] = None
    plugin_name: Optional[str] = None
    material_target: Optional[str] = None

class LayoutPoint(BaseModel):
    x: float
    y: float

class LayoutApplyRequest(BaseModel):
    points: List[LayoutPoint]

class SceneUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None

class GeneratedReportResponse(BaseModel):
    report_id: str
    title: str
    generated_at: str
    download_url: str
    summary: str
    message: Optional[str] = None

class DataExportResponse(BaseModel):
    export_id: str
    filename: str
    generated_at: str
    download_url: str
    data: Dict[str, Any]

class TrendResponse(BaseModel):
    window_days: int
    summary: str
    series: List[Dict[str, Any]]
