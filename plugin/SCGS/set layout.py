import bpy
import bmesh

# 确保在对象模式下运行脚本
if bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# 获取名为 "layout" 的物体
obj = bpy.data.objects.get("layout")

if obj and obj.type == 'MESH':
    # 切换到编辑模式
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # 使用 BMesh 操作网格
    bm = bmesh.from_edit_mesh(obj.data)

    # 删除所有面
    bmesh.ops.delete(bm, geom=bm.faces, context='FACES')

    # 创建一个自定义的四边形面
    # 添加四个顶点
    v1 = bm.verts.new((0, 0, 0))
    v2 = bm.verts.new((10, 0, 0))
    v3 = bm.verts.new((10, 10, 0))
    v4 = bm.verts.new((0, 10, 0))

    # 创建一个面
    bm.faces.new((v1, v2, v3, v4))

    # 更新网格
    bmesh.update_edit_mesh(obj.data)

    # 切换回对象模式
    bpy.ops.object.mode_set(mode='OBJECT')
else:
    print("没有找到名为 'layout' 的物体或该物体不是网格类型")