import bpy
import bmesh
# 场景2车辆1
# vertices=[(-200,200,0),(-200,-200,0),(200,-200,0),(200,200,0),(-200,200,0)]
# edges=[(0,1),(1,2),(2,3),(3,4)]

# 场景2车辆2
vertices=[(50,-200,0),(50,100,0),(-50,100,0),(-50,200,0)]
edges=[(0,1),(1,2),(2,3)]

# 创建汽车路径
# 创建一个新的网格
mesh = bpy.data.meshes.new(name="roadnew1")
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
obj = bpy.data.objects.new("roadnew1", mesh)
bpy.context.collection.objects.link(obj)
# 选中并激活新创建的对象
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
print("对象 'road' 创建完成！")
# 替换汽车路径
bpy.data.node_groups["节点城市"].nodes["Object Info.001"].inputs[0].default_value = bpy.data.objects["roadnew1"]