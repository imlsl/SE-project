# SCGS — AI驱动的3D城市生成器

SCGS 是一款 Blender 插件，基于 AI 自然语言指令，程序化生成包含道路、建筑、街道资产和天气效果的 3D 城市场景。

**版本:** 1.0.3 · **Blender:** 4.0+ · **作者:** SCGS

---

## 安装

1. 将 SCGS 文件夹放入 Blender 插件目录：
   ```
   .../Blender/4.1/scripts/addons/SCGS/
   ```
2. 启动 Blender → **编辑 → 偏好设置 → 插件**
3. 搜索 "SCGS"，启用插件

### LLM 配置（可选）

需要 DashScope（阿里云通义千问）API Key。在插件目录下创建 `.env` 文件：

```
DASHSCOPE_API_KEY=sk-你的密钥
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-max
```

未配置 API Key 时，AI 指令解析会自动回退到本地关键词匹配模式。

### 图像道路检测依赖

道路类型 3（图像提取）需要额外的 Python 包。在 Blender 自带的 Python 中安装：

```bash
# Windows
"C:\Program Files\Blender Foundation\Blender 4.1\4.1\python\bin\python.exe" -m pip install pillow scikit-learn opencv-python scikit-image networkx scipy sknw

# macOS / Linux
/path/to/blender/4.1/python/bin/python3.11 -m pip install pillow scikit-learn opencv-python scikit-image networkx scipy sknw
```

---

## 快速开始

1. 打开 **SCGS** 面板（3D 视图 → 按 N → 选择 SCGS 选项卡）
2. 输入描述，如 `请帮我在晴天生成一座现代城市`
3. 道路类型设为 `2`（网格布局）
4. 点击 **Generate City**
5. 等待约 30–60 秒，城市和天气将自动生成

---

## 面板布局

主面板（N 键 → SCGS 选项卡）：

```
┌──────────────────────────────────┐
│          [插件图标]               │
│     ***  Road Type  ***          │
│     [___________2___________]    │
│   ***  Description  ***          │
│  [自然语言描述输入框...]          │
│   ***  Manual Layout  ***        │
│  Vertices: [................]    │
│  Edges:    [................]    │
│  [Select Image] [Extract]       │
│       [图像预览]                  │
│ ┌────────────────────────────┐   │
│ │     Generate City           │   │
│ └────────────────────────────┘   │
│      ***  Edit  ***              │
│  [编辑指令输入框...]              │
│ ┌────────────────────────────┐   │
│ │      Edit City              │   │
│ └────────────────────────────┘   │
│ ── 场景模板配置 ──               │
│  模板: [0] [应用模板]            │
│ ── AI自然语言指令 ──             │
│  指令: [........] [执行]         │
│  示例: 树木1, 道路2, 座椅1       │
└──────────────────────────────────┘
```

---

## 功能详解

### 1. AI 城市生成

输入自然语言描述，LLM 自动提取关键信息：

| 参数 | 支持值 |
|------|--------|
| 城市类型 | classical type（古典）、ancient type（古代）、modern type（现代）、Taiwanese type（台湾）、industrial type（工业） |
| 天气 | sunny（晴天）、rainy（雨天）、snowy（雪天） |

生成流程：加载 ICity 模板 → 构建道路网络 → 放置街道资产 → 应用纹理 → 添加天气效果。

### 2. 道路布局类型

| 类型 | 说明 |
|------|------|
| `1` | 经典网格布局（16 顶点，17 条边） |
| `2` | 扩展网格布局（13 顶点，更大范围）— **默认** |
| `3` | 图像识别提取 — 从图片中自动检测道路网络（KMeans + 骨架化） |
| `4` | 手动布局 — 输入自定义顶点和边 |

### 3. 手动布局控制

主面板 **Manual Layout** 区域：

- **Vertices 输入框** — 逗号分隔的三维坐标，如 `(0,0,0),(50,0,0),(50,50,0),(0,50,0)`
- **Edges 输入框** — 逗号分隔的索引对，如 `(0,1),(1,2),(2,3),(3,0)`
- **Select Image** — 选择道路地图图片
- **Extract** — 从图片中自动提取道路网络，填入坐标和边字段

使用方式：输入顶点和边 → 点击 Generate City。手动内容有效时会自动覆盖其他道路类型。

### 4. 图像道路检测

适用于道路类型 `3` 或手动布局中的 Extract 按钮：

1. 选择道路地图图片（支持 JPG / PNG / BMP）
2. KMeans 聚类检测主色调
3. 颜色分层生成二值掩膜
4. 骨架化（scikit-image）提取道路中线
5. 构建图结构（sknw）
6. RDP 算法简化路径
7. KDTree 合并邻近节点
8. 输出顶点和边用于城市生成

### 5. 城市编辑

在编辑输入框输入指令，点击 **Edit City**：

| 功能 | 说明 |
|------|------|
| 切换晴天 `change_sunny_weather` | 清除所有天气效果，设为白天 |
| 切换雨天 `change_rain_weather` | 加载闪电、降雨和云层 |
| 切换雪天 `change_snow_weather` | 加载积雪地面和降雪 |
| 切换到白天 `turn_to_day` | 调整场景光照为白天 |
| 切换到夜晚 `turn_to_night` | 调整场景光照为夜晚 |
| 清洁道路 `make_road_clean` | 移除落叶、水洼、裂缝 |
| 脏污道路 `make_road_dirty` | 添加落叶和小垃圾 |

LLM 解析编辑指令，返回函数序列并依次执行。

### 6. 模板系统

预定义风格模板，一键同时设置树木、道路纹理和座椅类型。

| ID | 名称 | 树木 | 道路纹理 | 座椅 |
|----|------|------|----------|------|
| 0 | 现代风格 | Tree1_Tree_ICity_Default | ICity_Road 3 clean_Default | Bench1_Bench_ICity_Default |
| 1 | 古典风格 | Tree4_Tree_ICity_Default | ICity_Road 1 clean_Default | Bench4_Bench_ICity_Default |
| 2 | 绿色生态 | Tree8_Tree_ICity_Default | ICity_Road 8 dirty_Default | Bench8_Bench_ICity_Default |
| 3 | 工业风格 | Tree1_Tree_ICity_Default | ICity_Road 11 dirty_Default | Bench1_Bench_ICity_Default |
| 4 | 台湾风格 | Tree12_Tree_ICity_Default | ICity_Road 3 clean_Default | Bench11_Bench_ICity_Default |

**使用方式：**
- **模板选择输入框**：输入 `0`–`4` 或名称如 `现代风格`，点击 **应用模板**
- **AI 指令输入框**：输入 `模板4` 或 `选择模板0` 或 `古典风格`，点击 **执行**

### 7. AI 指令解析

**AI自然语言指令** 区域支持自由文本：

- `树木1, 道路2, 座椅1` — 显式指定类型和编号
- `模板4` — 应用预定义模板
- `现代风格` — 按模板名称匹配
- `帮我设置树木类型3` — 自然语言描述

优先使用 LLM 解析（DashScope），失败时回退到本地关键词/正则匹配。

### 8. 天气系统

| 天气 | 组成 |
|------|------|
| **雨天** | 闪电（WI Lightning）、降雨（WI Rain Fall）、云层 — 归入 `Rain Weather Collection` |
| **雪天** | 积雪地面（WI Snow Ground）、降雪（WI Snow Fall）— 归入 `Snow Weather Collection` |
| **晴天** | 移除所有天气集合，设为白天光照 |

天气对象从 `assets/Weather It.blend` 加载，支持修改器参数调节（密度、速率、大小等）。

### 9. 资产管理

**Append Assets** 面板（点击 `+` 按钮）支持：

- 按主题筛选（All / General / Chicago）
- City / Road 模式切换
- 按分类浏览：程序化建筑、公园预设、建筑预设、景观
- 按街道资产类型浏览：树木、灯光、长椅、护栏、服务设施、交通灯、标志、纹理、瑕疵
- 将选中资产追加到场景中

---

## 资产清单

### 街道资产

**树木**（14 种）：Tree1 ~ Tree14_Tree_ICity_Default，外加 Tree base 1–3

**长椅**（11 种）：Bench1 ~ Bench11_Bench_ICity_Default

**灯光**（6 种）：Light1 ~ Light6_Light_ICity_Default

**护栏**（7 种）：Bollard1 / 2 / 3 / 4 / 5 / 8 / 9_Bollard_Default_ICity

**服务设施**：配电箱 1–2、消防栓1、邮箱1、垃圾桶1–5

**交通灯**：Traffic light_Traffic light_ICity_Default

**标志**：Sign1_Sign_ICity_Default

### 道路材质

**路面纹理**（8 种）：

| 材质名称 | 风格 |
|----------|------|
| ICity_Road 1 clean_Default | 干净 1 |
| ICity_Road 2 clean_Default | 干净 2 |
| ICity_Road 3 clean_Default | 干净 3 |
| ICity_Road 4 clean_Default | 干净 4 |
| ICity_Road 2 dirty 2_Default | 脏污 2 |
| ICity_Road 7 dirty_Default | 脏污 7 |
| ICity_Road 8 dirty_Default | 脏污 8 |
| ICity_Road 11 dirty_Default | 脏污 11 |

另有道路标线：White line、White line dashed、Yellow line

**路缘**（4 种）：ICity_Curb grey / grey 2 / grey black / yellow black_Default

**人行道**（5 种）：ICity_Sidewalk 1 ~ 5_Default

### 建筑预设

- **摩天大楼**：Skyscraper01 / 02 / 03 / 04 / 06 / 08_Presets_ICity_Default
- **其他**：Court（法院）、Museum（博物馆）
- **按类别**：Skyscraper / Court / Market / Fire station / Police station / Hospital

### 公园与景观

| 类型 | 内容 |
|------|------|
| 公园 | Default_Park 01 ~ 04_ICity |
| 景观 | Default_Landscape 01 ~ 04_ICity |
| 程序化建筑 | Default building Procedural |

### 模板文件

| 文件 | 风格 |
|------|------|
| `ICity start.blend` | 原始默认 |
| `ICity start - GLASS.blend` | 玻璃建筑 |
| `ICity start - colorbuilding.blend` | 彩色建筑 |
| `ICity start - generatorcity_building.blend` | 程序化建筑（默认） |
| `ICity start - redroof.blend` | 红瓦屋顶 |

### 自定义资产

位于 `custom_assets/` 目录，每次生成城市时自动导入：

| 文件 | 内容 |
|------|------|
| `myroad.blend` | 自定义路面材质 "路面材质"（2D 资产） |
| `mylight.blend` | 自定义路灯 "路灯"（3D 资产） |
| `my_asphalt.png` | 自定义沥青纹理 |

---

## 场景集合

ICity 模板加载后创建以下集合层级：

| 集合名 | 用途 |
|--------|------|
| `ICity` | 根集合 |
| `ICity Assets` | 资产库（视口隐藏） |
| `ICity Base` | 基础网格 |
| `ICity Road` | 道路网格 |
| `ICity Road Boundry` | 道路边界 |
| `ICity Procedural ground` | 程序化地面 |
| `ICity building procedural base` | 建筑基础 |
| `ICity_Materials` | 材质持有对象 |
| `ICity_Tree` | 树木对象 |
| `ICity_Light` | 灯光对象 |
| `ICity_Bench` | 长椅对象 |
| `ICity_Bollard` | 护栏对象 |
| `ICity_Services` | 服务设施对象 |
| `ICity_Traffic light` | 交通灯对象 |
| `ICity_Sign` | 标志对象 |
| `ICity_Imperfection` | 路面瑕疵对象 |
| `ICity_Procedural` | 程序化建筑集合 |
| `ICity_Presets` | 建筑预设集合 |
| `ICity_Park` | 公园集合 |
| `ICity_Landscape` | 景观集合 |
| Rain Weather Collection | 雨天效果（云、闪电、雨） |
| Snow Weather Collection | 雪天效果（雪地、降雪） |

---

## 配置

### 插件偏好设置

在 Blender 偏好设置中：

- **Assets path** — 自定义资产目录，留空使用内置 `assets/` 文件夹
- **Read files** — 重新扫描资产目录并重建资产列表

### 环境变量（.env 文件）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DASHSCOPE_API_KEY` | — | DashScope API 密钥（LLM 功能必须） |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `DASHSCOPE_MODEL` | `qwen-max` | 模型名称 |

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| Shift+M | 打开插件偏好设置 |

---

## 文件结构

```
SCGS/
├── __init__.py                   # 主插件（约 5300 行）
│   ├── MainPathBuildings         # 图像道路检测
│   ├── SNA_OT_City_Generation    # 城市生成运算符
│   ├── SNA_OT_City_Edit          # 城市编辑运算符
│   ├── SNA_OT_Apply_Template     # 模板应用
│   ├── SNA_OT_Process_AI_Instruction  # AI 指令处理
│   ├── SNA_OT_ExtractLayout      # 图像提取到手动布局
│   ├── SNA_OT_SelectImage        # 图片文件选择
│   ├── SNA_PT_ICITY_EDITOR_6D34D # 主面板
│   └── SNA_PT_APPEND_PANEL_590A1 # 资产追加面板
├── scene_template_config.py      # 模板与 ASSET_NAMES 定义
├── weather.py                    # 天气效果加载
├── dashscope_client.py           # LLM API 客户端（OpenAI 兼容）
├── custom_assets/                # 用户扩展资产
│   ├── myroad.blend              # 自定义路面纹理
│   └── mylight.blend             # 自定义路灯
└── assets/
    ├── ICity start*.blend        # ICity 模板文件
    ├── Weather It.blend          # 天气效果
    ├── car.blend                 # 车辆网格
    ├── demo.blend                # 演示场景
    └── Assets/Default/           # 资产库
        ├── Building presets/     # 8 个建筑预设
        ├── Building landscape/   # 4 个景观
        ├── Park/                 # 4 个公园
        ├── Procedural/           # 程序化建筑
        ├── Road/                 # 道路资产与材质
        └── textures/             # PBR 纹理库
```


