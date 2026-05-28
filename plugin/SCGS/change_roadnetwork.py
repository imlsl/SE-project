import bpy
import bmesh

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

# 清除初始加载的内容 切记不能直接删除点 要调用函数 否则的话没办法在地块上生成城市
bpy.ops.sna.edit_city_d7cab()
bpy.ops.mesh.select_all(action='SELECT')
bpy.context.scene.sna_citystreet = 'Road'
bpy.context.scene.sna_street_assetoptions = 'Options'
bpy.ops.mesh.attribute_set(value_bool=True)
bpy.ops.sna.remove_road_a2302()

obj_name = "ICity Base"

# 1
# vertices=[(-50,50,0),(50,50,0),(50,-50,0),(-50,-50,0)]
# edges=[(0,1),(1,2),(2,3),(3,0)]
# nn = 3

# # 2
# vertices = [(-200, 200, 0), (-200, 50, 0),(-50, 50, 0), (-50, 100, 0),(-50,200,0),(200,200,0), (200,100,0),(50,100,0),(50,-100,0),(50,-200,0),(200,-200,0),(-200,-100,0),(-200,-200,0)]
# edges = [ (0, 1),  (1, 2),  (2, 3),  (3, 4),(0,4),(4,5),(5,6),(6,7),(3,7),(7,8),(8,9),(9,10),(10,6),(8,11),(1,11),(11,12),(9,12) ]
# nn=1
# vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

# # 3
# vertices = [ (-200, 200, 0),  (-100, 200, 0), (50, 200, 0), (200, 200, 0), (-200, 100, 0),  (-100, 100, 0),  (0, 100, 0), (50, 100, 0),   (100, 100, 0),  (200, 100, 0),  (-200, 0, 0), (-150, 0, 0),   (-100, 0, 0),  (-50, 0, 0),  (0, -0, 0) ,(100,0,0),(200,0,0),(0,-50,0),(100,-50,0),(-200,-100,0),(-150,-100,0),(-50,-100,0),(0,-100,0),(100,-100,0),(200,-100,0),(-200,-200,0),(-150,-200,0),(-50,-200,0),(0,-200,0),(100,-200,0),(200,-200,0)]
# edges = [ (1, 2),  (2, 3),(0,4),(1,5),(2,7),(3,9),(4,5),(5,6),(6,7),(7,8),(8,9),(4,10),(5,12),(6,14),(8,15),(9,16),(10,11),(11,12),(12,13),(13,14),(15,16),(10,19),(11,20),(13,21),(14,17),(17,22),(17,18),(15,18),(18,23),(16,24),(19,20),(20,21),(21,22),(22,23),(23,24),(19,25),(20,26),(21,27),(22,28),(23,29),(24,30),(26,27),(28,29) ]
# nn=1
# vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

# 4
# vertices = [(0, 0, 0), (0, 50, 0),(50, 0, 0),(0, -50, 0),(-50, 0, 0),(0, 100, 0),(100, 0, 0), (0, -100, 0),(-100, 0, 0),(0, 150, 0),(150, 0, 0), (0, -150, 0),(-150, 0, 0),]
# edges = [ (1, 2),(2, 3),(3, 4),(4,1),(5, 6),(6, 7), (7, 8),  (8, 5), (9, 10), (10, 11), (11, 12),(12, 9), (1, 5), (2, 6), (3, 7),(4, 8),  (5, 9), (6, 10), (7, 11), (8, 12),]
# nn=2
# vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

# 5
# vertices = [(5, 25, 0),(-15,15,0),(-5,15,0),(10,15,0),(-15,0,0),(-5,0,0),(15,0,0),(10,-5,0),(-5,-10,0),(10,-10,0),(-5,-20,0),(15,-15,0),(25,-10,0)]
# edges = [(0,2),(1,2),(2,3),(1,4),(2,5),(3,7),(5,8),(8,9),(7,9),(6,7),(8,10),(10,11),(6,11),(11,12),(4,5)]
# nn = 15
# vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

# 6
vertices = [(-1, 5, 0),(1,4,0),(-4,2,0),(-2,2,0),(1,2,0),(2,2,0),(3,2,0),(-5,-2,0),(-3,-2,0),(1,-2,0),(3,-2,0),(5,-2,0),(1,-3,0),(3,-4,0),(-4,-5,0),(1,-5,0)]
edges = [(0,3),(1,4),(2,3),(3,4),(4,5),(5,6),(3,9),(4,9),(5,10),(7,8),(8,9),(9,10),(10,11),(8,14),(9,12),(12,13),(12,15)]
nn = 100
vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

add_vertices_and_edges(obj_name, vertices, edges)

# 创建汽车路径
# 创建一个新的网格
mesh = bpy.data.meshes.new(name="road1")
# 使用BMesh来创建顶点和边
bm = bmesh.new()
for v in vertices:
    bm.verts.new(v)
bm.verts.ensure_lookup_table()
for e in edges:
    bm.edges.new((bm.verts[e[0]], bm.verts[e[1]]))
# 将BMesh数据写入网格
bm.to_mesh(mesh)
bm.free()
# 创建一个新的对象并将其链接到场景中
obj = bpy.data.objects.new("road1", mesh)
bpy.context.collection.objects.link(obj)
# 选中并激活新创建的对象
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
print("对象 'road' 创建完成！")
# 替换汽车路径
bpy.data.node_groups["节点城市"].nodes["Object Info.001"].inputs[0].default_value = bpy.data.objects["road1"]