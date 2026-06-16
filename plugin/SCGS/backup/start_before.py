# from Mycity import start_code
import bpy
import bmesh
from Mycity.weather import *
########################################################代码控制部分###############################################

def clear_all_vertices(obj_name):
    """
    清除指定对象中的所有点（顶点）。
    参数:
        obj_name (str): 对象的名称。
    """
    # 确保对象存在
    if obj_name not in bpy.data.objects:
        print(f"对象 '{obj_name}' 不存在！")
        return
    obj = bpy.data.objects[obj_name]
    # 切换到编辑模式
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    # 获取网格数据
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    # 删除所有顶点
    bmesh.ops.delete(bm, geom=bm.verts, context='VERTS')
    # 更新网格数据
    bmesh.update_edit_mesh(mesh)
    # 切换回对象模式
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"对象 '{obj_name}' 中的所有点已被清除。")

def add_vertices_and_edges(obj_name, vertices, edges):
    """
    在指定对象中添加顶点并创建边。
    参数:
        obj_name (str): 对象的名称。
        vertices (list of tuples): 顶点的坐标列表，每个顶点是一个 (x, y, z) 元组。
        edges (list of tuples): 边的索引列表，每条边是一个 (index1, index2) 元组。
    """
    # 确保对象存在
    if obj_name not in bpy.data.objects:
        raise ValueError(f"对象 '{obj_name}' 不存在于场景中！")
    obj = bpy.data.objects[obj_name]
    # 切换到对象模式并确保对象是活动对象
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = obj
    # 切换到编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    # 使用 BMesh 操作网格数据
    bm = bmesh.from_edit_mesh(obj.data)
    # 添加顶点
    bm_verts = [bm.verts.new(v) for v in vertices]
    # 创建边
    for edge in edges:
        bm.edges.new((bm_verts[edge[0]], bm_verts[edge[1]]))
    # 更新 BMesh 数据
    bmesh.update_edit_mesh(obj.data)
    # 切换回对象模式
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"在对象 '{obj_name}' 中成功添加顶点并创建边！")

def select_all_edges(obj_name):
    """
    选择指定对象中的所有边。
    参数:
        obj_name (str): 对象的名称。
    """
    # 确保对象存在
    if obj_name not in bpy.data.objects:
        raise ValueError(f"对象 '{obj_name}' 不存在于场景中！")
    obj = bpy.data.objects[obj_name]
    # 切换到对象模式并确保对象是活动对象
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = obj
    # 切换到编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    # 使用 BMesh 操作网格数据
    bm = bmesh.from_edit_mesh(obj.data)
    # 选择所有边
    for edge in bm.edges:
        edge.select = True
    # 更新 BMesh 数据
    bmesh.update_edit_mesh(obj.data)
    # # 切换回对象模式
    # bpy.ops.object.mode_set(mode='OBJECT')
    print(f"对象 '{obj_name}' 中的所有边已被选中！")

def move_snow_ground():
    # 定义目标集合和物体的名称
    collection_names = ["ICity_Procedural"]  # 需要移动的集合
    object_names = ["ICity Procedural ground", "ICity Road"]  # 需要移动的单个物体

    # 定义新集合的名称
    new_collection_name = "snow"

    # 检查是否已经存在名为 "snow" 的集合
    new_collection = bpy.data.collections.get(new_collection_name)

    # 如果不存在，则创建一个新集合
    if not new_collection:
        new_collection = bpy.data.collections.new(new_collection_name)
        bpy.context.scene.collection.children.link(new_collection)  # 将新集合添加到场景的最外层
        print(f"创建了新集合 '{new_collection_name}'")

    # 处理集合
    for collection_name in collection_names:
        target_collection = bpy.data.collections.get(collection_name)
        if target_collection:
            # 将目标集合移动到新集合中
            # 首先，从当前父集合中移除
            for parent_collection in bpy.data.collections:
                if target_collection.name in parent_collection.children:
                    parent_collection.children.unlink(target_collection)

            # 然后，将目标集合添加到新集合中
            new_collection.children.link(target_collection)
            print(f"集合 '{collection_name}' 已移动到集合 '{new_collection_name}'")
        else:
            print(f"未找到名为 '{collection_name}' 的集合")

    # 处理单个物体
    for object_name in object_names:
        obj = bpy.data.objects.get(object_name)
        if obj:
            # 将物体移动到新集合中
            # 首先，从当前集合中移除该物体
            for collection in obj.users_collection:
                collection.objects.unlink(obj)

            # 然后，将物体添加到新集合中
            new_collection.objects.link(obj)
            print(f"物体 '{object_name}' 已移动到集合 '{new_collection_name}'")
        else:
            print(f"未找到名为 '{object_name}' 的物体")

    print(f"操作完成，所有指定的集合和物体已移动到集合 '{new_collection_name}'")

########################################### 主函数部分  ############################################
def create_city_3D(exist_flag,vertices,edges,Texture_Road,Texture_Curb,Texture_Sidewalk,Tree,Tree_Spacing,Light,Light_Spacing,Light_Energy,Light_color,Bollard,Bollard_Spacing,Bench,Bench_Spacing,Services,Services_Spacing,Sign_Spacing,Road_Lanes_Width,Sidewalk_Width):
    #在设定好的文件中操作不需要start
    bpy.ops.sna.start_5209e()
    bpy.ops.sna.edit_city_d7cab()

    # 清除初始加载的内容 切记不能直接删除点 要调用函数 否则的话没办法在地块上生成城市
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.context.scene.sna_citystreet = 'Road'
    bpy.context.scene.sna_street_assetoptions = 'Options'
    bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.ops.sna.remove_road_a2302()

    obj_name="ICity Base"
    add_vertices_and_edges(obj_name, vertices, edges)
    select_all_edges(obj_name)

    ## 道路设置部分
    bpy.context.scene.sna_citystreet = 'Road'

    bpy.context.scene.sna_street_assetoptions = 'Assets'
    # 纹理
    bpy.context.scene.sna_street_asset_type = 'Texture'
    bpy.context.scene.sna_road_materials_type_ = 'Road'
    bpy.ops.sna.material_filter_f04c3()
    bpy.ops.sna.road_materials_filter_6a3ec()
    bpy.context.scene.sna_road_materials_browser = Texture_Road
    bpy.ops.sna.road_apply_5c3ab()
    bpy.context.scene.sna_road_materials_type_ = 'Curb'
    bpy.ops.sna.material_filter_f04c3()
    bpy.ops.sna.road_materials_filter_6a3ec()
    bpy.context.scene.sna_road_materials_browser = Texture_Curb
    bpy.ops.sna.road_apply_5c3ab()
    bpy.context.scene.sna_road_materials_type_ = 'Sidewalk'
    bpy.ops.sna.material_filter_f04c3()
    bpy.ops.sna.road_materials_filter_6a3ec()
    bpy.context.scene.sna_road_materials_browser = Texture_Sidewalk
    bpy.ops.sna.road_apply_5c3ab()

    # 树
    bpy.context.scene.sna_street_asset_type = 'Tree'
    bpy.context.scene.sna_street_asset_browser = Tree
    # bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.data.node_groups["Road 2"].nodes["Tree spacing"].outputs[0].default_value = Tree_Spacing
    bpy.ops.sna.road_apply_5c3ab()

    # 路灯
    bpy.context.scene.sna_street_asset_type = 'Light'
    bpy.context.scene.sna_street_asset_browser = Light
    # bpy.ops.mesh.attribute_set(value_bool=False)
    # bpy.data.objects["ICity Road"].modifiers["GeometryNodes"]["Socket_2"] = False
    # bpy.data.objects["ICity Road"].modifiers["GeometryNodes"]["Socket_3"] = False
    bpy.data.node_groups["Road 2"].nodes["Light"].inputs[10].default_value = Light_Spacing
    bpy.ops.sna.road_apply_5c3ab()


    # 灯光
    bpy.context.scene.sna_street_asset_type = 'Traffic light'
    bpy.data.lights["ICity Road light"].energy = Light_Energy
    bpy.data.lights["ICity Road light"].color = Light_color

    # 系船柱
    bpy.context.scene.sna_street_asset_type = 'Bollard'
    bpy.context.scene.sna_street_asset_browser = Bollard
    bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.data.node_groups["Road 2"].nodes["Bollard"].inputs[10].default_value = Bollard_Spacing
    bpy.ops.sna.road_apply_5c3ab()

    #长椅
    bpy.context.scene.sna_street_asset_type = 'Bench'
    bpy.context.scene.sna_street_asset_browser = Bench
    bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.data.node_groups["Road 2"].nodes["Bench"].inputs[10].default_value = Bench_Spacing
    bpy.ops.sna.road_apply_5c3ab()

    # 基础设施
    bpy.context.scene.sna_street_asset_type = 'Services'
    bpy.context.scene.sna_street_asset_browser = Services
    bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.data.node_groups["Road 2"].nodes["Services"].inputs[10].default_value = Services_Spacing
    bpy.ops.sna.road_apply_5c3ab()

    bpy.context.scene.sna_street_asset_type = 'Sign'
    bpy.ops.mesh.attribute_set(value_bool=True)
    bpy.data.node_groups["Road 2"].nodes["Sign"].inputs[10].default_value = Sign_Spacing
    bpy.ops.sna.road_apply_5c3ab()

    bpy.context.scene.sna_street_assetoptions = 'Options'
    # 道路宽度 默认是0
    bpy.ops.sna.road_lanes_width_93562()
    bpy.ops.mesh.attribute_set(value_float=Road_Lanes_Width)
    # 人行道宽度 默认是0
    bpy.ops.sna.sidewalk_width_99dc0()
    bpy.ops.mesh.attribute_set(value_float=Sidewalk_Width)

    # 执行删除操作
    if exist_flag[0]==1:
        # bpy.context.scene.sna_citystreet = 'Road'
        # bpy.context.scene.sna_street_assetoptions = 'Assets'
        # bpy.ops.sna.filter_street_assets_c5c0e()
        # bpy.ops.sna.material_filter_f04c3()
        # bpy.ops.sna.road_materials_filter_6a3ec()
        # bpy.context.scene.sna_street_asset_type = 'Tree'
        # bpy.ops.mesh.attribute_set(value_bool=False)
        # bpy.ops.sna.road_remove_aa51d()

        # 间距法
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Tree'
        bpy.data.node_groups["Road 2"].nodes["Tree spacing"].outputs[0].default_value = 10000

    if exist_flag[1]==1:
        # 曲线救国了，因为删除的接口做的不好，就那间距调的很大
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Light'
        bpy.data.node_groups["Road 2"].nodes["Light"].inputs[10].default_value = 10000

    if exist_flag[2] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Bench'
        bpy.data.node_groups["Road 2"].nodes["Bench"].inputs[10].default_value = 10000

    if exist_flag[3] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Services'
        bpy.data.node_groups["Road 2"].nodes["Services"].inputs[10].default_value = 10000

    if exist_flag[4] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Bollard'
        bpy.data.node_groups["Road 2"].nodes["Bollard"].inputs[10].default_value = 10000

    if exist_flag[5] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Sign'
        bpy.data.node_groups["Road 2"].nodes["Sign"].inputs[10].default_value = 10000

    if exist_flag[6] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Imperfection'
        bpy.data.node_groups["Road 2"].nodes["Group.012"].inputs[2].default_value = 10000

    if exist_flag[7] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Imperfection'
        bpy.data.node_groups["Road 2"].nodes["Group.054"].inputs[2].default_value = 0

    if exist_flag[8] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Imperfection'
        bpy.data.node_groups["Road 2"].nodes["Value"].outputs[0].default_value = 0
        bpy.data.node_groups["Road 2"].nodes["Value.001"].outputs[0].default_value = 0

    if exist_flag[9] == 1:
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Assets'
        bpy.ops.sna.filter_street_assets_c5c0e()
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()
        bpy.context.scene.sna_street_asset_type = 'Imperfection'
        bpy.data.node_groups["Road 2"].nodes["Group.013"].inputs[2].default_value = 0

    # bpy.context.scene.sna_citystreet = 'Road'
    # bpy.context.scene.sna_street_assetoptions = 'Assets'
    # bpy.ops.sna.filter_street_assets_c5c0e()
    # bpy.ops.sna.material_filter_f04c3()
    # bpy.ops.sna.road_materials_filter_6a3ec()
    # bpy.context.scene.sna_street_asset_type = 'Traffic light'
    # bpy.data.objects["ICity Road"].modifiers["GeometryNodes"]["Socket_0"] = False


# vertices = [
#         (-50, -50, 0),  # 第一个点的坐标
#         (-60, 50, 0),  # 第二个点的坐标
#         (50, 50, 0),  # 第三个点的坐标
#         (50, -50, 0),  # 第四个点的坐标
#         (-150, -50, 0),  # 第一个点的坐标
#         (-150, 50, 0),  # 第二个点的坐标
#     ]
# edges = [
#         (0, 1),   # 连接第一个和第五个点
#         (1, 2),  # 连接第一个和第二个点
#         (2, 3),  # 连接第一个和第三个点
#         (3, 0),
#         (0, 4),
#         (1, 5),
#         (4, 5)
#     ]

# 放射状

vertices = [
        (0, 0, 0),  # 第一个点的坐标

        (0, 50, 0),
        (50, 0, 0),
        (0, -50, 0),
        (-50, 0, 0),

        (0, 100, 0),
        (100, 0, 0),
        (0, -100, 0),
        (-100, 0, 0),

        (0, 150, 0),
        (150, 0, 0),
        (0, -150, 0),
        (-150, 0, 0),
    ]
edges = [
        (1, 2),   # 连接第一个和第五个点
        (2, 3),  # 连接第一个和第二个点(0, 1),   # 连接第一个和第五个点
        (3, 4),  # 连接第一个和第五个点
        (4,1),

        (5, 6),  # 连接第一个和第二个点
        (6, 7),  # 连接第一个和第五个点
        (7, 8),  # 连接第一个和第二个点
        (8, 5),  # 连接第一个和第二个点

        (9, 10),  # 连接第一个和第二个点(0, 1),   # 连接第一个和第五个点
        (10, 11),   # 连接第一个和第五个点
        (11, 12),  # 连接第一个和第五个点
        (12, 9),  # 连接第一个和第二个点(0, 1),   # 连接第一个和第五个点

        (1, 5),  # 连接第一个和第二个点
        (2, 6),  # 连接第一个和第二个点
        (3, 7),  # 连接第一个和第五个点
        (4, 8),  # 连接第一个和第二个点

        (5, 9),  # 连接第一个和第二个点
        (6, 10),  # 连接第一个和第二个点

        (7, 11),  # 连接第一个和第五个点
        (8, 12),  # 连接第一个和第二个点

    ]

# vertices = [
#         (-60, -60, 0),  # 第一个点的坐标
#         (-60, 60, 0),  # 第二个点的坐标
#         (60, 60, 0),  # 第三个点的坐标
#         (60, -60, 0),  # 第四个点的坐标
#     ]
# edges = [
#         (0, 1),   # 连接第一个和第五个点
#         (1, 2),  # 连接第一个和第二个点
#         (2, 3),  # 连接第一个和第三个点
#         (3, 0)
#     ]
Texture_Road='ICity_Road 2 dirty 2_Default'
Texture_Curb='ICity_Curb grey black_Default'
Texture_Sidewalk='ICity_Sidewalk 3_Default'
Tree='Tree1_Tree_ICity_Default'
Tree_Spacing=21
Light='Light4_Light_ICity_Default'
Light_Spacing=21
Light_Energy=300
Light_color=(1, 0.587094, 0.150187)
Bollard='Bollard1_Bollard_Default_ICity'
Bollard_Spacing=0.501
Bench='Bench1_Bench_ICity_Default'
Bench_Spacing=51
Services='Services_Default'
Services_Spacing=21
Sign_Spacing=61
Road_Lanes_Width=-1
Sidewalk_Width=-1
# 树木、路灯，长椅、周边设施、护栏、路标标志、路面落叶、路沿落叶、小垃圾、水洼存在标志,
# 为1的时候代表需要删除
# exist_flag=[1,1,1,1,1,1,1,1,1,1]
exist_flag=[0,0,0,0,0,0,0,0,0,0]

# 设置雪天
collection="snow"
snow_loaction=(-50,0,50)
snow_scale=(100,100,100)
snow_ground_loaction=(-50,0,6.2779)
snow_ground_dimensions=(250,150,6.2770)
density=0.8 # 雪密度
thickness=0.8 # 雪厚度

# 设置雨天
# 调用函数并设置输入值
# 闪电尺寸
lighting_socket_2_value=5.0
# 闪电速率
lighting_socket_3_value=10.0
# 闪电密度
lighting_socket_4_value=10.0
# z轴的坐标
lighting_loaction=(-50,0,50)
# 雨水速率
rain_fall_socket_2_value=3.0
# 雨水长度
rain_fall_socket_3_value=11.0
# 雨水密度
rain_fall_socket_4_value=14.0
rain_fall_location=(0,0,60)
rain_fall_scale=(100,100,100)
clouds_loaction=(0,0,50)
clouds_scale=(2.5,2.5,1)

#先运行
create_city_3D(exist_flag,vertices,edges,Texture_Road,Texture_Curb,Texture_Sidewalk,Tree,Tree_Spacing,Light,Light_Spacing,Light_Energy,Light_color,Bollard,Bollard_Spacing,Bench,Bench_Spacing,Services,Services_Spacing,Sign_Spacing,Road_Lanes_Width,Sidewalk_Width)
move_snow_ground()

#再运行下面之一
# snow_weather(collection,snow_ground_loaction,snow_ground_dimensions,density,thickness,snow_loaction,snow_scale)
# rain_weather(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,rain_fall_scale,clouds_loaction, clouds_scale)
