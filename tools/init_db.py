import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)

if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from datetime import datetime
from app.database import engine, Base, SessionLocal
from app.models.user import DBUser, UserRole
from app.models.scene import DBScene

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Creating database tables...")
    # 根据模型自动创建所有的表 (包括 users 和 scenes)
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully.")

def seed_data():
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(DBUser).first():
            logger.info("Database already contains data, skipping seed.")
            return
            
        logger.info("Seeding initial mock users...")
        # 为初始化的 Mock 用户赋予初始昵称、部分详情以及默认登录时间
        now = datetime.now()
        admin_user = DBUser(username="admin", password="123456", role=UserRole.ADMIN, full_name="系统总管", last_login=now)
        analyst_user = DBUser(username="analyst", password="123456", role=UserRole.ANALYST, full_name="核心分析师", last_login=now)
        modeler_user = DBUser(username="modeler", password="123456", role=UserRole.MODELER, full_name="顶级建模师", last_login=now)
        
        db.add_all([admin_user, analyst_user, modeler_user])
        db.commit() # 先提交，为了获取自动生成的 user.id
        db.refresh(modeler_user)
        logger.info("Mock users inserted successfully.")
        
        # --- 新增：为建模师插入一些初始场景数据 ---
        logger.info("Seeding initial mock scenes for modeler...")
        scenes = [
            DBScene(name="智慧城市中心区", status="published", owner_id=modeler_user.id),
            DBScene(name="滨江新区规划", status="draft", owner_id=modeler_user.id),
            DBScene(name="科技园区", status="published", owner_id=modeler_user.id)
        ]
        db.add_all(scenes)
        db.commit()
        logger.info("Mock scenes inserted successfully.")
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed_data()
