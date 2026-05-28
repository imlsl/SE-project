import bpy
import os


def load_lighting(socket_2_value=5.0, socket_3_value=5.0, socket_4_value=2.0, loaction=(0, 0, 30)):
    blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))
    collection_name = "WI Lightning"
    object_name = "WI Lightning"

    if not os.path.exists(blend_file_path):
        print(f"指定的文件路径不存在：{blend_file_path}")
        return

    with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"集合 {collection_name} 不存在于指定文件中。")
            return

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
        return

    try:
        if bpy.context.scene.collection.objects.get(obj.name) is None:
            bpy.context.scene.collection.objects.link(obj)
    except Exception as e:
        print(f"链接对象 {object_name} 到场景失败：{e}")

    obj.location = loaction
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.get("WI Lightning")
    if mod is None:
        print("未找到 modifier: WI Lightning（无法设置 Socket 参数）。")
        return
    mod["Socket_2"] = socket_2_value
    mod["Socket_3"] = socket_3_value
    mod["Socket_4"] = socket_4_value


def load_rain_fall(socket_2_value=5.0, socket_3_value=5.0, socket_4_value=2.0, loaction=(0, 0, 30),
                   scale=(1.0, 1.0, 1.0)):
    blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))
    collection_name = "WI Rain"
    object_name = "WI Rain Fall"

    if not os.path.exists(blend_file_path):
        print(f"指定的文件路径不存在：{blend_file_path}")
        return

    with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"集合 {collection_name} 不存在于指定文件中。")
            return

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
        return

    try:
        if bpy.context.scene.collection.objects.get(obj.name) is None:
            bpy.context.scene.collection.objects.link(obj)
    except Exception as e:
        print(f"链接对象 {object_name} 到场景失败：{e}")

    obj.location = loaction
    obj.scale = scale
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.get("WI Rain Fall")
    if mod is None:
        print("未找到 modifier: WI Rain Fall（无法设置 Socket 参数）。")
        return
    mod["Socket_2"] = socket_2_value
    mod["Socket_3"] = socket_3_value
    mod["Socket_4"] = socket_4_value


def load_clouds(loaction=(0, 0, 30), scale=(1.0, 1.0, 1.0)):
    blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))
    collection_name = "Collection 5"
    object_name = "Clouds"

    if not os.path.exists(blend_file_path):
        print(f"指定的文件路径不存在：{blend_file_path}")
        return

    with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"集合 {collection_name} 不存在于指定文件中。")
            return

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
        return

    try:
        if bpy.context.scene.collection.objects.get(obj.name) is None:
            bpy.context.scene.collection.objects.link(obj)
    except Exception as e:
        print(f"链接对象 {object_name} 到场景失败：{e}")

    obj.location = loaction
    obj.scale = scale


def load_snow_ground(collection_mesh, loaction=(0, 0, 6.2779), dimensions=(100, 100, 6.37),
                     density=0.8, thickness=0.8):
    blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))
    collection_name = "WI Snow"
    object_name = "WI Snow Ground"

    if not os.path.exists(blend_file_path):
        print(f"指定的文件路径不存在：{blend_file_path}")
        return

    with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"集合 {collection_name} 不存在于指定文件中。")
            return

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
        return

    try:
        if bpy.context.scene.collection.objects.get(obj.name) is None:
            bpy.context.scene.collection.objects.link(obj)
    except Exception as e:
        print(f"链接对象 {object_name} 到场景失败：{e}")

    obj.location = loaction
    obj.dimensions = dimensions
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.get("WI Snow Ground")
    if mod is None:
        print("未找到 modifier: WI Snow Ground（无法设置 Socket 参数）。")
        return
    mesh_coll = bpy.data.collections.get(collection_mesh)
    if mesh_coll is None:
        print(f"未找到集合 {collection_mesh}（无法设置 Socket_5）。")
        return
    mod["Socket_5"] = mesh_coll
    mod["Socket_6"] = density
    mod["Socket_7"] = thickness


def snow_fall(loaction=(0, 0, 30), scale=(1.0, 1.0, 1.0)):
    blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))
    collection_name = "WI Snow"
    object_name = "WI Snow Fall"

    if not os.path.exists(blend_file_path):
        print(f"指定的文件路径不存在：{blend_file_path}")
        return

    with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
        if collection_name in data_from.collections:
            data_to.collections = [collection_name]
        else:
            print(f"集合 {collection_name} 不存在于指定文件中。")
            return

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
        return

    try:
        if bpy.context.scene.collection.objects.get(obj.name) is None:
            bpy.context.scene.collection.objects.link(obj)
    except Exception as e:
        print(f"链接对象 {object_name} 到场景失败：{e}")

    obj.location = loaction
    obj.scale = scale


def rain_weather(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,
                 rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                 rain_fall_scale, clouds_loaction, clouds_scale):
    load_lighting(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction)
    load_rain_fall(rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                   rain_fall_scale)
    load_clouds(clouds_loaction, clouds_scale)

    collection_name = "Rain Weather Collection"
    if collection_name not in bpy.data.collections:
        rain_weather_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(rain_weather_collection)
        print(f"集合 '{collection_name}' 已创建。")
    else:
        rain_weather_collection = bpy.data.collections[collection_name]
        print(f"集合 '{collection_name}' 已存在。")

    object_names = ["Clouds", "WI Lightning", "WI Rain Fall"]
    for obj_name in object_names:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            rain_weather_collection.objects.link(obj)
            print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
        else:
            print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")


def snow_weather(collection_mesh, snow_ground_loaction, snow_ground_dimensions, density, thickness,
                 snow_loaction, snow_scale):
    load_snow_ground(collection_mesh, snow_ground_loaction, snow_ground_dimensions, density, thickness)
    snow_fall(snow_loaction, snow_scale)

    collection_name = "Snow Weather Collection"
    if collection_name not in bpy.data.collections:
        snow_weather_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(snow_weather_collection)
        print(f"集合 '{collection_name}' 已创建。")
    else:
        snow_weather_collection = bpy.data.collections[collection_name]
        print(f"集合 '{collection_name}' 已存在。")

    object_names = ["WI Snow Ground", "WI Snow Fall"]
    for obj_name in object_names:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            snow_weather_collection.objects.link(obj)
            print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
        else:
            print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")
