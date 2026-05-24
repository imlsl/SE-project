import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 确保 logs 目录存在，位于 backend/logs
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 设置管理员专用的 Logger
admin_logger = logging.getLogger("admin_logger")
admin_logger.setLevel(logging.INFO)

# 使用 TimedRotatingFileHandler
# when="D" 表示每天轮转一次
# backupCount=7 表示保留7天，超过7天的旧日志会被自动删除
log_file = os.path.join(LOG_DIR, "admin_operations.log")
handler = TimedRotatingFileHandler(
    filename=log_file,
    when="D",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)

formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

# 避免重复添加 handler
if not admin_logger.handlers:
    admin_logger.addHandler(handler)
