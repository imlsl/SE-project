# 智能城市生成系统 (Smart City Generation System) - 后端框架

本项目提供了一个基于 **FastAPI（Python）** 构建的智能城市场景生成系统的后端服务框架。该后端主要满足前端的多角色登录、基于角色的插件入口跳转控制，以及核心的 Blender 城市场景生成插件的交互功能。

## 目录结构

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth.py         # 认证接口，处理多角色登录与跳转逻辑
│   │   ├── admin.py        # 系统管理员接口，提供完整的用户增删改查(CRUD)
│   │   ├── analyst.py      # 行业分析师接口，提供数据大盘、行业指标与报告生成
│   │   ├── modeler.py      # 场景建模师接口，提供场景项目管理与LLM指令解析
│   │   └── blender.py      # Blender生成插件的核心业务接口
│   ├── models/
│   │   ├── user.py         # 用户数据模型定义(包含UserRole等)
│   │   └── scene.py        # 场景数据模型定义(场景列表与关联用户)
│   ├── services/
│   │   └── blender_service.py # 与Blender插件的具体通信和调度服务逻辑
│   ├── database.py         # 数据库连接与配置
│   └── main.py             # 整个FastAPI应用的入口与路由注册
├── tools/
│   └── init_db.py          # 数据库初始化脚本(自动建表与插入测试数据)
├── requirements.txt
├── .gitignore
└── README.md

```

## 功能与系统要求实现

### 1. 多角色登录系统 (前端登录界面支持)

系统主要支持三种用户角色的认证与授权 (`app/models/user.py`)：

* **系统管理员 (System Administrator)**
* **行业分析师 (Industry Analyst)**
* **场景建模师 (Scene Modeler)**

### 2. 行业分析师模块 (Industry Analyst Dashboard)

在 `app/api/analyst.py` 中实现了面向行业分析师的数据服务：

* **大盘监控**：提供实时的城市项目数、活跃场景、预测准确率等核心业务指标。
* **行业分析**：支持交通运输、能源管理、环境保护等细分领域的健康度打分与趋势分析。
* **报告系统**：提供活动日志追踪，并支持触发生成季度/月度的行业分析报告。

### 3. 场景建模师模块 (Scene Modeler Workspace)

在 `app/api/modeler.py` 中实现了面向建模师的场景与项目管理服务：

* **场景项目管理**：支持用户个人的 3D 场景项目创建、查询和删除（CRUD），状态区分草稿与已发布。
* **多模态大模型指令集成 (LLM Command)**：新增自然语言转控制指令接口，接收建模师的日常语义（如“在十字路口添加智能路灯”），转化为 Blender 插件所需的标准化参数。

### 4. 插件系统入口跳转控制 (前端登录后)

后端 `/auth/login` 接口 (`app/api/auth.py`) 根据身份验证结果（即不同的 `UserRole`），自动返回给前端对应的 `redirect_url`。例如：

* 管理员跳转至仪表盘 `/admin/dashboard`
* 分析师跳转至分析工具系统 `/plugin/analysis-tool`
* 建模师跳转至城市场景生成系统 `/plugin/blender-generator`
通过此设计完成鉴权与插件入口的动态路由机制。

### 5. 连接 Blender 城市场景生成插件系统

在 `app/services/blender_service.py` 和 `app/api/blender.py` 中实现了连接 Blender 系统的核心接口：

* 提供场景构建任务调度API，前端建模师通过下发城市参数（如 `scale`, `style` 等），触发后端的Blender插件自动运行。
* 底层实现可通过 **headless运行Blender启动Python脚本生成**，或者**微服务/Websocket/RPC形式与常驻Blender实例通讯**完成场景建模自动化。

## 安装与运行

确保你的环境中已经安装了 Python 3.9+ 以及 **MySQL** 数据库。

1. **安装依赖:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **数据库配置与初始化:**
   - 确保你的 MySQL 服务已启动。
   - 在 MySQL 中创建一个数据库（并且根据需要在 `.env` 或者`app/database.py` 中修改 `DATABASE_URL` 配合你自己的用户名密码）。
   - 运行初始化脚本自动生成表并插入测试用户/场景数据：
   ```bash
   python init_db.py
   ```

3. **运行服务:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **接口文档:**
   服务成功启动后在浏览器打开 `http://127.0.0.1:8000/docs` 即可查看 Swagger UI 互动式API文档。
