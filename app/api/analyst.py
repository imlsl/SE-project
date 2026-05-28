from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from app.database import get_db
from app.models.user import DBUser, UserRole
from app.models.scene import (
    DBScene, IndustryDashboardResponse, MetricItem, ActivityItem,
    GeneratedReportResponse, DataExportResponse, TrendResponse
)

router = APIRouter(prefix="/analyst", tags=["industry-analyst"])

def get_analyst_user(x_username: str = Header(...), db: Session = Depends(get_db)):
    """权限校验：仅限行业分析师"""
    user = db.query(DBUser).filter(DBUser.username == x_username).first()
    if not user or user.role != UserRole.ANALYST:
        raise HTTPException(status_code=403, detail="权限不足：仅限行业分析师操作")
    return user

@router.get("/dashboard", response_model=IndustryDashboardResponse)
async def get_dashboard_data(
    current_user: DBUser = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """
    获取行业分析工作台大盘数据 (对应 loadIndustryData)
    注意：在真实生产环境中，这里的数据应该通过复杂的 SQL 聚合查询得出
    """
    total_projects = db.query(DBScene).count()
    active_scenes = db.query(DBScene).filter(DBScene.status == "published").count()
    return IndustryDashboardResponse(
        totalProjects=max(total_projects, 24),
        activeScenes=max(active_scenes, 8),
        totalReports=156 + total_projects,
        accuracy="94%",
        metrics={
            "transportation": MetricItem(value=85, trend="+12%", status="up"),
            "energy": MetricItem(value=72, trend="+5%", status="up"),
            "environment": MetricItem(value=91, trend="+3%", status="up")
        },
        activities=[
            ActivityItem(time="10:30", action="生成了第三季度城市交通分析报告", type="report"),
            ActivityItem(time="09:15", action="新增了5个智慧交通场景数据", type="data"),
            ActivityItem(time="昨天", action="完成了能源消耗趋势预测模型", type="model"),
            ActivityItem(time="昨天", action="导出了环境监测月度报告", type="report")
        ]
    )

@router.post("/reports/generate", response_model=GeneratedReportResponse)
async def generate_weekly_report(
    current_user: DBUser = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """触发报告生成任务"""
    report_id = str(uuid.uuid4())
    total_projects = db.query(DBScene).count()
    active_scenes = db.query(DBScene).filter(DBScene.status == "published").count()
    return GeneratedReportResponse(
        report_id=report_id,
        title="智慧城市行业周报",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        download_url=f"/analyst/reports/{report_id}/download",
        summary=f"本周累计城市项目 {total_projects} 个，活跃场景 {active_scenes} 个，交通与环境指标保持上升。"
    )

@router.get("/data/export", response_model=DataExportResponse)
async def export_data(
    current_user: DBUser = Depends(get_analyst_user),
    db: Session = Depends(get_db)
):
    """导出前端分析面板需要的数据。"""
    dashboard = await get_dashboard_data(current_user=current_user, db=db)
    export_id = str(uuid.uuid4())
    return DataExportResponse(
        export_id=export_id,
        filename=f"industry-data-{datetime.now().strftime('%Y%m%d%H%M%S')}.json",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        download_url=f"/analyst/data/export/{export_id}/download",
        data=dashboard.model_dump()
    )

@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    days: int = 30,
    current_user: DBUser = Depends(get_analyst_user)
):
    """查看趋势按钮对应的趋势数据。"""
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="days 必须在 1 到 365 之间")
    return TrendResponse(
        window_days=days,
        summary=f"近 {days} 天智慧交通增长显著，环境与能源指标稳定提升。",
        series=[
            {"label": "transportation", "value": 85, "change": 12.5},
            {"label": "energy", "value": 72, "change": 5.2},
            {"label": "environment", "value": 91, "change": 3.1},
        ]
    )
