import logging
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
        users = [
            DBUser(username="admin", password="admin123", role=UserRole.ADMIN),
            DBUser(username="analyst", password="123456", role=UserRole.ANALYST),
            DBUser(username="modeler", password="123456", role=UserRole.MODELER),
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
