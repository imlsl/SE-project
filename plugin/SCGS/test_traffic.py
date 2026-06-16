"""
交通功能测试脚本
在 Blender 文本编辑器中打开 → 运行 → 测试车辆功能
"""

import bpy
import os
# Blender 文本编辑器运行时代码的 __file__ 解析不正确，用 addon 路径
ADDON_DIR = r"D:\SteamLibrary\steamapps\common\Blender\4.1\scripts\addons\SCGS"


def log(msg):
    print(f"[SCGS Traffic Test] {msg}")


def run():
    print("\n" + "🚗"*20)
    print("🚗  SCGS 交通功能测试")
    print("🚗"*20 + "\n")

    # 1. 检查 car.blend 是否存在
    car_path = os.path.join(ADDON_DIR, "assets", "car.blend")
    if os.path.exists(car_path):
        log(f"✅ car.blend 存在 ({os.path.getsize(car_path)//1024} KB)")
    else:
        log("❌ car.blend 不存在！路径: " + car_path)
        return

    # 2. 检查场景中是否有城市道路
    has_road = "ICity Road" in bpy.data.objects
    has_base = "ICity Base" in bpy.data.objects
    if has_road or has_base:
        log(f"✅ 城市道路存在: ICity Road={has_road}, ICity Base={has_base}")
    else:
        log("❌ 未检测到城市！请先点 Generate City 生成城市")
        return

    # 3. 检查是否有旧的 car_mesh 集合
    old_car_mesh = "car_mesh" in bpy.data.collections
    if old_car_mesh:
        log("✅ car_mesh 集合已存在")

    # 4. 执行重新绑定交通路径
    log("\n🔄 正在绑定交通路径...")
    try:
        bpy.ops.sna.rebind_traffic_to_city()
        log("✅ 交通路径绑定成功")
    except Exception as e:
        log(f"❌ 交通路径绑定失败: {e}")

    # 5. 查找 traffic 物体
    bpy.ops.object.select_all(action='DESELECT')
    traffic_obj = None
    for obj in bpy.data.objects:
        if obj.name.lower().startswith("traffic"):
            traffic_obj = obj
            break

    if traffic_obj:
        log(f"✅ traffic 物体: {traffic_obj.name}")
        log(f"   位置: ({traffic_obj.location.x:.2f}, {traffic_obj.location.y:.2f}, {traffic_obj.location.z:.2f})")
        log(f"   缩放: ({traffic_obj.scale.x:.2f}, {traffic_obj.scale.y:.2f}, {traffic_obj.scale.z:.2f})")

        # 设置为可见并选中
        traffic_obj.hide_viewport = False
        traffic_obj.hide_set(False)
        traffic_obj.select_set(True)
        bpy.context.view_layer.objects.active = traffic_obj
        log("✅ traffic 已设为可见并选中")

        # 检查修改器
        has_nodes = False
        for mod in traffic_obj.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                has_nodes = True
                ng = mod.node_group
                # 检查 Object Info 节点
                obj_info = ng.nodes.get("Object Info.001") or ng.nodes.get("Object Info")
                if obj_info:
                    path_obj = obj_info.inputs[0].default_value
                    log(f"✅ 几何节点修改器存在, 路径绑定: {path_obj.name if path_obj else '❌ 空'}")
                else:
                    log("❌ 几何节点中未找到 Object Info 节点")
                break
        if not has_nodes:
            log("❌ traffic 没有几何节点修改器")
    else:
        log("❌ 未找到 traffic 物体")

    # 6. 查找 path_source 物体
    path_src = bpy.data.objects.get("path_source")
    if path_src:
        vert_count = len(path_src.data.vertices) if path_src.data else 0
        edge_count = len(path_src.data.edges) if path_src.data else 0
        log(f"✅ path_source 路径物体: {vert_count} 顶点, {edge_count} 边")
        # 输出顶点范围
        if path_src.data and vert_count > 0:
            xs = [v.co.x for v in path_src.data.vertices]
            ys = [v.co.y for v in path_src.data.vertices]
            zs = [v.co.z for v in path_src.data.vertices]
            log(f"   X范围: {min(xs):.1f} ~ {max(xs):.1f}")
            log(f"   Y范围: {min(ys):.1f} ~ {max(ys):.1f}")
            log(f"   Z范围: {min(zs):.1f} ~ {max(zs):.1f}")
            log(f"   中心: ({(min(xs)+max(xs))/2:.1f}, {(min(ys)+max(ys))/2:.1f})")
    else:
        log("❌ path_source 不存在（路径提取可能失败）")

    # 7. 查找车辆集合
    vehicle_coll = None
    for coll in bpy.data.collections:
        if "车辆" in coll.name or "vehicle" in coll.name.lower():
            vehicle_coll = coll
            break
    if vehicle_coll:
        log(f"✅ 车辆集合: {vehicle_coll.name} ({len(vehicle_coll.all_objects)} 个物体)")
        # 显示车辆集合
        vehicle_coll.hide_viewport = False
    else:
        log("ℹ️ 无独立车辆集合（车辆由几何节点生成实例）")

    # 8. 调整车辆高度
    log("\n🔄 正在调整车辆高度...")
    try:
        bpy.ops.sna.raise_carmesh_height()
        log("✅ 车辆高度已调整")
    except Exception as e:
        log(f"❌ 调整车辆高度失败: {e}")

    # 9. 聚焦视图
    if traffic_obj:
        bpy.ops.object.select_all(action='DESELECT')
        traffic_obj.select_set(True)
        bpy.context.view_layer.objects.active = traffic_obj
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces[0].shading.type = 'MATERIAL'
                break

    print("\n" + "🚗"*20)
    log("测试完成！")
    print("🚗"*20 + "\n")


run()
