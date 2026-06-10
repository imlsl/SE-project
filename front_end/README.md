# 智能城市生成系统 (Smart City Generation System) - 前端框架

## 前端文件结构

```plaintext
frontend/
├── index.html                # 登录/注册页面（入口文件）
├── admin.html                # 系统管理员工作台
├── analyst.html              # 行业分析师工作台
├── modeler.html              # 场景建模师工作台
├── scene_edit.html           # 场景编辑器页面
├── profile.html              # 个人设置页面
├── css/
│   └── style.css             # 全局样式文件
├── js/
│   ├── auth.js               # 认证模块（登录/注册）
│   ├── common.js             # 通用工具函数
│   └── blenderBridge.js      # Blender插件桥接模块
└── role/
    ├── baseRole.js           # 角色UI基类
    ├── systemAdmin.js        # 系统管理员UI组件
    ├── industryAnalyst.js    # 行业分析师UI组件
    ├── sceneModeler.js       # 场景建模师UI组件
    └── sceneEditor.js        # 场景编辑器UI组件
```



## 各部分细节说明

### 页面与入口

- index.html：登录/注册入口，调用 auth.js 完成认证，登录后基于角色跳转至对应工作台。
- admin.html：系统管理员面板，侧重账号/角色/系统配置等入口展示。
- analyst.html：行业分析师面板，包含指标概览、活动列表、报告生成、导出与趋势查看。
- modeler.html：建模师面板，包含场景列表、资产库、进入编辑器入口。
- profile.html：个人设置页，查看/更新个人信息与修改密码。

### 样式与资源

- css/style.css：全局样式与基础布局风格，含面板、按钮、卡片、列表等通用样式。

### 核心脚本

- js/auth.js：登录/注册请求封装、token 与角色存取。
- js/common.js：通用工具与守卫，包括登录校验、角色跳转、提示展示等。
- js/blenderBridge.js：Blender/SCGS 插件桥接，封装生成任务、状态轮询与日志输出。

### 角色模块

- js/role/baseRole.js：统一 API 调用入口，自动注入认证头与错误处理。
- js/role/systemAdmin.js：管理员 UI 行为与数据绑定。
- js/role/industryAnalyst.js：分析师数据拉取、报告生成、导出与趋势接口适配。
- js/role/sceneModeler.js：建模师场景列表/删除、资产库读取与新增、进入场景编辑。
  
  

## 运行

**1.启动后端**

见backend/README.md

 **2.前端启动方式**

建议通过以下命令启动系统进行使用和开发，其中```<port>```为本地端口号，可自行设置，或者直接访问本地静态文件

```bash
python -m http.server <port>
```

之后可在```http://127.0.0.1:<port>/front_end/index.html```进入系统

> 不建议的方式：使用VS Code中的Live Server插件可快速搭建，但在某些界面会有交互的异常


