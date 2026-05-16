frontend/
│
├── index.html                      # 登录/注册页面（入口文件）
├── admin.html                      # 系统管理员工作台
├── analyst.html                    # 行业分析师工作台
├── modeler.html                    # 场景建模师工作台
├── profile.html                    # 个人设置页面
│
├── css/
│   └── style.css                   # 全局样式文件
│
└── js/
    ├── auth.js                     # 认证模块（登录/注册）
    ├── common.js                   # 通用工具函数
    ├── blenderBridge.js            # Blender插件桥接模块
    │
    └── role/
        ├── baseRole.js             # 角色UI基类
        ├── systemAdmin.js          # 系统管理员UI组件
        ├── industryAnalyst.js      # 行业分析师UI组件
        └── sceneModeler.js         # 场景建模师UI组件