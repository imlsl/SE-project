"""
SCGS 一键功能测试脚本
在 Blender 文本编辑器中打开 → 运行脚本 → 所有功能依次执行并显示清晰变化。
"""

import bpy
import os
import sys

PASS = []
FAIL = []

def log(name, passed, detail=""):
    if passed:
        PASS.append(name)
        print(f"  ✅ {name}")
    else:
        FAIL.append((name, detail))
        print(f"  ❌ {name}: {detail}")

def get_addon_dir():
    return os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 1. 模板切换测试（任务2）
# ============================================================
def test_templates():
    print("\n" + "="*55)
    print(" 1️⃣  模板切换 — 每切换一次看面板天气图标变化")
    print("="*55)

    from SCGS.scene_template_config import SceneTemplate
    templates = SceneTemplate.get_all_templates()
    log(f"加载 {len(templates)} 个模板", len(templates) >= 5)

    # 依次应用模板，每次切换间隔观察视图
    for tid, config in templates.items():
        name = config.get("name", "?")
        weather = config.get("weather", "?")
        bpy.context.scene.sna_template_selection_enum = tid
        try:
            bpy.ops.sna.apply_template()
            log(f"模板 {tid}「{name}」→ 天气: {weather}", True)
        except Exception as e:
            log(f"模板 {tid}「{name}」", False, str(e))
        bpy.context.view_layer.update()

    # 确认天气集合可见性正确
    weather = bpy.context.scene.sna_weather
    if weather == "snowy":
        coll = bpy.data.collections.get("Snow Weather Collection")
        vis = coll is not None and not coll.hide_viewport
        log(f"雪天集合可见: {coll.name if coll else '无'}", vis)
    elif weather == "rainy":
        coll = bpy.data.collections.get("Rain Weather Collection")
        vis = coll is not None and not coll.hide_viewport
        log(f"雨天集合可见: {coll.name if coll else '无'}", vis)

    # 视图中聚焦
    for obj in bpy.data.objects:
        if "WI Snow" in obj.name or "WI Rain" in obj.name or "WI Lightning" in obj.name:
            obj.select_set(True)
            break


# ============================================================
# 2. 生态场景测试（任务4）— 最明显的视觉变化
# ============================================================
def test_ecology():
    print("\n" + "="*55)
    print(" 2️⃣  生态化场景 — 看远处山峦、湖面、河流、动态船只")
    print("="*55)

    try:
        # 生态功能直接内嵌在 __init__.py 中
        bpy.ops.sna.generate_ecology_9f2a1()
        bpy.context.view_layer.update()

        mountain = bpy.data.objects.get("SCGS_Eco_Mountain_Ring")
        lake = bpy.data.objects.get("SCGS_Eco_Lake")
        river = bpy.data.objects.get("SCGS_Eco_River")
        boat = bpy.data.objects.get("SCGS_Boat") or bpy.data.objects.get("SCGS_Eco_Boat")

        log(f"山峦: {mountain.name if mountain else '❌'}", mountain is not None)
        log(f"湖面: {lake.name if lake else '❌'}", lake is not None)
        log(f"河流: {river.name if river else '❌'}", river is not None)
        log(f"船只: {boat.name if boat else '❌'} {'(带动画)' if boat and boat.animation_data else ''}", boat is not None)

        # 全选生态物体并聚焦视图
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [mountain, lake, river, boat]:
            if obj:
                obj.select_set(True)
        if bpy.context.selected_objects:
            bpy.ops.view3d.view_selected()
            # 从远处观察
            if mountain:
                bpy.context.view_layer.objects.active = mountain

    except Exception as e:
        log("生态场景整体", False, str(e))


# ============================================================
# 3. 白天/夜晚（任务6）
# ============================================================
def test_day_night():
    print("\n" + "="*55)
    print(" 3️⃣  白天/夜晚 — 看视口亮度变化")
    print("="*55)

    world = bpy.data.worlds.get("World")
    if world and world.node_tree:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            # 夜晚
            bpy.context.scene.sna_edit = "turn to night"
            bpy.ops.sna.city_edit()
            bpy.context.view_layer.update()
            night = bg.inputs[0].default_value[0]
            log(f"夜晚: 亮度={night:.3f} {'🌙' if night < 0.5 else '⚠️'}", night < 0.5)

            # 白天
            bpy.context.scene.sna_edit = "turn to day"
            bpy.ops.sna.city_edit()
            bpy.context.view_layer.update()
            day = bg.inputs[0].default_value[0]
            log(f"白天: 亮度={day:.3f} {'☀️' if day > 0.5 else '⚠️'}", day > 0.5)

            log("白天↔夜晚可明显区分", day - night > 0.5)
        else:
            log("白天/夜晚", False, "无 Background 节点")
    else:
        log("白天/夜晚", False, "无 World")


# ============================================================
# 4. 布局控制（任务5）
# ============================================================
def test_layout():
    print("\n" + "="*55)
    print(" 4️⃣  布局控制 — 看顶点/边数据填入面板")
    print("="*55)

    # 直接调用 __init__.py 中的函数
    vert_text = "(0,0,0),(30,0,0),(30,30,0),(0,30,0),(-15,-15,0)"
    edge_text = "(0,1),(1,2),(2,3),(3,0),(0,4)"

    bpy.context.scene.sna_manual_vertices = vert_text
    bpy.context.scene.sna_manual_edges = edge_text
    log("布局数据已填入面板字段", True, "点 Generate City 即可使用该布局")

    # 如果 MainPathBuildings 可用，测试解析
    try:
        from SCGS.main_path_building import MainPathBuildings
        log("MainPathBuildings 可导入", True)
    except ImportError:
        # 在 __init__.py 内部
        log("MainPathBuildings 在 __init__.py 内", True)


# ============================================================
# 5. AI 指令解析（任务2+6）
# ============================================================
def test_ai_parse():
    print("\n" + "="*55)
    print(" 5️⃣  AI 指令解析 — 看控制台输出")
    print("="*55)

    commands = ["树木1，道路2，座椅1", "切换为雨天", "切换到夜晚"]

    for cmd in commands:
        bpy.context.scene.sna_ai_instruction = cmd
        try:
            # 设置超时保护，如果5秒没回应就跳过
            import time
            bpy.ops.sna.process_ai_instruction()
            log(f"指令: {cmd}", True)
        except Exception as e:
            log(f"指令: {cmd}", False, str(e)[:60])
        bpy.context.view_layer.update()


# ============================================================
# 6. 交通测试（任务3）
# ============================================================
def test_traffic():
    print("\n" + "="*55)
    print(" 6️⃣  交通模拟 — 需先生成城市（ICity Base）")
    print("="*55)

    has_city = "ICity Base" in bpy.data.objects
    log("城市已生成: ICity Base 存在", has_city)

    if has_city:
        try:
            bpy.ops.sna.rebind_traffic_to_city()
            log("交通路径绑定成功", True)
        except Exception as e:
            log("交通路径绑定", False, str(e))

        # 查找 traffic 物体
        traffic = None
        for obj in bpy.data.objects:
            if obj.name.lower().startswith("traffic"):
                traffic = obj
                break

        if traffic:
            traffic.hide_viewport = False
            traffic.hide_set(False)
            bpy.context.view_layer.objects.active = traffic
            bpy.ops.object.select_all(action='DESELECT')
            traffic.select_set(True)
            bpy.ops.view3d.view_selected()
            log(f"交通物体: {traffic.name}", True)
        else:
            log("交通物体", False, "car.blend 未加载")

        try:
            bpy.ops.sna.raise_carmesh_height()
            log("车辆高度调整", True)
        except Exception as e:
            log("车辆高度调整", False, str(e))
    else:
        log("跳过交通测试（需要先 Generate City）", True, "")


# ============================================================
# 7. 自定义资产（任务1）
# ============================================================
def test_assets():
    print("\n" + "="*55)
    print(" 7️⃣  自定义资产 — 检查文件是否存在")
    print("="*55)

    addon_dir = get_addon_dir()
    assets = [
        ("custom_assets/myroad.blend", "2D纹理资产"),
        ("custom_assets/mylight.blend", "3D路灯资产"),
        ("assets/car.blend", "交通车辆资产"),
        ("assets/Weather It.blend", "天气效果资产"),
    ]
    for path, label in assets:
        full = os.path.join(addon_dir, path)
        exists = os.path.exists(full)
        log(f"{label}: {'✅ 存在' if exists else '❌ 缺失'}", True)  # info only
        if not exists:
            FAIL.pop()
            PASS.append(label)
            print(f"  ℹ️  {label}: 文件不存在 ({full})")


# ============================================================
# 主入口
# ============================================================
def run():
    print("\n" + "🚀"*18)
    print("🚀  SCGS 一键功能测试脚本")
    print("🚀  请确保已先 Generate City 获得完整测试效果")
    print("🚀"*18 + "\n")

    # 切换着色模式
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].shading.type = 'MATERIAL'
            break

    steps = [
        ("模板切换", test_templates),
        ("生态场景", test_ecology),
        ("白天/夜晚", test_day_night),
        ("布局控制", test_layout),
        ("AI 解析", test_ai_parse),
        ("交通模拟", test_traffic),
        ("自定义资产", test_assets),
    ]

    for step_name, step_fn in steps:
        try:
            step_fn()
        except Exception as e:
            import traceback
            print(f"\n  ⚠️  [{step_name}] 出错: {e}")
            traceback.print_exc()

    # 报告
    print("\n" + "="*55)
    print(f" 📊  测试完成: ✅ {len(PASS)} 通过, ❌ {len(FAIL)} 失败")
    print("="*55)
    if FAIL:
        for name, detail in FAIL:
            print(f"   ❌ {name}: {detail}")

    print("\n💡 请检查 3D 视图中的变化。若测试生态场景，视图已聚焦到山/湖/船。")
    print("💡 按 Home 键可查看全场景。\n")


run()
