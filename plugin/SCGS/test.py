import bpy
import bmesh


# # 设置某一块是程序化城市
# bpy.context.scene.sna_citystreet = 'City'
# bpy.ops.sna.filter_presets_fb5a4()
# bpy.ops.sna.park_filter_5a7a2()
# bpy.ops.sna.procedural_building_filter_05bed()
# bpy.ops.sna.landscape_filter_0bf89()
# bpy.context.scene.sna_city_space_type = 'Procedural'
# bpy.context.scene.sna_procedural_building_browser = 'Procedural building_Default_ICity'
# bpy.ops.mesh.attribute_set(value_int=0)
# bpy.ops.mesh.attribute_set(value_int=0)
# bpy.ops.sna.city_apply_dae66()

# bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
# bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.0748147, 0.0748147, 0.0748147, 1)

# # 让路面变干净
# def make_road_clean():
#     # 路边落叶间距
#     bpy.data.node_groups["Road 2"].nodes["Group.012"].inputs[2].default_value = 10000
#     #路沿落叶密度
#     bpy.data.node_groups["Road 2"].nodes["Group.054"].inputs[2].default_value = 0
#     bpy.data.node_groups["Road 2"].nodes["Value"].outputs[0].default_value = 0
#     bpy.data.node_groups["Road 2"].nodes["Value.001"].outputs[0].default_value = 0
#     # 水洼密度
#     bpy.data.node_groups["Road 2"].nodes["Group"].inputs[2].default_value = 0
#     # 路面裂缝密度
#     bpy.data.node_groups["Road 2"].nodes["Group.013"].inputs[2].default_value = 0
#
# def make_road_dirty():
#     bpy.data.node_groups["Road 2"].nodes["Group.012"].inputs[2].default_value = 2
#     bpy.data.node_groups["Road 2"].nodes["Group.054"].inputs[2].default_value = 0.2
#     bpy.data.node_groups["Road 2"].nodes["Value"].outputs[0].default_value = 10
#     bpy.data.node_groups["Road 2"].nodes["Value.001"].outputs[0].default_value = 10
#     bpy.data.node_groups["Road 2"].nodes["Group"].inputs[2].default_value = 0
#     bpy.data.node_groups["Road 2"].nodes["Group.013"].inputs[2].default_value = 0
#
# make_road_clean()
# # make_road_dirty()


# import bpy
# import bmesh
#
# # 定义顶点和边
# vertices = [(-200, 200, 0), (-200, 50, 0), (-50, 50, 0), (-50, 100, 0), (-50, 200, 0), (200, 200, 0),
#             (200, 100, 0), (50, 100, 0), (50, -100, 0), (50, -200, 0), (200, -200, 0), (-200, -100, 0),
#             (-200, -200, 0)]
# edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (4, 5), (5, 6), (6, 7), (3, 7), (7, 8), (8, 9),
#          (9, 10), (10, 6), (8, 11), (1, 11), (11, 12), (9, 12)]
#
# # 创建一个新的网格
# mesh = bpy.data.meshes.new(name="road")
#
# # 使用BMesh来创建顶点和边
# bm = bmesh.new()
# for v in vertices:
#     bm.verts.new(v)
# bm.verts.ensure_lookup_table()
#
# for e in edges:
#     bm.edges.new((bm.verts[e[0]], bm.verts[e[1]]))
#
# # 将BMesh数据写入网格
# bm.to_mesh(mesh)
# bm.free()
#
# # 创建一个新的对象并将其链接到场景中
# obj = bpy.data.objects.new("road", mesh)
# bpy.context.collection.objects.link(obj)
#
# # 选中并激活新创建的对象
# bpy.ops.object.select_all(action='DESELECT')
# obj.select_set(True)
# bpy.context.view_layer.objects.active = obj
#
# print("对象 'road' 创建完成！")
# bpy.data.node_groups["节点城市"].nodes["Object Info.001"].inputs[0].default_value = bpy.data.objects["road"]


import bpy
import os

# 定义Blender文件路径
car_file_path = r"C:\Users\VR\AppData\Roaming\Blender Foundation\Blender\4.1\scripts\addons\SCGS\assets\car.blend"

# 导入traffic物体
if os.path.exists(car_file_path):
    try:
        # 使用完整路径导入traffic物体
        bpy.ops.wm.append(
            filepath=f"{car_file_path}\\Object\\traffic",
            directory=f"{car_file_path}\\Object\\",
            filename="traffic"
        )
        print("成功导入 traffic 物体")
    except Exception as e:
        print(f"导入 traffic 物体失败: {e}")
else:
    print(f"错误: 文件不存在 - {car_file_path}")

# 导入base物体
if os.path.exists(car_file_path):
    try:
        # 使用完整路径导入base物体
        bpy.ops.wm.append(
            filepath=f"{car_file_path}\\Object\\base",
            directory=f"{car_file_path}\\Object\\",
            filename="base"
        )
        print("成功导入 base 物体")
    except Exception as e:
        print(f"导入 base 物体失败: {e}")
else:
    print(f"错误: 文件不存在 - {car_file_path}")

# 导入"车辆"集合及其所有子物体
if os.path.exists(car_file_path):
    try:
        # 使用完整路径导入"车辆"集合
        bpy.ops.wm.append(
            filepath=f"{car_file_path}\\Collection\\车辆",
            directory=f"{car_file_path}\\Collection\\",
            filename="车辆"
        )

        # 确认集合是否成功导入
        if "车辆" in bpy.data.collections:
            vehicle_collection = bpy.data.collections["车辆"]
            print(f"成功导入 '车辆' 集合，包含 {len(vehicle_collection.all_objects)} 个物体")

            # 确保集合中的物体在场景中可见
            for obj in vehicle_collection.all_objects:
                if obj.name not in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.link(obj)

            print("'车辆' 集合中的物体:")
            for obj in vehicle_collection.objects:
                print(f"  - {obj.name}")
        else:
            print("未找到 '车辆' 集合或导入失败")
    except Exception as e:
        print(f"导入 '车辆' 集合失败: {e}")
else:
    print(f"错误: 文件不存在 - {car_file_path}")
