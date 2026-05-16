import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)

if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.database import engine, Base, SessionLocal
from app.models.user import DBUser, UserRole

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Creating database tables...")
    # 根据模型自动创建所有的表 
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
        # 修改：为初始化的 Mock 用户赋予初始昵称
        users = [
            DBUser(username="admin", password="123456", role=UserRole.ADMIN, full_name="系统总管"),
            DBUser(username="analyst", password="123456", role=UserRole.ANALYST, full_name="核心分析师"),
            DBUser(username="modeler", password="123456", role=UserRole.MODELER, full_name="顶级建模师"),
        ]
        db.add_all(users)
        db.commit()
        logger.info("Mock users inserted successfully.")
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    seed_data()
