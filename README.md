# 智能城市生成系统 (Smart City Generation System) - 后端框架

本项目提供了一个基于 **FastAPI（Python）** 构建的智能城市场景生成系统后端服务。该后端主要满足前端的多角色登录、基于角色的工作台数据、系统管理、行业分析、场景建模，以及核心 Blender 城市场景生成插件的交互功能。

## 目录结构

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth.py         # 认证接口，处理多角色登录与跳转逻辑
│   │   ├── admin.py        # 系统管理员接口，提供用户管理、日志、运行时间、系统配置与API统计
│   │   ├── analyst.py      # 行业分析师接口，提供数据大盘、行业指标、报告生成、数据导出与趋势查询
│   │   ├── modeler.py      # 场景建模师接口，提供场景项目、资产库、布局/草图处理与LLM指令解析
│   │   └── blender.py      # Blender生成插件的核心业务接口
│   ├── models/
│   │   ├── user.py         # 用户数据模型定义(包含UserRole等)
│   │   └── scene.py        # 场景数据模型定义(场景列表与关联用户)
│   ├── services/
│   │   └── blender_service.py # 与Blender插件的具体通信和调度服务逻辑
│   ├── database.py         # 数据库连接与配置
│   ├── admin_logger.py     # 生成系统管理员日志
│   └── main.py             # 整个FastAPI应用的入口与路由注册
├── tools/
│   └── init_db.py          # 数据库初始化脚本(自动建表与插入测试数据)
├── data/                   # 运行时数据，如系统运行时间、系统配置、建模资产JSON
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

### 2. 系统管理员模块 (System Admin Dashboard)

在 `app/api/admin.py` 及 `app/admin_logger.py` 中实现了面向系统管理员的核心服务：

* **全局用户管理**：提供创建、修改、删除和查询用户的权限 (基于角色的高权限校验)。
* **日志与审计**：独立的 `admin_operations.log` 文件记录管理行为，支持定期轮转（每天备份）并配置自动清理策略，避免日志膨胀。`/admin/users/system/logs` 接口，以便在前端实时提取查看或清楚日志条目。
* **系统运行监控**：提供接口 `/admin/users/system/uptime` 可实时获取系统启动时长和当前服务器时间，供前端仪表盘同步展示。
* **系统配置**：提供 `/admin/users/system/settings` 的读取与保存能力，对应前端的渲染质量、自动备份间隔、数据统计分析开关。
* **API统计**：提供 `/admin/users/system/api-stats`，汇总用户数、场景数、日志条目数等统计信息，支撑管理员统计卡片。

### 3. 行业分析师模块 (Industry Analyst Dashboard)

在 `app/api/analyst.py` 中实现了面向行业分析师的数据服务：

* **大盘监控**：提供实时的城市项目数、活跃场景、预测准确率等核心业务指标。
* **行业分析**：支持交通运输、能源管理、环境保护等细分领域的健康度打分与趋势分析。
* **报告系统**：提供活动日志追踪，并支持通过 `/analyst/reports/generate` 触发生成行业周报。
* **数据导出与趋势查询**：提供 `/analyst/data/export` 和 `/analyst/trends`，对应前端“导出数据”和“查看趋势”按钮。

### 4. 场景建模师模块 (Scene Modeler Workspace)

在 `app/api/modeler.py` 中实现了面向建模师的场景与项目管理服务：

* **场景项目管理**：支持用户个人的 3D 场景项目创建、查询、更新和删除（CRUD），状态区分草稿与已发布。
* **资产库管理**：提供 `/modeler/assets` 的资产列表读取与新增能力，对应前端资产库刷新和上传入口。当前轻量实现使用 `data/modeler_assets.json` 存储。
* **布局与草图处理**：提供 `/modeler/layout/apply` 和 `/modeler/sketch/process`，接收前端点集布局和草图文件名，返回可交给 Blender 侧继续处理的节点/道路参数。
* **多模态大模型指令集成 (LLM Command)**：新增自然语言转控制指令接口，接收建模师的日常语义（如“在十字路口添加智能路灯”），转化为 Blender 插件所需的标准化参数。

### 5. 前端已实现需求的后端补齐

本次后端补齐了前端工作台中已出现但原先仍依赖模拟数据或“开发中”提示的功能：

* 管理员工作台：系统配置保存、系统配置读取、API统计。
* 行业分析师工作台：周报生成返回结构化报告信息、数据导出、趋势查询。
* 场景建模师工作台：场景更新、资产库读取/新增、布局点集应用、草图处理。

这些接口均已注册到 FastAPI 应用中，可以通过 `http://127.0.0.1:8000/docs` 查看和调试。

### 6. 插件系统入口跳转控制 (前端登录后)

后端 `/auth/login` 接口 (`app/api/auth.py`) 根据身份验证结果（即不同的 `UserRole`），自动返回给前端对应的 `redirect_url`。例如：

* 管理员跳转至仪表盘 `/admin/dashboard`
* 分析师跳转至分析工具系统 `/plugin/analysis-tool`
* 建模师跳转至城市场景生成系统 `/plugin/blender-generator`
通过此设计完成鉴权与插件入口的动态路由机制。

### 7. 连接 Blender 中已安装的 SCGS 插件系统

在 app/services/blender_service.py 和 app/api/blender.py 中实现了连接 Blender/SCGS 的核心接口：

* 提供 /blender/diagnostics，用于检查 Blender 是否可启动、SCGS 插件是否可启用，并列出 sna.* 相关的 apy.ops 候选算子。
* 提供 /blender/generate、/blender/status/{task_id}、/blender/download/{task_id}，前端建模师通过下发 description、emplate_id、
oad_type、weather、manual_vertices、manual_edges、scale、style 等参数触发 SCGS 生成。
* 默认启用 Blender 中已安装的 SCGS 模块，并默认调用 sna.city_generation。
* 任务状态会持久化到 data/blender_tasks.json，生成结果保存到 data/exports/。

.env 中的 SCGS 配置示例：

`env
BLENDER_URL=D:/Blender/Blender Foundation/Blender 4.1/blender.exe
BLENDER_PLUGIN_MODULE=SCGS
BLENDER_GENERATE_OPERATOR=sna.city_generation
BLENDER_EDIT_OPERATOR=sna.city_edit
BLENDER_OPERATOR_FILTER=sna
`

如果你的真实 SCGS 插件模块名或算子名和默认值不同，先调用 /blender/diagnostics，根据返回的 addons 和 operators 调整上述配置。

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
