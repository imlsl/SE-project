from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import DBUser, UserRole
from app.models.scene import IndustryDashboardResponse, MetricItem, ActivityItem

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
    return IndustryDashboardResponse(
        totalProjects=24,
        activeScenes=8,
        totalReports=156,
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

@router.post("/reports/generate")
async def generate_weekly_report(current_user: DBUser = Depends(get_analyst_user)):
    """触发报告生成任务"""
    # 实际项目中可集成定时任务或异步后台任务 (Celery/FastAPI BackgroundTasks)
    return {"message": "报告生成任务已提交，预计需要3分钟"}