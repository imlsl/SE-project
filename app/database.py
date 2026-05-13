import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# MySQL数据库连接URL，您可以将其配置在.env文件中
# 格式: mysql+pymysql://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 创建引擎
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 创建SessionLocal类用于生成数据库会话实例
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类，所有ORM模型继承于此
Base = declarative_base()

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
