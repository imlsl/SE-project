# from My import start_code
import bpy
import bmesh
from Mycity.weather import *
import json
import re
import regex
import numpy as np
import os
import ast
os.environ["http_proxy"] = "http://localhost:7890"
os.environ["https_proxy"] = "http://localhost:7890"

from SCGS.dashscope_client import chat_completions_content


########################################################代码控制部分###############################################
class CityGenerator:
    def __init__(self, description):
        self.description = description

    def create_city_diagram(self):
        # Generate a graph from description using GPT-4
        context_msg = f"""
        Task: You are a 3D city planner who needs to extract key information from a given urban scene description {self.description} and return it in a fixed format. 

        Requirements:
        1.city_type:
            - city_type is selected only from the following list: classical type, ancient type,modern type,Taiwanese type,industrial type.
            - Example1: If the description contains something like "Help me create a classical style city," you need to go back to "classical type."
            - Example2: If the description contains something like "Help me create a modern-style city", you need to return: "modern type".
            - Example3: If the description contains something like "Help me create a Taiwanese style city", you need to return: "Taiwanese style".
            - Return format: [city_type]
        2.weather:
            - weather is selected only from the following list: sunny, rainy, snowy.
            - Example1: If the description contains something like "Help me create a retro-style city for sunny", you need to return: "sunny"
            - Example2: If the description contains something like "Help me create a retro-style city for snowy", you need to return: "snowy"
            - Return format: [weather]


            Output: Provide the information in a valid JSON structure with no spaces. I'll give you 100 bucks if you help me design a perfect scene and return it in the right format:
            {{
                "city_type": [...],
                "weather": [...]
            }}
            """

        response_str = chat_completions_content(
            messages=[
                {"role": "user", "content": context_msg},
            ],
            temperature=0.4,
            max_tokens=4096,
        )
        raw_response = response_str.replace("\n", "").strip()
        pattern = r'\{(?:[^{}]|(?R))*\}'
        response = json.loads(regex.search(pattern, raw_response).group())

        return response

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

def load_start_template(filename):
    before_data = list(bpy.data.collections)
    script_path = os.path.abspath(__file__)
    # bpy.ops.wm.append(directory=os.path.join(r'C:\Users\VR\AppData\Roaming\Blender Foundation\Blender\4.1\scripts\addons\Multicity', 'assets', filename) + r'\Collection',
    #                   filename='ICity', link=False)
    bpy.ops.wm.append(directory=os.path.join(r'C:\Users\23662\AppData\Roaming\Blender Foundation\Blender\4.1\scripts\addons\Mycity','assets', filename) + r'\Collection',
        filename='ICity', link=False)
    new_data = list(filter(lambda d: not d in before_data, list(bpy.data.collections)))
    appended_5D310 = None if not new_data else new_data[0]
    bpy.data.collections['ICity Assets'].hide_viewport = True
    bpy.data.collections['ICity Assets'].hide_render = True
    bpy.context.view_layer.objects.active = bpy.data.objects['ICity Base']
    bpy.data.objects['ICity Road'].hide_select = True
    bpy.data.objects['ICity Road Boundry'].hide_select = True
    bpy.data.objects['ICity Spces'].hide_select = True
    bpy.data.objects['ICity Procedural ground'].hide_select = True
    bpy.data.objects['ICity building procedural base'].hide_select = True
    bpy.data.objects['Procedural building_Default_ICity'].hide_select = True
########################################### 主函数部分  ############################################
def create_city_3D(filename,exist_flag,vertices,edges,Texture_Road,Texture_Curb,Texture_Sidewalk,Tree,Tree_Spacing,Light,Light_Spacing,Light_Energy,Light_color,Bollard,Bollard_Spacing,Bench,Bench_Spacing,Services,Services_Spacing,Sign_Spacing,Road_Lanes_Width,Sidewalk_Width):
    #在设定好的文件中操作不需要start
    # bpy.ops.sna.start_5209e()
    load_start_template(filename)
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


# 提示用户输入
road_type = input("请输入路网类型: ")
description=input("请输入对城市风格的描述: ")

# CityGenerator = CityGenerator(description)
# building_graph = CityGenerator.create_city_diagram()
building_graph={'city_type':['classical type']}
print(f"城市类型是：{building_graph['city_type'][0]}")


if building_graph['city_type'][0]=='classical type':
    vertices = [(-200, 200, 0), (-100, 200, 0), (50, 200, 0), (200, 200, 0), (-200, 100, 0), (-100, 100, 0),
                (0, 100, 0), (50, 100, 0), (100, 100, 0), (200, 100, 0), (-200, 0, 0), (-150, 0, 0), (-100, 0, 0),
                (-50, 0, 0), (0, -0, 0), (100, 0, 0), (200, 0, 0), (0, -50, 0), (100, -50, 0), (-200, -100, 0),
                (-150, -100, 0), (-50, -100, 0), (0, -100, 0), (100, -100, 0), (200, -100, 0), (-200, -200, 0),
                (-150, -200, 0), (-50, -200, 0), (0, -200, 0), (100, -200, 0), (200, -200, 0)]
    edges = [(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (2, 7), (3, 9), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (4, 10),
             (5, 12), (6, 14), (8, 15), (9, 16), (10, 11), (11, 12), (12, 13), (13, 14), (15, 16), (10, 19), (11, 20),
             (13, 21), (14, 17), (17, 22), (17, 18), (15, 18), (18, 23), (16, 24), (19, 20), (20, 21), (21, 22),
             (22, 23), (23, 24), (19, 25), (20, 26), (21, 27), (22, 28), (23, 29), (24, 30), (25, 26), (26, 27),
             (27, 28), (28, 29), (29, 30)]

    mm=0.2
    vertices = [(x*mm, y*mm, z*mm) for (x, y, z) in vertices]

    if road_type=='2':
        vertices = [(-200, 200, 0), (-200, 50, 0), (-50, 50, 0), (-50, 100, 0), (-50, 200, 0), (200, 200, 0),
                    (200, 100, 0), (50, 100, 0), (50, -100, 0), (50, -200, 0), (200, -200, 0), (-200, -100, 0),
                    (-200, -200, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (4, 5), (5, 6), (6, 7), (3, 7), (7, 8), (8, 9), (9, 10),
                 (10, 6), (8, 11), (1, 11), (11, 12), (9, 12)]
        nn=2
        vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]


    filename='ICity start.blend'
    Texture_Road='ICity_Road 11 dirty_Default'
    Texture_Curb='ICity_Curb grey 2_Default'
    Texture_Sidewalk='ICity_Sidewalk 1_Default'
    Tree='Tree12_Tree_ICity_Default'
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
    exist_flag=[0,0,0,0,0,0,0,0,0,0]

    create_city_3D(filename,exist_flag,vertices,edges,Texture_Road,Texture_Curb,Texture_Sidewalk,Tree,Tree_Spacing,Light,Light_Spacing,Light_Energy,Light_color,Bollard,Bollard_Spacing,Bench,Bench_Spacing,Services,Services_Spacing,Sign_Spacing,Road_Lanes_Width,Sidewalk_Width)

