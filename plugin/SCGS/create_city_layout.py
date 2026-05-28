import bpy

# 定义面的顶点
faces = [
    [(-60, 60, 0), (-59, 59, 0), (-59, -59, 0), (-60, -60, 0)],
    [(-59, -59, 0), (-60, -60, 0), (60, -60, 0), (59, -59, 0)],
    [(60, -60, 0), (59, -59, 0),(59, 59, 0), (60, 60, 0)],
    [(60, 60, 0), (59, 59, 0), (-59, 59, 0),(-60, 60, 0)],
    [(10,10,0),(-10,10,0),(-10,-10,0),(10,-10,0)]
]

# 合并所有顶点
all_vertices = []
vertex_index_map = {}
final_faces = []

for face in faces:
    new_face = []
    for vertex in face:
        if vertex not in vertex_index_map:
            vertex_index_map[vertex] = len(all_vertices)
            all_vertices.append(vertex)
        new_face.append(vertex_index_map[vertex])
    final_faces.append(new_face)

# 创建新的网格和对象
mesh = bpy.data.meshes.new(name="CustomGeometry")
obj = bpy.data.objects.new("CustomGeometry", mesh)

# 将对象添加到场景中
scene = bpy.context.scene
scene.collection.objects.link(obj)

# 更新网格数据
mesh.from_pydata(all_vertices, [], final_faces)
mesh.update()

# 为每个面设置布尔类型属性，标记前两个面
bool_attribute = mesh.attributes.new(name="path", type='BOOLEAN', domain='FACE')
for i, _ in enumerate(mesh.polygons):
    if i < 4:
        bool_attribute.data[i].value = True
    else:
        bool_attribute.data[i].value = False