# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "SCGS",
    "author" : "SCGS",
    "description" : "一款可以生成3D城市道路建筑景观的blender插件",
    "blender" : (4, 0, 1),
    "version" : (1, 0, 3),
    "location" : "",
    "warning" : "Beta version!",
    "doc_url": "https://shop204936337.taobao.com/", 
    "tracker_url": "https://shop204936337.taobao.com/", 
    "category" : "3D View" 
}

import bpy
import bmesh
import bpy.utils.previews
import os
from bpy.app.handlers import persistent
# import main_path_building
from PIL import Image
from sklearn.cluster import KMeans
from skimage.measure import label, regionprops
import cv2
import numpy as np
from skimage.morphology import skeletonize
import sknw
import networkx as nx
from scipy.spatial import cKDTree

# 导入模板相关模块
try:
    from SCGS.scene_template_config import SceneTemplate, ConfigParser
except ImportError as e:
    print(f"警告: 无法导入模板模块: {e}")
    # 定义空的类以防导入失败
    class SceneTemplate:
        @classmethod
        def get_asset_name(cls, asset_type, index):
            return None
    class ConfigParser:
        pass


class MainPathBuildings:
    def __init__(self, tolerance=30, merge_threshold=20.0, rdp_epsilon=2.0):
        self.tolerance = tolerance
        self.merge_threshold = merge_threshold
        self.rdp_epsilon = rdp_epsilon

    def detect_dominant_colors(self, image_path, num_colors=2, white_threshold=160):
        img = Image.open(image_path).convert('RGBA')
        pixels = [
            pixel[:3] for pixel in img.getdata()
            if pixel[3] != 0 and not all(c >= white_threshold for c in pixel[:3])
        ]
        if len(pixels) < num_colors:
            raise ValueError(f"有效像素不足 {num_colors} 种颜色")
        kmeans = KMeans(n_clusters=num_colors, random_state=0).fit(pixels)
        colors = sorted(
            [tuple(map(int, c)) for c in kmeans.cluster_centers_],
            key=lambda c: sum(c),
            reverse=True
        )
        return colors

    def create_color_mask(self, image, target_color):
        img = image.convert('RGBA')
        new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        pixels = img.load()
        new_pixels = new_img.load()

        def is_target(p): return all(
            abs(p[i] - target_color[i]) <= self.tolerance for i in range(3))

        for x in range(img.width):
            for y in range(img.height):
                r, g, b, a = pixels[x, y]
                if a == 0 or (r >= 240 and g >= 240 and b >= 240):
                    continue
                if is_target((r, g, b)):
                    new_pixels[x, y] = (r, g, b, a)
        return new_img

    def split_colors(self, image_path):
        colors = self.detect_dominant_colors(image_path)
        src_img = Image.open(image_path).convert('RGBA')
        return [self.create_color_mask(src_img, c) for c in colors]

    def count_rings(self, mask):
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        return sum(1 for h in hierarchy[0] if h[3] != -1) if hierarchy is not None else 0

    def detect_ring_counts(self, pil_img):
        data = np.array(pil_img)
        alpha = data[:, :, 3]
        color_matrix = np.where(alpha != 0, (data[:, :, 0] << 24) | (data[:, :, 1] << 16) | (data[:, :, 2] << 8) | alpha, 0)
        labels = label(color_matrix, connectivity=1, background=0)

        ring_counts = []
        for region in regionprops(labels):
            minr, minc, maxr, maxc = region.bbox
            mask = (labels[minr:maxr, minc:maxc] == region.label).astype(np.uint8) * 255
            ring_counts.append(self.count_rings(mask))
        return ring_counts

    def detect_transparent_polygons_noring(self, pil_img):
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        alpha_channel = img[:, :, 3]
        _, mask = cv2.threshold(alpha_channel, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center = (img.shape[1] / 2, img.shape[0] / 2)

        polygons = []
        for contour in contours:
            epsilon = 0.0005 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            if len(approx) < 3:
                continue
            if cv2.contourArea(approx, oriented=True) > 0:
                approx = approx[::-1]
            poly = [(round(p[0][0] - center[0], 2), round(center[1] - p[0][1], 2), 0) for p in approx]
            polygons.append(poly)
        return polygons

    def perpendicular_dist(self, point, start, end):
        p, s, e = np.array(point), np.array(start), np.array(end)
        if np.allclose(s, e):
            return np.linalg.norm(p - s)
        to_3d = lambda v: np.hstack((v, 0)) if v.size == 2 else v
        s3, e3, p3 = to_3d(s), to_3d(e), to_3d(p)
        t = np.dot(p3 - s3, e3 - s3) / np.dot(e3 - s3, e3 - s3)
        if t <= 0:
            return np.linalg.norm(p - s)
        elif t >= 1:
            return np.linalg.norm(p - e)
        else:
            return np.linalg.norm(np.cross(e3 - s3, p3 - s3)) / np.linalg.norm(e3 - s3)

    def rdp_simplify(self, points):
        if len(points) <= 2:
            return [tuple(p) for p in points]
        points = [np.array(p) for p in points]
        start, end = points[0], points[-1]
        dists = [self.perpendicular_dist(p, start, end) for p in points[1:-1]]
        max_dist = max(dists, default=0)
        index = dists.index(max_dist) + 1 if max_dist > self.rdp_epsilon else None

        if index:
            return self.rdp_simplify(points[:index + 1])[:-1] + self.rdp_simplify(points[index:])
        return [tuple(start), tuple(end)]

    def merge_close_nodes(self, nodes, connections):
        node_points = np.array([(n[0], n[1]) for n in nodes])
        tree = cKDTree(node_points)
        clusters = tree.query_ball_tree(tree, self.merge_threshold)

        seen, unique_clusters = set(), []
        for i, cluster in enumerate(clusters):
            if i not in seen:
                unique_clusters.append(cluster)
                seen.update(cluster)

        merged_nodes = []
        index_mapping = np.zeros(len(nodes), dtype=int)
        for cluster in unique_clusters:
            center = np.mean(node_points[cluster], axis=0)
            merged_nodes.append((center[0], center[1], 0))
            for idx in cluster:
                index_mapping[idx] = len(merged_nodes) - 1

        merged_conn = set()
        for a, b in connections:
            na, nb = index_mapping[a], index_mapping[b]
            if na != nb:
                merged_conn.add(tuple(sorted((na, nb))))
        return merged_nodes, list(merged_conn)

    def detect_transparent_polygons_ring(self, pil_img):
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        alpha = img[:, :, 3]
        binary = np.where(alpha > 0, 255, 0).astype(np.uint8)

        skeleton = skeletonize(binary // 255).astype(np.uint16)
        graph = sknw.build_sknw(skeleton)
        min_branch = 10

        edges_to_remove = []
        for s, e, attr in graph.edges(data=True):
            pts = attr['pts']
            length = sum(np.linalg.norm(np.array(pts[i]) - np.array(pts[i - 1])) for i in range(1, len(pts)))
            if length < min_branch:
                edges_to_remove.append((s, e))
        graph.remove_edges_from(edges_to_remove)
        graph.remove_nodes_from(list(nx.isolates(graph)))

        height, width = binary.shape
        nodes, coord_map = [], {}
        for node in graph.nodes():
            y, x = graph.nodes[node]['o']
            key = (round(x - width / 2, 2), round(height / 2 - y, 2))
            if key not in coord_map:
                nodes.append((*key, 0))
                coord_map[key] = len(nodes) - 1

        connections = []
        for s, e, attr in graph.edges(data=True):
            raw_pts = [(p[1] - width / 2, height / 2 - p[0]) for p in attr['pts']]
            simplified = self.rdp_simplify(raw_pts)
            prev_idx = None
            for p in simplified:
                key = (round(p[0], 2), round(p[1], 2))
                if key not in coord_map:
                    nodes.append((*key, 0))
                    coord_map[key] = len(nodes) - 1
                curr_idx = coord_map[key]
                if prev_idx is not None:
                    connections.append((prev_idx, curr_idx))
                prev_idx = curr_idx

        return self.merge_close_nodes(nodes, connections)

    def process(self, image_path):
        masks = self.split_colors(image_path)
        all_polygons, all_vertices, all_edges = [], [], []

        for mask in masks:
            ring_counts = self.detect_ring_counts(mask)
            if all(r == 0 for r in ring_counts):
                polys = self.detect_transparent_polygons_noring(mask)
                all_polygons.extend([[(float(x), float(y), z) for x, y, z in poly] for poly in polys])
            else:
                verts, edges = self.detect_transparent_polygons_ring(mask)
                all_vertices.extend(verts)
                all_vertices = [
                                tuple(float(item) if isinstance(item, np.float64) else item for item in tpl)
                                for tpl in all_vertices
                                ]
                all_edges.extend(edges)
                all_edges = [
                    tuple(int(item) if isinstance(item, np.int64) else item for item in tpl)
                    for tpl in all_edges
                ]

        return all_polygons, all_vertices, all_edges


def parse_manual_vertices(text):
    """解析顶点文本 '(0,0,0),(1,1,0)' 为 [(0,0,0), (1,1,0)]"""
    import ast
    text = text.strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple)):
            if parsed and isinstance(parsed[0], (list, tuple)):
                return [tuple(float(v) for v in p) for p in parsed]
            if parsed and isinstance(parsed[0], (int, float)):
                return [tuple(float(v) for v in parsed)]
        if isinstance(parsed, tuple) and len(parsed) == 3:
            return [tuple(float(v) for v in parsed)]
        return []
    except (ValueError, SyntaxError, TypeError):
        return []


def parse_manual_edges(text):
    """解析边文本 '(0,1),(1,2)' 为 [(0,1), (1,2)]"""
    import ast
    text = text.strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple)):
            if parsed and isinstance(parsed[0], (list, tuple)):
                return [tuple(int(v) for v in p) for p in parsed]
            if parsed and isinstance(parsed[0], (int, float)):
                return [tuple(int(v) for v in parsed)]
        if isinstance(parsed, tuple) and len(parsed) == 2:
            return [tuple(int(v) for v in parsed)]
        return []
    except (ValueError, SyntaxError, TypeError):
        return []


import bpy
import bmesh
import bpy.utils.previews
import os
from bpy.app.handlers import persistent


addon_keymaps = {}
_icons = None
all_assets = {'sna_l': [], }
append = {'sna_asset_type_cat': [], 'sna_city_assets_filtered': [], 'sna_asset_type_cat_2': [], 'sna_all_assets': [], 'sna_theme_filtered': [], 'sna_landscape_filtered': [], 'sna_all_materials': [], 'sna_materials_theme_filtered': [], 'sna_road_materials_filtered': [], 'sna_road_assets_filtered': [], }
hide_assets = {'sna_show_all_v_procedural': False, 'sna_show_all_r_procedural': False, 'sna_show_props_v_procedural': False, 'sna_show_props_r_procedural': False, 'sna_show_all_v_park': False, 'sna_show_all_r_park': False, 'sna_show_grass_v_park': False, 'sna_show_grass_r_park': False, 'sna_show_trees_v_park': False, 'sna_show_trees_r_park': False, }
materials_variables = {'sna_all_materials_enum': [], 'sna_all_materials': [], 'sna_road_materials_filtered_': [], }
variables = {'sna_street_asset_browser': [], 'sna_street_asset': [], 'sna_building_presets': [], 'sna_building_presets_browser': [], 'sna_landscape_browser': [], 'sna_edit_city': False, 'sna_road_materials': [], 'sna_road_materials_browser': [], 'sna_procedural_building_browser': [], 'sna_procedural_building': [], 'sna_landscape_list': [], 'sna_theme': [], 'sna_park_browser': [], 'sna_park_list': [], 'sna_attributes': [], 'sna_sidewalk_curb_mat': [], 'sna_sidewalk_mat': [], }
append_vars_AA8BD = {}


def get_blend_contents(path, data_type):
    if os.path.exists(path):
        with bpy.data.libraries.load(path) as (data_from, data_to):
            return getattr(data_from, data_type)
    return []


def sna_remove_last_path_5D152_A1BA7(String):
    return String.replace('\\' + String.split('\\')[int(len(String.split('\\')) - 1.0)], '')


def sna_remove_last_path_5D152_215A6(String):
    return String.replace('\\' + String.split('\\')[int(len(String.split('\\')) - 1.0)], '')


_item_map = dict()


def make_enum_item(_id, name, descr, preview_id, uid):
    lookup = str(_id)+"\0"+str(name)+"\0"+str(descr)+"\0"+str(preview_id)+"\0"+str(uid)
    if not lookup in _item_map:
        _item_map[lookup] = (_id, name, descr, preview_id, uid)
    return _item_map[lookup]


def sna_update_sna_city_space_type_append_A7B1C(self, context):
    sna_updated_prop = self.sna_city_space_type_append
    bpy.ops.sna.filter_city_assets_ea982('INVOKE_DEFAULT', )


append_vars_48E33 = {}


def sna_filter_list__4A11C_48E33(List):
    append['sna_city_assets_filtered'] = []
    for i_B4720 in range(len(append['sna_theme_filtered'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_theme_filtered'][i_B4720][0]:
                append['sna_city_assets_filtered'].append(append['sna_theme_filtered'][i_B4720])
    return append['sna_city_assets_filtered']


append_vars_B2349 = {}


def sna_filter_list__4A11C_B2349(List):
    append['sna_landscape_filtered'] = []
    for i_B4720 in range(len(append['sna_theme_filtered'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_theme_filtered'][i_B4720][0]:
                append['sna_landscape_filtered'].append(append['sna_theme_filtered'][i_B4720])
    return append['sna_landscape_filtered']


def sna_update_sna_street_asset_type_append_FC104(self, context):
    sna_updated_prop = self.sna_street_asset_type_append
    bpy.ops.sna.filter_road_bc600('INVOKE_DEFAULT', )


append_vars_F9AC6 = {}


def sna_filter_list__4A11C_F9AC6(List):
    append['sna_road_assets_filtered'] = []
    for i_B4720 in range(len(append['sna_theme_filtered'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_theme_filtered'][i_B4720][0]:
                append['sna_road_assets_filtered'].append(append['sna_theme_filtered'][i_B4720])
    return append['sna_road_assets_filtered']


append_vars_F30E5 = {}


def sna_filter_list__4A11C_F30E5(List):
    append['sna_road_materials_filtered'] = []
    for i_B4720 in range(len(append['sna_all_assets'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_all_assets'][i_B4720][0]:
                append['sna_road_materials_filtered'].append(append['sna_all_assets'][i_B4720])
    return append['sna_road_materials_filtered']


def sna_update_sna_city_building_presets_type_append_A77BA(self, context):
    sna_updated_prop = self.sna_city_building_presets_type_append
    bpy.ops.sna.filter_city_assets_ea982('INVOKE_DEFAULT', )


def sna_update_sna_road_materials_type_append_CB7F1(self, context):
    sna_updated_prop = self.sna_road_materials_type_append
    bpy.ops.sna.filter_road_bc600('INVOKE_DEFAULT', )


append_vars_503EF = {}


def sna_filter_list__4A11C_503EF(List):
    append['sna_theme_filtered'] = []
    for i_B4720 in range(len(append['sna_all_assets'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_all_assets'][i_B4720][0]:
                append['sna_theme_filtered'].append(append['sna_all_assets'][i_B4720])
    return append['sna_theme_filtered']


append_vars_1E8BF = {}


def sna_filter_list__4A11C_1E8BF(List):
    append['sna_materials_theme_filtered'] = []
    for i_B4720 in range(len(append['sna_all_materials'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_all_materials'][i_B4720][0]:
                append['sna_materials_theme_filtered'].append(append['sna_all_materials'][i_B4720])
    return append['sna_materials_theme_filtered']


def sna_update_sna_theme_88C83(self, context):
    sna_updated_prop = self.sna_theme
    bpy.ops.sna.filter_theme_31d4c('INVOKE_DEFAULT', )
    bpy.ops.sna.filter_road_bc600('INVOKE_DEFAULT', )
    bpy.ops.sna.filter_city_assets_ea982('INVOKE_DEFAULT', )


hide_assets_vars_E8BEE = {}


def sna_hide_assets_viewport_92CB5_E8BEE(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_all_r_park'] = not hide_assets['sna_show_all_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_all_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


hide_assets_vars_982E5 = {}


def sna_hide_assets_viewport_92CB5_982E5(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_grass_r_park'] = not hide_assets['sna_show_grass_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_grass_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


hide_assets_vars_1E48D = {}


def sna_hide_assets_viewport_92CB5_1E48D(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_grass_v_park'] = not hide_assets['sna_show_grass_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_grass_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


hide_assets_vars_E138F = {}


def sna_hide_assets_viewport_92CB5_E138F(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_trees_r_park'] = not hide_assets['sna_show_trees_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_trees_r_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


hide_assets_vars_8DFD5 = {}


def sna_hide_assets_viewport_92CB5_8DFD5(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_trees_v_park'] = not hide_assets['sna_show_trees_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_trees_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


hide_assets_vars_3361F = {}


def sna_hide_assets_viewport_92CB5_3361F(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_all_v_park'] = not hide_assets['sna_show_all_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_all_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'OBJECT', 'DATA'}, )
    return


def sna_update_sna_proxy_mode_0EBCB(self, context):
    sna_updated_prop = self.sna_proxy_mode
    if property_exists("bpy.data.node_groups['Hide viewport input'].nodes['Proxy buildings'].inputs[0].default_value", globals(), locals()):
        bpy.data.node_groups['Hide viewport input'].nodes['Proxy buildings'].inputs[0].default_value = sna_updated_prop
    bpy.data.node_groups['ICity Proxy'].nodes['Light'].inputs[0].default_value = sna_updated_prop


visual_scripting_editor_vars_867FF = {}


def sna_generate_icon_list_from_collection_6BD3F_867FF(Collection):
    materials_variables['sna_all_materials'] = []
    for i_037A6 in range(len(Collection)):
        materials_variables['sna_all_materials'].append(Collection[i_037A6].name)
    materials_variables['sna_all_materials'] = sorted(materials_variables['sna_all_materials'], reverse=False)
    return materials_variables['sna_all_materials']


def sna_update_sna_road_materials_type__75061(self, context):
    sna_updated_prop = self.sna_road_materials_type_
    bpy.ops.sna.material_filter_f04c3('INVOKE_DEFAULT', )
    bpy.ops.sna.road_materials_filter_6a3ec('INVOKE_DEFAULT', )


append_vars_71E86 = {}


def sna_filter_list__4A11C_71E86(List):
    materials_variables['sna_road_materials_filtered_'] = []
    for i_B4720 in range(len(materials_variables['sna_all_materials_enum'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in materials_variables['sna_all_materials_enum'][i_B4720][0]:
                materials_variables['sna_road_materials_filtered_'].append(materials_variables['sna_all_materials_enum'][i_B4720])
    return materials_variables['sna_road_materials_filtered_']


visual_scripting_editor_vars_5001C = {}


def sna_set_active_attribute_572EC_5001C(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_A11A7 = {}


def sna_set_active_attribute_572EC_A11A7(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_30DFB = {}


def sna_set_active_attribute_572EC_30DFB(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_1DA63 = {}


def sna_set_active_attribute_572EC_1DA63(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_E3814 = {}


def sna_set_active_attribute_572EC_E3814(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_5FBBE = {}


def sna_set_active_attribute_572EC_5FBBE(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_0978B = {}


def sna_set_active_attribute_572EC_0978B(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_813E4 = {}


def sna_set_active_attribute_572EC_813E4(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_4CC88 = {}


def sna_set_active_attribute_572EC_4CC88(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_FD2DC = {}


def sna_set_active_attribute_572EC_FD2DC(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_2F07A = {}


def sna_set_active_attribute_572EC_2F07A(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_92991 = {}


def sna_set_active_attribute_572EC_92991(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_41053 = {}


def sna_set_active_attribute_572EC_41053(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_0DB67 = {}


def sna_set_active_attribute_572EC_0DB67(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_6A49A = {}


def sna_store_atrributes_list_D7786_6A49A():
    variables['sna_attributes'] = []
    obj = bpy.context.active_object
    if obj is not None and obj.data is not None and hasattr(obj.data, 'attributes'):
        for i_0900E in range(len(obj.data.attributes)):
            variables['sna_attributes'].append(obj.data.attributes[i_0900E].name)
    variables['sna_attributes'] = variables['sna_attributes']
    return variables['sna_attributes']


visual_scripting_editor_vars_AE34F = {}


def sna_set_active_attribute_572EC_AE34F(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_BBC9A = {}


def sna_set_active_attribute_572EC_BBC9A(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_7B5C3 = {}


def sna_set_active_attribute_572EC_7B5C3(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_81051 = {}


def sna_set_active_attribute_572EC_81051(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_5CC3C = {}


def sna_set_active_attribute_572EC_5CC3C(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_997D9 = {}


def sna_set_active_attribute_572EC_997D9(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


def sna_move_to_collection_A3C17_7B15A(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


def sna_move_to_collection_A3C17_97000(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


def sna_move_to_collection_A3C17_D6B3F(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


def sna_move_to_collection_A3C17_D47A1(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


def sna_move_to_collection_A3C17_575C9(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


visual_scripting_editor_vars_62FA0 = {}


def sna_set_active_attribute_572EC_62FA0(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


visual_scripting_editor_vars_42E3D = {}


def sna_set_active_attribute_572EC_42E3D(Name):
    bpy.context.active_object.data.attributes.active_index = variables['sna_attributes'].index(bpy.context.active_object.data.attributes[Name].name)
    return


def sna_update_sna_street_asset_type_append_F3D9F(self, context):
    sna_updated_prop = self.sna_street_asset_type_append
    listed_enum_0_83b17 = sna_sidewalk_mat_C9E1B()
    result_0_08a09, path_1_08a09, output_2_08a09, filtered_3_08a09 = sna_street_assets_lists_1588D()


def sna_update_sna_city_space_type_F658C(self, context):
    sna_updated_prop = self.sna_city_space_type
    bpy.ops.sna.filter_presets_fb5a4()
    bpy.ops.sna.park_filter_5a7a2()
    bpy.ops.sna.procedural_building_filter_05bed()
    bpy.ops.sna.landscape_filter_0bf89()


def sna_update_sna_street_asset_type_BF136(self, context):
    sna_updated_prop = self.sna_street_asset_type
    bpy.ops.sna.filter_street_assets_c5c0e('INVOKE_DEFAULT', )
    bpy.ops.sna.material_filter_f04c3()
    bpy.ops.sna.road_materials_filter_6a3ec()


visual_scripting_editor_vars_EAC41 = {}


def sna_generate_icon_list_from_collection_6BD3F_EAC41(Collection):
    variables['sna_procedural_building'] = []
    for i_037A6 in range(len(Collection)):
        variables['sna_procedural_building'].append(Collection[i_037A6].name)
    variables['sna_procedural_building'] = sorted(variables['sna_procedural_building'], reverse=False)
    return variables['sna_procedural_building']


visual_scripting_editor_vars_B83D7 = {}


def sna_generate_icon_list_from_collection_6BD3F_B83D7(Collection):
    variables['sna_park_list'] = []
    for i_037A6 in range(len(Collection)):
        variables['sna_park_list'].append(Collection[i_037A6].name)
    variables['sna_park_list'] = sorted(variables['sna_park_list'], reverse=False)
    return variables['sna_park_list']


visual_scripting_editor_vars_BBAA3 = {}


def sna_generate_icon_list_from_collection_6BD3F_BBAA3(Collection):
    variables['sna_landscape_list'] = []
    for i_037A6 in range(len(Collection)):
        variables['sna_landscape_list'].append(Collection[i_037A6].name)
    variables['sna_landscape_list'] = sorted(variables['sna_landscape_list'], reverse=False)
    return variables['sna_landscape_list']


def sna_update_sna_city_building_presets_type_FB155(self, context):
    sna_updated_prop = self.sna_city_building_presets_type
    bpy.ops.sna.filter_presets_fb5a4()


visual_scripting_editor_vars_EDBEF = {}


def sna_generate_icon_list_from_collection_6BD3F_EDBEF(Collection):
    variables['sna_street_asset'] = []
    for i_037A6 in range(len(Collection)):
        variables['sna_street_asset'].append(Collection[i_037A6].name)
    variables['sna_street_asset'] = sorted(variables['sna_street_asset'], reverse=False)
    return variables['sna_street_asset']


visual_scripting_editor_vars_593DA = {}


def sna_generate_icon_list_from_collection_6BD3F_593DA(Collection):
    variables['sna_street_asset'] = []
    for i_037A6 in range(len(Collection)):
        variables['sna_street_asset'].append(Collection[i_037A6].name)
    variables['sna_street_asset'] = sorted(variables['sna_street_asset'], reverse=False)
    return variables['sna_street_asset']


def sna_update_sna_city_space_type_AE473(self, context):
    sna_updated_prop = self.sna_city_space_type


def load_preview_icon(path):
    global _icons
    if not path in _icons:
        if os.path.exists(path):
            _icons.load(path, path, "IMAGE")
        else:
            return 0
    return _icons[path].icon_id


def property_exists(prop_path, glob, loc):
    try:
        eval(prop_path, glob, loc)
        return True
    except:
        return False


class SNA_OT_Store_All_Assets_5B09E(bpy.types.Operator):
    bl_idname = "sna.store_all_assets_5b09e"
    bl_label = "Store all assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    bl_property = 'sna_assets'
    sna_assets: bpy.props.StringProperty(name='Assets', description='', default='', subtype='NONE', maxlen=0)
    sna_materials: bpy.props.StringProperty(name='Materials', description='', default='', subtype='NONE', maxlen=0)

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        with open(os.path.join(r'C:\Users\hothifa\Desktop\New folder (4)',self.sna_assets), mode='w') as file_B938B:
            file_B938B.seek(0)
            file_B938B.write('')
            file_B938B.truncate()
        for i_01B64 in range(len(append['sna_all_assets'])):
            with open(os.path.join(r'C:\Users\hothifa\Desktop\New folder (4)',self.sna_assets), mode='a') as file_B8646:
                file_B8646.write(str(append['sna_all_assets'][i_01B64]))
            with open(os.path.join(r'C:\Users\hothifa\Desktop\New folder (4)',self.sna_materials), mode='w') as file_77F2E:
                file_77F2E.seek(0)
                file_77F2E.write('')
                file_77F2E.truncate()
            for i_7F837 in range(len(append['sna_all_materials'])):
                with open(os.path.join(r'C:\Users\hothifa\Desktop\New folder (4)',self.sna_materials), mode='a') as file_B2545:
                    file_B2545.write(str(append['sna_all_materials'][i_7F837]))
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'sna_assets', text='Assets', icon_value=0, emboss=True)
        layout.prop(self, 'sna_materials', text='M', icon_value=0, emboss=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


class SNA_OT_Refresh_Theme_443Bd(bpy.types.Operator):
    bl_idname = "sna.refresh_theme_443bd"
    bl_label = "REFRESH theme"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        append['sna_all_assets'] = []
        variables['sna_theme'] = []
        append['sna_all_materials'] = []
        for i_44F70 in range(len([f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))])):
            variables['sna_theme'].append([[f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_44F70], [f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_44F70], '', 0])
        bpy.ops.sna.read_97c87('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Refresh_C6Cb8(bpy.types.Operator):
    bl_idname = "sna.refresh_c6cb8"
    bl_label = "REFRESH"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        append['sna_all_assets'] = []
        variables['sna_theme'] = []
        append['sna_all_materials'] = []
        for i_83C0D in range(len([f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))])):
            variables['sna_theme'].append([[f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_83C0D], [f for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_83C0D], '', 0])
            append['sna_all_materials'] = []
            append['sna_all_assets'] = []
            for i_C1B5F in range(len([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))])):
                print([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F])
                for i_F84DA in range(len([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))])):
                    if 'textures' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]:
                        pass
                    else:
                        if ('Procedural' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA] or 'Park' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA] or 'Landscape' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]):
                            for i_135F8 in range(len([f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))])):
                                if ('.blend' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA] + '\\' + [f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8] and (not '.blend1' in [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA] + '\\' + [f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8])):
                                    print([f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8].replace('.blend', ''))
                                    append['sna_all_assets'].append([[f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8].replace('.blend', ''), [f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8].replace('.blend', ''), [os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA] + '\\' + [f for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_135F8], 0])
                        else:
                            print(str([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))]))
                            for i_82365 in range(len([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))])):
                                print([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365])
                                if ('.blend' in [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365] and (not '.blend1' in [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365])):
                                    if 'Materials' in [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365]:
                                        for i_25698 in range(len(get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'materials'))):
                                            print(str([get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'materials')[i_25698], get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'materials')[i_25698], [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 0]))
                                            append['sna_all_materials'].append([get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'materials')[i_25698], get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'materials')[i_25698], [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 0])
                                    else:
                                        for i_1C51B in range(len(get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'objects'))):
                                            print(get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'objects')[i_1C51B])
                                            append['sna_all_assets'].append([get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'objects')[i_1C51B], get_blend_contents([os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 'objects')[i_1C51B], [os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f) for f in os.listdir([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA]) if os.path.isfile(os.path.join([os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f) for f in os.listdir([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]) if os.path.isdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F], f))][i_F84DA], f))][i_82365], 0])
            append['sna_all_assets'].append(['Services_' + os.path.basename([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]), 'Services_' + os.path.basename([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]), os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'Road','Road assets.blend'), 0])
            append['sna_all_assets'].append(['Imperfections_' + os.path.basename([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]), 'Imperfections_' + os.path.basename([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F]), os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'Road','Road assets.blend'), 0])
            with open(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'All assets'), mode='w') as file_79393:
                file_79393.seek(0)
                file_79393.write('')
                file_79393.truncate()
            for i_DAC5F in range(len(append['sna_all_assets'])):
                with open(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'All assets'), mode='a') as file_7F70C:
                    file_7F70C.write(str(append['sna_all_assets'][i_DAC5F]))
                with open(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'All materials'), mode='w') as file_C4C79:
                    file_C4C79.seek(0)
                    file_C4C79.write('')
                    file_C4C79.truncate()
                for i_0EF82 in range(len(append['sna_all_materials'])):
                    with open(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_C1B5F],'All materials'), mode='a') as file_C219A:
                        file_C219A.write(str(append['sna_all_materials'][i_0EF82]))
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text='This may take a long time!', icon_value=2)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


class SNA_OT_Read_97C87(bpy.types.Operator):
    bl_idname = "sna.read_97c87"
    bl_label = "Read"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        for i_48027 in range(len([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))])):
            print([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027])
            all_assets['sna_l'] = []
            for i_74205 in range(len([os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f) for f in os.listdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],)) if os.path.isfile(os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f))])):
                print(os.path.join('','assets','Assets'))
                text_928F4 = ""
                lines_928F4 = []
                if os.path.exists([os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f) for f in os.listdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],)) if os.path.isfile(os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f))][i_74205]):
                    with open([os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f) for f in os.listdir(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],)) if os.path.isfile(os.path.join(os.path.join([os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f) for f in os.listdir(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))) if os.path.isdir(os.path.join(sna_assets_path_7BE86(os.path.join(os.path.dirname(__file__), 'assets', 'Assets')), f))][i_48027],), f))][i_74205], "r") as file_928F4:
                        lines_928F4 = list(map(lambda l: l.strip(), file_928F4.readlines()))
                        text_928F4 = "\n".join(lines_928F4)
                print(text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')))
                for i_C26C7 in range(len(text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')).split(']'))):
                    if (text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')).split(']')[i_C26C7] == ''):
                        pass
                    else:
                        for i_B308C in range(len(text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')).split(']')[i_C26C7].replace('[', '').split(','))):
                            if (text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')).split(']')[i_C26C7].replace('[', '').split(',')[i_B308C] == ''):
                                pass
                            else:
                                all_assets['sna_l'].append(text_928F4.replace('G:\\\\My Drive\\\\Building\\\\Assets', os.path.join(os.path.dirname(__file__), 'assets', 'Assets')).split(']')[i_C26C7].replace('[', '').split(',')[i_B308C].replace("'", '').replace('"', ''))
            append['sna_all_assets'] = []
            for i_E241D in range(int(len(all_assets['sna_l']) / 4.0)):
                append['sna_all_assets'].append([all_assets['sna_l'][int(i_E241D * 4.0)].strip(), all_assets['sna_l'][int(i_E241D * 4.0)].strip(), all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)].strip().replace('\\\\', '\\'), (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + 'Custom asset.png') if (load_preview_icon(r'') == load_preview_icon(os.path.join(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + all_assets['sna_l'][int(i_E241D * 4.0)] + '.png',).strip())) else load_preview_icon(os.path.join(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + all_assets['sna_l'][int(i_E241D * 4.0)] + '.png',).strip()))) else (load_preview_icon(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + 'Custom asset.png') if (load_preview_icon(r'') == load_preview_icon(os.path.join(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + all_assets['sna_l'][int(i_E241D * 4.0)] + '.png',).strip())) else load_preview_icon(os.path.join(sna_remove_last_path_5D152_A1BA7(all_assets['sna_l'][int(int(i_E241D * 4.0) + 2.0)]) + '\\' + all_assets['sna_l'][int(i_E241D * 4.0)] + '.png',).strip())))])
            append['sna_all_materials'] = []
            for i_41DE6 in range(int(len(all_assets['sna_l']) / 4.0)):
                append['sna_all_materials'].append([all_assets['sna_l'][int(i_41DE6 * 4.0)].strip(), all_assets['sna_l'][int(i_41DE6 * 4.0)].strip(), all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\'), (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(os.path.join(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png',).strip()) == (load_preview_icon(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)] + '\\' + 'Custom asset.png') if (load_preview_icon(os.path.join(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png',).strip()) == load_preview_icon(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png')) else load_preview_icon(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png'))) else (load_preview_icon(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)] + '\\' + 'Custom asset.png') if (load_preview_icon(os.path.join(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png',).strip()) == load_preview_icon(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png')) else load_preview_icon(sna_remove_last_path_5D152_215A6(all_assets['sna_l'][int(int(i_41DE6 * 4.0) + 2.0)].strip().replace('\\\\', '\\')) + '\\' + all_assets['sna_l'][int(i_41DE6 * 4.0)] + '.png')))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_assets_path_7BE86(Assets):
    prefs = bpy.context.preferences.addons[__name__].preferences
    return (Assets if (prefs.sna_assets_path == '') else prefs.sna_assets_path)


def sna_road_browser_append_enum_items(self, context):
    enum_items = append['sna_road_assets_filtered']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


class SNA_OT_Filter_City_Assets_Ea982(bpy.types.Operator):
    bl_idname = "sna.filter_city_assets_ea982"
    bl_label = "filter City assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        print(bpy.context.scene.sna_city_space_type_append)
        filtered_0_48e33 = sna_filter_list__4A11C_48E33([bpy.context.scene.sna_city_space_type_append])
        print(str(filtered_0_48e33), str([bpy.context.scene.sna_city_space_type_append]))
        filtered_0_b2349 = sna_filter_list__4A11C_B2349(['Landscape'])
        print(str(filtered_0_b2349))
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_city_browser_append_enum_items(self, context):
    enum_items = append['sna_city_assets_filtered']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_landscape_browser_append_enum_items(self, context):
    enum_items = append['sna_landscape_filtered']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_road_materials_browser_append_enum_items(self, context):
    enum_items = append['sna_road_materials_filtered']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_theme_enum_items(self, context):
    enum_items = variables['sna_theme']
    return [make_enum_item(item[0], item[1], item[2], item[3], 2**i) for i, item in enumerate(enum_items)]


class SNA_OT_Filter_Road_Bc600(bpy.types.Operator):
    bl_idname = "sna.filter_road_bc600"
    bl_label = "filter road"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        print('')
        filtered_0_f9ac6 = sna_filter_list__4A11C_F9AC6([bpy.context.scene.sna_street_asset_type_append])
        print(str(filtered_0_f9ac6))
        filtered_0_f30e5 = sna_filter_list__4A11C_F30E5([bpy.context.scene.sna_road_materials_type_append])
        print(str(filtered_0_f30e5))
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_filter_list__4A11C(List):
    append['sna_theme_filtered'] = []
    for i_B4720 in range(len(append['sna_all_assets'])):
        for i_9206E in range(len(List)):
            if List[i_9206E] in append['sna_all_assets'][i_B4720][0]:
                append['sna_theme_filtered'].append(append['sna_all_assets'][i_B4720])
    return append['sna_theme_filtered']


class SNA_OT_Filter_Theme_31D4C(bpy.types.Operator):
    bl_idname = "sna.filter_theme_31d4c"
    bl_label = "filter theme"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        filtered_0_503ef = sna_filter_list__4A11C_503EF(list(bpy.context.scene.sna_theme))
        print(str(filtered_0_503ef))
        filtered_0_1e8bf = sna_filter_list__4A11C_1E8BF(list(bpy.context.scene.sna_theme))
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_MT_89AD5(bpy.types.Menu):
    bl_idname = "SNA_MT_89AD5"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        layout = self.layout.column_flow(columns=3)
        layout.operator_context = "INVOKE_DEFAULT"
        layout.template_icon(icon_value=242, scale=12.0)
        
        # 添加模板选择输入框
        row = layout.row()
        row.prop(context.scene, "sna_template_selection", text="模板选择")
        row.operator("sna.apply_template", text="应用模板")
        
        # 添加大模型指令输入框
        row = layout.row()
        row.prop(context.scene, "sna_ai_instruction", text="AI指令")
        row.operator("sna.process_ai_instruction", text="执行")

# 模板应用操作符
class SNA_OT_Apply_Template(bpy.types.Operator):
    bl_idname = "sna.apply_template"
    bl_label = "应用模板"
    bl_description = "根据选择的模板编号自动配置树木、道路和座椅类型"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        template_input = context.scene.sna_template_selection.strip()

        if not template_input:
            self.report({'ERROR'}, "请输入模板编号(0-4)或模板名称")
            return {"CANCELLED"}

        # 匹配模板：支持数字ID和名称匹配
        template_id = None
        if template_input.isdigit():
            template_id = template_input
        else:
            for tid, config in SceneTemplate.get_all_templates().items():
                if template_input.lower() in config.get("name", "").lower():
                    template_id = tid
                    break

        if template_id is None:
            template_id = template_input

        template_config = SceneTemplate.get_template(template_id)
        if template_config is None:
            available = SceneTemplate.list_templates()
            names = "\n".join([f"  {t['id']}: {t['name']}" for t in available])
            self.report({'ERROR'}, f"未找到模板: {template_input}\n可用模板:\n{names}")
            return {"CANCELLED"}

        try:
            self._apply_config(context, template_config)
            template_name = template_config.get("name", "模板")
            self.report({'INFO'}, f"成功应用模板: {template_name}")
            return {"FINISHED"}
        except Exception as e:
            self.report({'ERROR'}, f"应用模板失败: {str(e)}")
            return {"CANCELLED"}

    def _apply_config(self, context, config):
        """应用模板配置到场景"""
        if "tree" in config:
            self._apply_tree_config(context, config["tree"])
        if "road" in config:
            self._apply_road_config(context, config["road"])
        if "bench" in config:
            self._apply_bench_config(context, config["bench"])

    def _apply_tree_config(self, context, tree_type):
        """应用树木类型配置"""
        context.scene.sna_street_asset_type = 'Tree'
        tree_asset = SceneTemplate.get_asset_name("tree", tree_type)
        if tree_asset:
            try:
                context.scene.sna_street_asset_browser = tree_asset
            except TypeError:
                print(f"树木资产 '{tree_asset}' 不可用（场景中可能不存在）")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用树木类型 {tree_type} 时出错: {e}")

    def _apply_road_config(self, context, road_type):
        """应用道路纹理配置"""
        context.scene.sna_street_asset_type = 'Texture'
        context.scene.sna_road_materials_type_ = 'Road'
        road_asset = SceneTemplate.get_asset_name("road", road_type)
        if road_asset:
            try:
                context.scene.sna_road_materials_browser = road_asset
            except TypeError:
                print(f"道路资产 '{road_asset}' 不可用（场景中可能不存在）")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用道路类型 {road_type} 时出错: {e}")

    def _apply_bench_config(self, context, bench_type):
        """应用座椅类型配置"""
        context.scene.sna_street_asset_type = 'Bench'
        bench_asset = SceneTemplate.get_asset_name("bench", bench_type)
        if bench_asset:
            try:
                context.scene.sna_street_asset_browser = bench_asset
            except TypeError:
                print(f"座椅资产 '{bench_asset}' 不可用（场景中可能不存在）")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用座椅类型 {bench_type} 时出错: {e}")

# AI指令处理操作符
class SNA_OT_Process_AI_Instruction(bpy.types.Operator):
    bl_idname = "sna.process_ai_instruction"
    bl_label = "处理AI指令"
    bl_description = "使用大模型解析并执行自然语言指令"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        instruction = context.scene.sna_ai_instruction.strip()
        if not instruction:
            self.report({'ERROR'}, "请输入AI指令")
            return {"CANCELLED"}

        try:
            # 尝试使用LLM解析，失败则回退到本地解析
            config = None
            try:
                config = self._parse_with_llm(instruction)
                if config:
                    print(f"LLM解析结果: {config}")
            except Exception as e:
                print(f"LLM解析失败，使用本地解析: {e}")

            if not config:
                config = self._parse_locally(instruction)
                print(f"本地解析结果: {config}")

            if not config:
                self.report({'ERROR'}, "无法解析指令，请尝试输入如'树木1，道路2，座椅1'的格式")
                return {"CANCELLED"}

            # 验证配置
            is_valid, error_msg = ConfigParser.validate_config(config)
            if not is_valid:
                self.report({'ERROR'}, f"配置无效: {error_msg}")
                return {"CANCELLED"}

            # 应用配置
            self._apply_config(context, config)

            # 构造成功信息
            applied = []
            if "tree" in config:
                applied.append(f"树木={config['tree']}")
            if "road" in config:
                applied.append(f"道路={config['road']}")
            if "bench" in config:
                applied.append(f"座椅={config['bench']}")

            message = "成功执行指令: " + ", ".join(applied) if applied else "成功处理指令"
            self.report({'INFO'}, message)
            return {"FINISHED"}

        except Exception as e:
            self.report({'ERROR'}, f"处理指令失败: {str(e)}")
            return {"CANCELLED"}

    def _parse_with_llm(self, instruction):
        """使用大模型解析指令"""
        try:
            from SCGS.dashscope_client import chat_completions_content
        except ImportError:
            from dashscope_client import chat_completions_content

        prompt = SceneTemplate.create_prompt_for_parsing().replace(
            "{INSTRUCTION}", instruction
        )

        response_str = chat_completions_content(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )

        return ConfigParser.parse_response(response_str)

    def _parse_locally(self, instruction):
        """本地解析指令（不使用LLM）"""
        import re
        config = {}

        # 检查是否是纯数字（模板ID）
        if instruction.strip().isdigit():
            template = SceneTemplate.get_template(instruction.strip())
            if template:
                config.update({
                    "tree": template.get("tree"),
                    "road": template.get("road"),
                    "bench": template.get("bench"),
                })
                return config

        # 检查是否包含 "模板" 关键词（如 "模板4"、"选择模板4"、"应用模板0"）
        template_match = re.search(r'模板\s*(\d)', instruction)
        if template_match:
            template_id = template_match.group(1)
            template = SceneTemplate.get_template(template_id)
            if template:
                config.update({
                    "tree": template.get("tree"),
                    "road": template.get("road"),
                    "bench": template.get("bench"),
                })
                return config

        # 检查是否包含模板名称（如 "现代风格"、"古典风格"）
        for tid, tpl in SceneTemplate.get_all_templates().items():
            tpl_name = tpl.get("name", "")
            if tpl_name and tpl_name in instruction:
                config.update({
                    "tree": tpl.get("tree"),
                    "road": tpl.get("road"),
                    "bench": tpl.get("bench"),
                })
                return config

        instruction_lower = instruction.lower()

        # 按关键词提取类型数字
        tree_patterns = [
            r'树木[：:=\s]*(\d)', r'tree[：:=\s]*(\d)', r'树[：:=\s]*(\d)',
        ]
        for pattern in tree_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["tree"] = match.group(1)
                break

        road_patterns = [
            r'道路[：:=\s]*(\d)', r'road[：:=\s]*(\d)', r'路[：:=\s]*(\d)',
        ]
        for pattern in road_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["road"] = match.group(1)
                break

        bench_patterns = [
            r'座椅[：:=\s]*(\d)', r'bench[：:=\s]*(\d)', r'椅[：:=\s]*(\d)',
        ]
        for pattern in bench_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["bench"] = match.group(1)
                break

        # 如果没有提取到任何参数，尝试按顺序提取数字
        if not config:
            numbers = re.findall(r'\d', instruction)
            if numbers:
                if len(numbers) >= 1:
                    config["tree"] = numbers[0]
                if len(numbers) >= 2:
                    config["road"] = numbers[1]
                if len(numbers) >= 3:
                    config["bench"] = numbers[2]

        return config

    def _apply_config(self, context, config):
        """应用配置到场景"""
        if "tree" in config:
            self._apply_tree_config(context, str(config["tree"]))
        if "road" in config:
            self._apply_road_config(context, str(config["road"]))
        if "bench" in config:
            self._apply_bench_config(context, str(config["bench"]))

    def _apply_tree_config(self, context, tree_type):
        """应用树木类型配置"""
        context.scene.sna_street_asset_type = 'Tree'
        tree_asset = SceneTemplate.get_asset_name("tree", tree_type)
        if tree_asset:
            try:
                context.scene.sna_street_asset_browser = tree_asset
            except TypeError:
                print(f"树木资产 '{tree_asset}' 不可用")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用树木类型 {tree_type} 时出错: {e}")

    def _apply_road_config(self, context, road_type):
        """应用道路纹理配置"""
        context.scene.sna_street_asset_type = 'Texture'
        context.scene.sna_road_materials_type_ = 'Road'
        road_asset = SceneTemplate.get_asset_name("road", road_type)
        if road_asset:
            try:
                context.scene.sna_road_materials_browser = road_asset
            except TypeError:
                print(f"道路资产 '{road_asset}' 不可用")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用道路类型 {road_type} 时出错: {e}")

    def _apply_bench_config(self, context, bench_type):
        """应用座椅类型配置"""
        context.scene.sna_street_asset_type = 'Bench'
        bench_asset = SceneTemplate.get_asset_name("bench", bench_type)
        if bench_asset:
            try:
                context.scene.sna_street_asset_browser = bench_asset
            except TypeError:
                print(f"座椅资产 '{bench_asset}' 不可用")
        try:
            bpy.ops.sna.road_apply_5c3ab()
        except Exception as e:
            print(f"应用座椅类型 {bench_type} 时出错: {e}")




class SNA_MT_8CD9F(bpy.types.Menu):
    bl_idname = "SNA_MT_8CD9F"
    bl_label = ""

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        layout = self.layout.column_flow(columns=2)
        layout.operator_context = "INVOKE_DEFAULT"


def sna_test_enum_items(self, context):
    enum_items = [['zz', 'zz', 'df', 242], ['vb', 'vb', 'jh', 31]]
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


class SNA_MT_0BED6(bpy.types.Menu):
    bl_idname = "SNA_MT_0BED6"
    bl_label = "zz"

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw(self, context):
        layout = self.layout.column_flow(columns=1)
        layout.operator_context = "INVOKE_DEFAULT"
        grid_83B36 = layout.grid_flow(columns=2, row_major=False, even_columns=False, even_rows=True, align=False)
        grid_83B36.enabled = True
        grid_83B36.active = True
        grid_83B36.use_property_split = False
        grid_83B36.use_property_decorate = False
        grid_83B36.alignment = 'Expand'.upper()
        grid_83B36.scale_x = 1.0
        grid_83B36.scale_y = 1.0
        if not True: grid_83B36.operator_context = "EXEC_DEFAULT"
        grid_83B36.prop_enum(bpy.context.scene, 'sna_test', text='541', value='zz')


class SNA_OT_Append_Panel_Lunch_221D5(bpy.types.Operator):
    bl_idname = "sna.append_panel_lunch_221d5"
    bl_label = "Append panel lunch"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You cant append in edit mode!')
        return not 'EDIT' in bpy.context.mode

    def execute(self, context):
        bpy.ops.wm.call_panel(name="SNA_PT_APPEND_PANEL_590A1", keep_open=True)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_PT_APPEND_PANEL_590A1(bpy.types.Panel):
    bl_label = 'Append panel'
    bl_idname = 'SNA_PT_APPEND_PANEL_590A1'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = ''
    bl_order = 0
    bl_options = {'HEADER_LAYOUT_EXPAND'}
    bl_ui_units_x=0

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        row_E44A7 = layout.row(heading='', align=True)
        row_E44A7.alert = False
        row_E44A7.enabled = True
        row_E44A7.active = True
        row_E44A7.use_property_split = False
        row_E44A7.use_property_decorate = False
        row_E44A7.scale_x = 1.0
        row_E44A7.scale_y = 1.0
        row_E44A7.alignment = 'Expand'.upper()
        row_E44A7.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        op = row_E44A7.operator('sna.open_addon_prefrences_34afe', text='Addon preferences', icon_value=117, emboss=True, depress=False)
        op = row_E44A7.operator('sna.refresh_theme_443bd', text='', icon_value=692, emboss=True, depress=False)
        box_E3D9D = layout.box()
        box_E3D9D.alert = False
        box_E3D9D.enabled = True
        box_E3D9D.active = True
        box_E3D9D.use_property_split = False
        box_E3D9D.use_property_decorate = False
        box_E3D9D.alignment = 'Expand'.upper()
        box_E3D9D.scale_x = 1.0
        box_E3D9D.scale_y = 1.0
        if not True: box_E3D9D.operator_context = "EXEC_DEFAULT"
        box_E3D9D.template_icon(icon_value=77, scale=2.0)
        grid_7BE28 = box_E3D9D.grid_flow(columns=3, row_major=False, even_columns=True, even_rows=False, align=True)
        grid_7BE28.enabled = True
        grid_7BE28.active = True
        grid_7BE28.use_property_split = False
        grid_7BE28.use_property_decorate = False
        grid_7BE28.alignment = 'Expand'.upper()
        grid_7BE28.scale_x = 1.0
        grid_7BE28.scale_y = 1.5
        if not True: grid_7BE28.operator_context = "EXEC_DEFAULT"
        grid_7BE28.prop(bpy.context.scene, 'sna_theme', text=str(list(bpy.context.scene.sna_theme)), icon_value=0, emboss=True, expand=True)
        if (list(bpy.context.scene.sna_theme) == []):
            box_C425C = grid_7BE28.box()
            box_C425C.alert = True
            box_C425C.enabled = True
            box_C425C.active = True
            box_C425C.use_property_split = False
            box_C425C.use_property_decorate = False
            box_C425C.alignment = 'Center'.upper()
            box_C425C.scale_x = 1.0
            box_C425C.scale_y = 1.0
            if not True: box_C425C.operator_context = "EXEC_DEFAULT"
            box_C425C.label(text='No themes loaded', icon_value=2)
        row_5299A = layout.row(heading='', align=False)
        row_5299A.alert = False
        row_5299A.enabled = True
        row_5299A.active = True
        row_5299A.use_property_split = False
        row_5299A.use_property_decorate = False
        row_5299A.scale_x = 1.0
        row_5299A.scale_y = 2.2810001373291016
        row_5299A.alignment = 'Expand'.upper()
        row_5299A.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        row_5299A.prop(bpy.context.scene, 'sna_citystreet_append', text=bpy.context.scene.sna_citystreet_append, icon_value=0, emboss=True, expand=True)
        if bpy.context.scene.sna_citystreet_append == "Road":
            col_9EE10 = layout.column(heading='', align=False)
            col_9EE10.alert = False
            col_9EE10.enabled = True
            col_9EE10.active = True
            col_9EE10.use_property_split = False
            col_9EE10.use_property_decorate = False
            col_9EE10.scale_x = 1.0
            col_9EE10.scale_y = 1.0
            col_9EE10.alignment = 'Expand'.upper()
            col_9EE10.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
            box_4CF7C = col_9EE10.box()
            box_4CF7C.alert = False
            box_4CF7C.enabled = True
            box_4CF7C.active = True
            box_4CF7C.use_property_split = False
            box_4CF7C.use_property_decorate = False
            box_4CF7C.alignment = 'Expand'.upper()
            box_4CF7C.scale_x = 1.0
            box_4CF7C.scale_y = 1.0
            if not True: box_4CF7C.operator_context = "EXEC_DEFAULT"
            col_EB3DE = box_4CF7C.column(heading='', align=False)
            col_EB3DE.alert = False
            col_EB3DE.enabled = True
            col_EB3DE.active = True
            col_EB3DE.use_property_split = False
            col_EB3DE.use_property_decorate = False
            col_EB3DE.scale_x = 1.0
            col_EB3DE.scale_y = 1.0
            col_EB3DE.alignment = 'Expand'.upper()
            col_EB3DE.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
            grid_86524 = col_EB3DE.grid_flow(columns=2, row_major=True, even_columns=False, even_rows=False, align=True)
            grid_86524.enabled = True
            grid_86524.active = True
            grid_86524.use_property_split = False
            grid_86524.use_property_decorate = False
            grid_86524.alignment = 'Expand'.upper()
            grid_86524.scale_x = 1.0
            grid_86524.scale_y = 1.0
            if not True: grid_86524.operator_context = "EXEC_DEFAULT"
            grid_86524.prop(bpy.context.scene, 'sna_street_asset_type_append', text='.', icon_value=0, emboss=True, expand=True)
            if bpy.context.scene.sna_street_asset_type_append == "Cars":
                box_41A34 = box_4CF7C.box()
                box_41A34.alert = False
                box_41A34.enabled = True
                box_41A34.active = True
                box_41A34.use_property_split = False
                box_41A34.use_property_decorate = False
                box_41A34.alignment = 'Expand'.upper()
                box_41A34.scale_x = 1.0
                box_41A34.scale_y = 2.0
                if not True: box_41A34.operator_context = "EXEC_DEFAULT"
                box_41A34.label(text='Coming soon!', icon_value=16)
            elif bpy.context.scene.sna_street_asset_type_append == "Texture":
                box_4CF7C.prop(bpy.context.scene, 'sna_road_materials_type_append', text='Type', icon_value=0, emboss=True)
                box_4CF7C.template_icon_view(bpy.context.scene, 'sna_road_materials_browser_append', show_labels=True, scale=7.0, scale_popup=7.0)
            else:
                box_4CF7C.template_icon_view(bpy.context.scene, 'sna_road_browser_append', show_labels=True, scale=7.0, scale_popup=7.0)
        elif bpy.context.scene.sna_citystreet_append == "City":
            col_504E8 = layout.column(heading='', align=True)
            col_504E8.alert = False
            col_504E8.enabled = True
            col_504E8.active = True
            col_504E8.use_property_split = False
            col_504E8.use_property_decorate = False
            col_504E8.scale_x = 1.0
            col_504E8.scale_y = 1.0
            col_504E8.alignment = 'Expand'.upper()
            col_504E8.operator_context = "INVOKE_DEFAULT" if False else "EXEC_DEFAULT"
            row_F0AB4 = col_504E8.row(heading='', align=False)
            row_F0AB4.alert = False
            row_F0AB4.enabled = True
            row_F0AB4.active = True
            row_F0AB4.use_property_split = False
            row_F0AB4.use_property_decorate = False
            row_F0AB4.scale_x = 1.0
            row_F0AB4.scale_y = 1.0
            row_F0AB4.alignment = 'Expand'.upper()
            row_F0AB4.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
            row_F0AB4.prop(bpy.context.scene, 'sna_city_space_type_append', text=bpy.context.scene.sna_city_space_type_append, icon_value=0, emboss=True, expand=True)
            if bpy.context.scene.sna_city_space_type_append == "Presets":
                box_CDBC6 = col_504E8.box()
                box_CDBC6.alert = False
                box_CDBC6.enabled = True
                box_CDBC6.active = True
                box_CDBC6.use_property_split = False
                box_CDBC6.use_property_decorate = False
                box_CDBC6.alignment = 'Expand'.upper()
                box_CDBC6.scale_x = 1.0
                box_CDBC6.scale_y = 1.0
                if not True: box_CDBC6.operator_context = "EXEC_DEFAULT"
                col_CED62 = box_CDBC6.column(heading='', align=True)
                col_CED62.alert = False
                col_CED62.enabled = True
                col_CED62.active = True
                col_CED62.use_property_split = False
                col_CED62.use_property_decorate = False
                col_CED62.scale_x = 1.0
                col_CED62.scale_y = 1.0
                col_CED62.alignment = 'Expand'.upper()
                col_CED62.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
                col_CED62.template_icon_view(bpy.context.scene, 'sna_landscape_browser_append', show_labels=True, scale=7.0, scale_popup=7.0)
                box_0AB48 = col_CED62.box()
                box_0AB48.alert = False
                box_0AB48.enabled = True
                box_0AB48.active = True
                box_0AB48.use_property_split = True
                box_0AB48.use_property_decorate = False
                box_0AB48.alignment = 'Expand'.upper()
                box_0AB48.scale_x = 1.0
                box_0AB48.scale_y = 3.0999999046325684
                if not True: box_0AB48.operator_context = "EXEC_DEFAULT"
                op = box_0AB48.operator('sna.append_landscape_c97bb', text='Append', icon_value=0, emboss=True, depress=False)
            else:
                pass
            box_F5BD4 = col_504E8.box()
            box_F5BD4.alert = False
            box_F5BD4.enabled = True
            box_F5BD4.active = True
            box_F5BD4.use_property_split = False
            box_F5BD4.use_property_decorate = False
            box_F5BD4.alignment = 'Expand'.upper()
            box_F5BD4.scale_x = 1.0
            box_F5BD4.scale_y = 1.0
            if not True: box_F5BD4.operator_context = "EXEC_DEFAULT"
            box_F5BD4.template_icon_view(bpy.context.scene, 'sna_city_browser_append', show_labels=True, scale=7.0, scale_popup=7.0)
        else:
            pass
        box_6ACD3 = layout.box()
        box_6ACD3.alert = False
        box_6ACD3.enabled = True
        box_6ACD3.active = True
        box_6ACD3.use_property_split = True
        box_6ACD3.use_property_decorate = False
        box_6ACD3.alignment = 'Expand'.upper()
        box_6ACD3.scale_x = 1.0
        box_6ACD3.scale_y = 3.0999999046325684
        if not True: box_6ACD3.operator_context = "EXEC_DEFAULT"
        op = box_6ACD3.operator('sna.append_assets_ffd74', text='Append', icon_value=0, emboss=True, depress=False)


class SNA_OT_Open_Addon_Prefrences_34Afe(bpy.types.Operator):
    bl_idname = "sna.open_addon_prefrences_34afe"
    bl_label = "Open addon prefrences"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT', section='ADDONS')
        bpy.data.window_managers['WinMan'].addon_search = 'ICity'
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_hide_assets_viewport_92CB5(Collection, Input_name):
    for i_B7E96 in range(len(bpy.data.collections[Collection].all_objects)):
        for i_D4098 in range(len(bpy.data.collections[Collection].all_objects[i_B7E96].modifiers)):
            if (bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].type == 'NODES'):
                hide_assets['sna_show_all_v_park'] = not hide_assets['sna_show_all_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098][bpy.data.collections[Collection].all_objects[i_B7E96].modifiers[i_D4098].node_group.interface.items_tree[Input_name].identifier] = hide_assets['sna_show_all_v_park']
                bpy.data.collections[Collection].all_objects[i_B7E96].update_tag(refresh={'DATA', 'OBJECT'}, )
    return


class SNA_OT_Hide_Park_R_192D6(bpy.types.Operator):
    bl_idname = "sna.hide_park_r_192d6"
    bl_label = "Hide park R"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_E8BEE('ICity_Park', 'All R')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Grass_R_E07D4(bpy.types.Operator):
    bl_idname = "sna.grass_r_e07d4"
    bl_label = "Grass R"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_982E5('ICity_Park', 'Grass R')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Grass_V_4Cdd7(bpy.types.Operator):
    bl_idname = "sna.grass_v_4cdd7"
    bl_label = "Grass V"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_1E48D('ICity_Park', 'Grass V')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Trees_R_164C2(bpy.types.Operator):
    bl_idname = "sna.trees_r_164c2"
    bl_label = "Trees R"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_E138F('ICity_Park', 'Trees R')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Trees_V_25C59(bpy.types.Operator):
    bl_idname = "sna.trees_v_25c59"
    bl_label = "Trees V"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_8DFD5('ICity_Park', 'Trees V')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Hide_Park_3Ea8F(bpy.types.Operator):
    bl_idname = "sna.hide_park_3ea8f"
    bl_label = "Hide park"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        sna_hide_assets_viewport_92CB5_3361F('ICity_Park', 'All V')
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_road_materials_browser_enum_items(self, context):
    enum_items = materials_variables['sna_road_materials_filtered_']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


class SNA_OT_Material_Filter_F04C3(bpy.types.Operator):
    bl_idname = "sna.material_filter_f04c3"
    bl_label = "Material filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        variables['sna_road_materials_browser'] = []
        print('')
        materials_variables['sna_all_materials'] = []
        list_names_0_867ff = sna_generate_icon_list_from_collection_6BD3F_867FF(bpy.data.objects['ICity_Materials'].material_slots)
        print(str(list_names_0_867ff))
        materials_variables['sna_all_materials_enum'] = []
        for i_057BD in range(len(list_names_0_867ff)):
            if (list_names_0_867ff[i_057BD] == ''):
                pass
            else:
                print(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + list_names_0_867ff[i_057BD] + '.png')).replace('\\', '/'))
                materials_variables['sna_all_materials_enum'].append([list_names_0_867ff[i_057BD], list_names_0_867ff[i_057BD], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + 'Custom asset.png').replace('\\', '/'))) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + list_names_0_867ff[i_057BD] + '.png')).replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + list_names_0_867ff[i_057BD] + '.png')).replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + 'Custom asset.png').replace('\\', '/'))) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + list_names_0_867ff[i_057BD] + '.png')).replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.materials[list_names_0_867ff[i_057BD]].sna_asset_category_path_material)) + '\\' + list_names_0_867ff[i_057BD] + '.png')).replace('\\', '/'))))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Road_Materials_Filter_6A3Ec(bpy.types.Operator):
    bl_idname = "sna.road_materials_filter_6a3ec"
    bl_label = "Road materials filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        print(bpy.context.scene.sna_road_materials_type_)
        filtered_0_71e86 = sna_filter_list__4A11C_71E86([bpy.context.scene.sna_road_materials_type_])
        print(str(filtered_0_71e86))
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Start_5209E(bpy.types.Operator):
    bl_idname = "sna.start_5209e"
    bl_label = "Start"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        demo_blend = os.path.join(os.path.dirname(__file__), 'assets', 'demo.blend')
        with bpy.data.libraries.load(demo_blend, link=False) as (data_from, data_to):
            if 'ICity' in data_from.collections:
                data_to.collections = ['ICity']
        icity = bpy.data.collections.get('ICity')
        if icity:
            bpy.context.scene.collection.children.link(icity)
        bpy.data.collections['ICity Assets'].hide_viewport = True
        bpy.data.collections['ICity Assets'].hide_render = True
        bpy.context.view_layer.objects.active = bpy.data.objects['ICity Base']
        bpy.data.objects['ICity Road'].hide_select = True
        bpy.data.objects['ICity Road Boundry'].hide_select = True
        bpy.data.objects['ICity Spces'].hide_select = True
        bpy.data.objects['ICity Procedural ground'].hide_select = True
        bpy.data.objects['ICity building procedural base'].hide_select = True
        bpy.data.objects['Procedural building_Default_ICity'].hide_select = True
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text='This might take some time to set up the scene!', icon_value=0)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


class SNA_OT_City_Apply_Dae66(bpy.types.Operator):
    bl_idname = "sna.city_apply_dae66"
    bl_label = "City apply"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_5001C('space type')
        print(str((3 if (bpy.context.scene.sna_city_space_type == 'Custom') else (2 if (bpy.context.scene.sna_city_space_type == 'Presets') else (1 if (bpy.context.scene.sna_city_space_type == 'Park') else (0 if (bpy.context.scene.sna_city_space_type == 'Procedural') else None))))))
        bpy.ops.mesh.attribute_set(value_int=(3 if (bpy.context.scene.sna_city_space_type == 'Custom') else (2 if (bpy.context.scene.sna_city_space_type == 'Presets') else (1 if (bpy.context.scene.sna_city_space_type == 'Park') else (0 if (bpy.context.scene.sna_city_space_type == 'Procedural') else None)))))
        if bpy.context.scene.sna_city_space_type == "Procedural":
            sna_set_active_attribute_572EC_A11A7('Procedural index')
            print(str(variables['sna_procedural_building'].index(bpy.context.scene.sna_procedural_building_browser)))
            bpy.ops.mesh.attribute_set(value_int=variables['sna_procedural_building'].index(bpy.context.scene.sna_procedural_building_browser))
            bpy.data.objects[bpy.context.scene.sna_procedural_building_browser].update_tag(refresh={'DATA'}, )
        elif bpy.context.scene.sna_city_space_type == "Park":
            sna_set_active_attribute_572EC_30DFB('Park')
            print(str(variables['sna_park_list'].index(bpy.context.scene.sna_park_browser)), bpy.context.scene.sna_park_browser)
            bpy.ops.mesh.attribute_set(value_int=variables['sna_park_list'].index(bpy.context.scene.sna_park_browser))
        elif bpy.context.scene.sna_city_space_type == "Presets":
            sna_set_active_attribute_572EC_1DA63('Presets')
            print(str(variables['sna_building_presets'].index(bpy.context.scene.sna_building_presets_browser)), bpy.context.scene.sna_building_presets_browser)
            bpy.ops.mesh.attribute_set(value_int=variables['sna_building_presets'].index(bpy.context.scene.sna_building_presets_browser))
            sna_set_active_attribute_572EC_E3814('Landscape')
            bpy.ops.mesh.attribute_set(value_int=variables['sna_landscape_list'].index(bpy.context.scene.sna_landscape_browser))
        else:
            pass
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


@persistent
def depsgraph_update_pre_handler_361D3(dummy):
    if property_exists("bpy.context.view_layer.objects.active.name", globals(), locals()):
        variables['sna_edit_city'] = ((bpy.context.mode == 'EDIT_MESH') and (bpy.context.view_layer.objects.active.name == 'ICity Base'))


class SNA_OT_Road_Apply_5C3Ab(bpy.types.Operator):
    bl_idname = "sna.road_apply_5c3ab"
    bl_label = "Road apply"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        if ('Texture' == bpy.context.scene.sna_street_asset_type):
            bpy.data.node_groups['Road 2'].nodes[bpy.context.scene.sna_road_materials_type_].inputs[2].default_value = bpy.data.materials[bpy.context.scene.sna_road_materials_browser]
            bpy.data.objects['ICity Road'].update_tag(refresh={'DATA'}, )
        else:
            sna_set_active_attribute_572EC_5FBBE(bpy.context.scene.sna_street_asset_type)
            if 'Light' in bpy.context.scene.sna_street_asset_type:
                bpy.ops.mesh.attribute_set(value_bool=False)
            else:
                bpy.ops.mesh.attribute_set(value_bool=True)
            if bpy.context.scene.sna_street_asset_type == "Cars":
                print('')
            elif bpy.context.scene.sna_street_asset_type == "Sign":
                print('')
            elif bpy.context.scene.sna_street_asset_type == "Texture":
                print('')
            elif bpy.context.scene.sna_street_asset_type == "Imperfection":
                print('')
            elif bpy.context.scene.sna_street_asset_type == "Services":
                bpy.data.node_groups['Road 2'].nodes[bpy.context.scene.sna_street_asset_type].inputs[5].default_value = bpy.data.collections[bpy.context.scene.sna_street_asset_browser]
            else:
                bpy.data.node_groups['Road 2'].nodes[bpy.context.scene.sna_street_asset_type].inputs[4].default_value = bpy.data.objects[bpy.context.scene.sna_street_asset_browser]
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Sync_City_76707(bpy.types.Operator):
    bl_idname = "sna.sync_city_76707"
    bl_label = "sync city"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        for i_D6A85 in range(len(bpy.data.collections['ICity_Procedural'].all_objects)):
            bpy.data.collections['ICity_Procedural'].all_objects[i_D6A85].update_tag(refresh={'DATA'}, )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Floor_Count_Min_C2Cf8(bpy.types.Operator):
    bl_idname = "sna.floor_count_min_c2cf8"
    bl_label = "Floor count min"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_0978B('Floor count')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Floor_Count_Max_Db555(bpy.types.Operator):
    bl_idname = "sna.floor_count_max_db555"
    bl_label = "Floor count max"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_813E4('Floor count max')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Offset_X_A87Eb(bpy.types.Operator):
    bl_idname = "sna.offset_x_a87eb"
    bl_label = "Offset x"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_4CC88('Offset x')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Offset_Y_45B11(bpy.types.Operator):
    bl_idname = "sna.offset_y_45b11"
    bl_label = "Offset y"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_FD2DC('Offset y')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Rotation_Z_4Edcd(bpy.types.Operator):
    bl_idname = "sna.rotation_z_4edcd"
    bl_label = "Rotation z"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_2F07A('Rotation z')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Offset_X_Preset_5A427(bpy.types.Operator):
    bl_idname = "sna.offset_x_preset_5a427"
    bl_label = "Offset x preset"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_92991('Offset x preset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Offset_Y_Preset_Dcad4(bpy.types.Operator):
    bl_idname = "sna.offset_y_preset_dcad4"
    bl_label = "Offset y preset"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_41053('Offset y preset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Rotation_Z_Preset_60648(bpy.types.Operator):
    bl_idname = "sna.rotation_z_preset_60648"
    bl_label = "Rotation z preset"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_0DB67('Rotation z preset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


@persistent
def depsgraph_update_pre_handler_59166(dummy):
    list_0_6a49a = sna_store_atrributes_list_D7786_6A49A()


class SNA_OT_Set_Side_Count_49527(bpy.types.Operator):
    bl_idname = "sna.set_side_count_49527"
    bl_label = "Set side count"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_AE34F('street type')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Assign_Road_Deef9(bpy.types.Operator):
    bl_idname = "sna.assign_road_deef9"
    bl_label = "Assign road"
    bl_description = "Select edge that you want to assign to be road and click"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_BBC9A('Road del')
        bpy.ops.mesh.attribute_set(value_bool=False)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Remove_Road_A2302(bpy.types.Operator):
    bl_idname = "sna.remove_road_a2302"
    bl_label = "Remove road"
    bl_description = "Select edge that you want to not be a road and click"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_7B5C3('Road del')
        bpy.ops.mesh.attribute_set(value_bool=True)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Road_Lanes_Width_93562(bpy.types.Operator):
    bl_idname = "sna.road_lanes_width_93562"
    bl_label = "Road lanes width"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_81051('Road lanes width')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Sidewalk_Width_99Dc0(bpy.types.Operator):
    bl_idname = "sna.sidewalk_width_99dc0"
    bl_label = "Sidewalk width"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_5CC3C('side walk offset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Crosswalk_Offset_B1E82(bpy.types.Operator):
    bl_idname = "sna.crosswalk_offset_b1e82"
    bl_label = "crosswalk offset"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_997D9('crosswalk offset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Append_Assets_Ffd74(bpy.types.Operator):
    bl_idname = "sna.append_assets_ffd74"
    bl_label = "Append Assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        if 'Road' in bpy.context.scene.sna_citystreet_append:
            if 'Texture' in bpy.context.scene.sna_street_asset_type_append:
                print(bpy.context.scene.sna_road_materials_browser_append, '')
                for i_C1098 in range(len(append['sna_road_materials_filtered'])):
                    if append['sna_road_materials_filtered'][i_C1098][0] in bpy.context.scene.sna_road_materials_browser_append:
                        before_data = list(bpy.data.materials)
                        bpy.ops.wm.append(directory=append['sna_road_materials_filtered'][i_C1098][2] + r'\Material', filename=append['sna_road_materials_filtered'][i_C1098][0], link=False)
                        new_data = list(filter(lambda d: not d in before_data, list(bpy.data.materials)))
                        appended_0F2E8 = None if not new_data else new_data[0]
                        if property_exists("appended_0F2E8", globals(), locals()):
                            appended_0F2E8.sna_asset_category_path_material = append['sna_road_materials_filtered'][i_C1098][2]
                            bpy.data.objects['ICity_Materials'].data.materials.append(material=appended_0F2E8, )
            else:
                if ('Services' in bpy.context.scene.sna_street_asset_type_append or 'Imperfection' in bpy.context.scene.sna_street_asset_type_append):
                    print('')
                    for i_3A396 in range(len(append['sna_road_assets_filtered'])):
                        if bpy.context.scene.sna_street_asset_type_append in append['sna_road_assets_filtered'][i_3A396][0]:
                            print(append['sna_road_assets_filtered'][i_3A396][2], append['sna_road_assets_filtered'][i_3A396][0])
                            before_data = list(bpy.data.collections)
                            bpy.ops.wm.append(directory=append['sna_road_assets_filtered'][i_3A396][2] + r'\Collection', filename=append['sna_road_assets_filtered'][i_3A396][0], link=False)
                            new_data = list(filter(lambda d: not d in before_data, list(bpy.data.collections)))
                            appended_BBE11 = None if not new_data else new_data[0]
                            if property_exists("bpy.data.collections[append['sna_road_assets_filtered'][i_3A396][0]]", globals(), locals()):
                                bpy.data.collections[append['sna_road_assets_filtered'][i_3A396][0]].sna_asset_category_path_collection = append['sna_road_assets_filtered'][i_3A396][2]
                                print(append['sna_road_assets_filtered'][i_3A396][0], ('ICity_Services' if 'Services' in append['sna_road_assets_filtered'][i_3A396][0] else 'ICity_Imperfection'))
                                sna_move_to_collection_A3C17_7B15A(False, bpy.data.collections[append['sna_road_assets_filtered'][i_3A396][0]], None, bpy.data.collections[('ICity_Services' if 'Services' in append['sna_road_assets_filtered'][i_3A396][0] else 'ICity_Imperfection')])
                else:
                    print(bpy.context.scene.sna_road_browser_append, '')
                    for i_51FAF in range(len(append['sna_road_assets_filtered'])):
                        if append['sna_road_assets_filtered'][i_51FAF][0] in bpy.context.scene.sna_road_browser_append:
                            before_data = list(bpy.data.objects)
                            bpy.ops.wm.append(directory=append['sna_road_assets_filtered'][i_51FAF][2] + r'\Object', filename=append['sna_road_assets_filtered'][i_51FAF][0], link=False)
                            new_data = list(filter(lambda d: not d in before_data, list(bpy.data.objects)))
                            appended_F0624 = None if not new_data else new_data[0]
                            if property_exists("appended_F0624", globals(), locals()):
                                appended_F0624.sna_asset_category_path_object = append['sna_road_assets_filtered'][i_51FAF][2]
                                sna_move_to_collection_A3C17_97000(True, appended_F0624, None, bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type_append])
        else:
            if 'Procedural' in bpy.context.scene.sna_city_space_type_append:
                for i_F2E6F in range(len(append['sna_city_assets_filtered'])):
                    if append['sna_city_assets_filtered'][i_F2E6F][0] in bpy.context.scene.sna_city_browser_append:
                        before_data = list(bpy.data.collections)
                        bpy.ops.wm.append(directory=append['sna_city_assets_filtered'][i_F2E6F][2] + r'\Collection', filename=append['sna_city_assets_filtered'][i_F2E6F][0], link=False)
                        new_data = list(filter(lambda d: not d in before_data, list(bpy.data.collections)))
                        appended_CBAC9 = None if not new_data else new_data[0]
                        if property_exists("appended_CBAC9", globals(), locals()):
                            appended_CBAC9.sna_asset_category_path_collection = append['sna_city_assets_filtered'][i_F2E6F][2]
                            sna_move_to_collection_A3C17_D6B3F(False, bpy.data.collections[bpy.context.scene.sna_city_browser_append], None, bpy.data.collections['ICity Assets'])
                            for i_05E8B in range(len(bpy.data.collections[bpy.context.scene.sna_city_browser_append + ' Objects'].all_objects)):
                                bpy.data.collections['ICity_Procedural'].objects.link(object=bpy.data.collections[bpy.context.scene.sna_city_browser_append + ' Objects'].all_objects[i_05E8B], )
                                if property_exists("bpy.data.collections[bpy.context.scene.sna_city_browser_append + ' Objects'].all_objects[i_05E8B]", globals(), locals()):
                                    bpy.data.collections[bpy.context.scene.sna_city_browser_append + ' Objects'].all_objects[i_05E8B].sna_asset_category_path_object = append['sna_city_assets_filtered'][i_F2E6F][2]
            else:
                for i_AF454 in range(len(append['sna_city_assets_filtered'])):
                    if append['sna_city_assets_filtered'][i_AF454][0] in bpy.context.scene.sna_city_browser_append:
                        before_data = list(bpy.data.objects)
                        bpy.ops.wm.append(directory=append['sna_city_assets_filtered'][i_AF454][2] + r'\Object', filename=append['sna_city_assets_filtered'][i_AF454][0], link=False)
                        new_data = list(filter(lambda d: not d in before_data, list(bpy.data.objects)))
                        appended_770CC = None if not new_data else new_data[0]
                        if property_exists("appended_770CC", globals(), locals()):
                            appended_770CC.sna_asset_category_path_object = append['sna_city_assets_filtered'][i_AF454][2]
                            sna_move_to_collection_A3C17_D47A1(True, appended_770CC, None, bpy.data.collections['ICity_' + bpy.context.scene.sna_city_space_type_append])
            bpy.context.scene.sna_city_space_type = bpy.context.scene.sna_city_space_type
            bpy.data.collections['ICity Assets'].hide_viewport = True
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Append_Landscape_C97Bb(bpy.types.Operator):
    bl_idname = "sna.append_landscape_c97bb"
    bl_label = "Append landscape"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        for i_9DA95 in range(len(append['sna_landscape_filtered'])):
            if append['sna_landscape_filtered'][i_9DA95][0] in bpy.context.scene.sna_landscape_browser_append:
                before_data = list(bpy.data.objects)
                bpy.ops.wm.append(directory=append['sna_landscape_filtered'][i_9DA95][2] + r'\Object', filename=append['sna_landscape_filtered'][i_9DA95][0], link=False)
                new_data = list(filter(lambda d: not d in before_data, list(bpy.data.objects)))
                appended_5A06C = None if not new_data else new_data[0]
                if property_exists("appended_5A06C", globals(), locals()):
                    appended_5A06C.sna_asset_category_path_object = append['sna_landscape_filtered'][i_9DA95][2]
                    sna_move_to_collection_A3C17_575C9(True, appended_5A06C, None, bpy.data.collections['ICity_Landscape'])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Intersection_Offset_16E01(bpy.types.Operator):
    bl_idname = "sna.intersection_offset_16e01"
    bl_label = "Intersection Offset"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You have to be in Edit city mode!')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        sna_set_active_attribute_572EC_62FA0('offset')
        bpy.ops.mesh.attribute_set('INVOKE_DEFAULT', )
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Edit_City_D7Cab(bpy.types.Operator):
    bl_idname = "sna.edit_city_d7cab"
    bl_label = "Edit city"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        bpy.context.view_layer.objects.active = bpy.data.objects['ICity Base']
        if (bpy.context.mode == 'EDIT_MESH'):
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            bpy.ops.object.select_all('INVOKE_DEFAULT', action='DESELECT')
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.sna.light_city_20ca9()
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Delete_From_Scene_City_324Ff(bpy.types.Operator):
    bl_idname = "sna.delete_from_scene_city_324ff"
    bl_label = "Delete from scene city"
    bl_description = "Delete from scene."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('You cant remove this!')
        return not 'Procedural' in bpy.context.scene.sna_city_space_type

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.collections['ICity Assets'].hide_viewport = False
        bpy.data.objects[(bpy.context.scene.sna_building_presets_browser if 'Presets' in bpy.context.scene.sna_city_space_type else (bpy.context.scene.sna_park_browser if 'Park' in bpy.context.scene.sna_city_space_type else None))].select_set(state=True, )
        bpy.ops.object.delete(confirm=True)
        bpy.context.scene.sna_city_space_type = bpy.context.scene.sna_city_space_type
        bpy.data.collections['ICity Assets'].hide_viewport = True
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Light_City_20Ca9(bpy.types.Operator):
    bl_idname = "sna.light_city_20ca9"
    bl_label = "Light city"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        bpy.data.node_groups['Light mode'].nodes['Boolean Math.003'].inputs[0].default_value = (variables['sna_edit_city'] and bpy.context.scene.sna_light_mode)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Delete_From_Scene_7C7D8(bpy.types.Operator):
    bl_idname = "sna.delete_from_scene_7c7d8"
    bl_label = "Delete from scene"
    bl_description = "Delete from scene road assets."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not variables['sna_edit_city']

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.collections['ICity Assets'].hide_viewport = False
        if 'Texture' in bpy.context.scene.sna_street_asset_type:
            if property_exists("bpy.data.materials[bpy.context.scene.sna_road_materials_browser]", globals(), locals()):
                bpy.data.materials.remove(material=bpy.data.materials[bpy.context.scene.sna_road_materials_browser], )
        else:
            if ('Imperfection' in bpy.context.scene.sna_street_asset_type or 'Services' in bpy.context.scene.sna_street_asset_type):
                bpy.data.collections.remove(collection=bpy.data.collections[bpy.context.scene.sna_street_asset_browser], )
            else:
                bpy.data.objects[bpy.context.scene.sna_street_asset_browser].select_set(state=True, )
                bpy.ops.object.delete(confirm=True)
        bpy.context.scene.sna_street_asset_type = bpy.context.scene.sna_street_asset_type
        bpy.data.collections['ICity Assets'].hide_viewport = True
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Road_Remove_Aa51D(bpy.types.Operator):
    bl_idname = "sna.road_remove_aa51d"
    bl_label = "Road Remove"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not (not variables['sna_edit_city'])

    def execute(self, context):
        if ('Texture' == bpy.context.scene.sna_street_asset_type):
            pass
        else:
            sna_set_active_attribute_572EC_42E3D(bpy.context.scene.sna_street_asset_type)
            if 'Light' in bpy.context.scene.sna_street_asset_type:
                bpy.ops.mesh.attribute_set(value_bool=True)
            else:
                bpy.ops.mesh.attribute_set(value_bool=False)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_AddonPreferences_7CCE1(bpy.types.AddonPreferences):
    bl_idname = 'icity'
    sna_assets_path: bpy.props.StringProperty(name='Assets path', description='', default='', subtype='DIR_PATH', maxlen=0)

    def draw(self, context):
        if not (False):
            layout = self.layout
            box_A083F = layout.box()
            box_A083F.alert = False
            box_A083F.enabled = True
            box_A083F.active = True
            box_A083F.use_property_split = False
            box_A083F.use_property_decorate = False
            box_A083F.alignment = 'Expand'.upper()
            box_A083F.scale_x = 1.0
            box_A083F.scale_y = 1.0
            if not True: box_A083F.operator_context = "EXEC_DEFAULT"
            col_D81F8 = box_A083F.column(heading='', align=False)
            col_D81F8.alert = False
            col_D81F8.enabled = True
            col_D81F8.active = True
            col_D81F8.use_property_split = False
            col_D81F8.use_property_decorate = False
            col_D81F8.scale_x = 1.0
            col_D81F8.scale_y = 1.7200000286102295
            col_D81F8.alignment = 'Expand'.upper()
            col_D81F8.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
            col_D81F8.prop(bpy.context.preferences.addons[__name__].preferences, 'sna_assets_path', text='Assets path', icon_value=0, emboss=True)
            op = col_D81F8.operator('sna.refresh_c6cb8', text='Read files', icon_value=0, emboss=True, depress=False)
            col_D81F8.label(text=('No assets found!' if ((None == append['sna_all_assets']) or (None == append['sna_all_materials'])) else 'Assets found' + '(' + str(int(len(append['sna_all_assets']) + len(append['sna_all_materials']))) + ')'), icon_value=0)


def sna_remove_last_path_5D152(String):
    return String.replace('\\' + String.split('\\')[int(len(String.split('\\')) - 1.0)], '')


def sna_move_to_collection_A3C17(Object_collection, Item, From__default_active_collection, To):
    if Object_collection:
        if (property_exists("To.objects", globals(), locals()) and Item.name in To.objects):
            pass
        else:
            To.objects.link(object=bpy.data.objects[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).objects.unlink(object=bpy.data.objects[Item.name], )
    else:
        To.children.link(child=bpy.data.collections[Item.name], )
        (bpy.context.view_layer.active_layer_collection.collection if (From__default_active_collection == None) else From__default_active_collection).children.unlink(child=bpy.data.collections[Item.name], )
    return


class SNA_OT_Test_Assets_B9626(bpy.types.Operator):
    bl_idname = "sna.test_assets_b9626"
    bl_label = "test assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        print(os.path.join('','assets'))
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_street_assets_lists_1588D():
    variables['sna_street_asset_browser'] = []
    for i_97E63 in range(len((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects))):
        if ('Signs' if (bpy.context.scene.sna_street_asset_type_append == 'Signs') else ('Tree base' if (bpy.context.scene.sna_street_asset_type_append == 'Tree base') else ('Services' if (bpy.context.scene.sna_street_asset_type_append == 'Services') else ('Trees' if (bpy.context.scene.sna_street_asset_type_append == 'Trees') else ('Bench' if (bpy.context.scene.sna_street_asset_type_append == 'Bench') else ('Lights' if (bpy.context.scene.sna_street_asset_type_append == 'Lights') else None)))))) in ((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else (bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name):
            variables['sna_street_asset_browser'].append([((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else (bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name), ((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else (bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name), '', load_preview_icon((os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + ((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else (bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name) + '.png' if 'ICity' in ((bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else (bpy.data.collections if ('Trees' in bpy.context.scene.sna_street_asset_type_append or 'Services' in bpy.context.scene.sna_street_asset_type_append) else bpy.data.objects)[i_97E63].name) else os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + 'Custom asset' + '.png'))])
    return


def sna_sidewalk_mat_C9E1B():
    variables['sna_sidewalk_mat'] = []
    for i_22F91 in range(len(bpy.data.materials)):
        if 'Sidewalk' in bpy.data.materials[i_22F91].name:
            variables['sna_sidewalk_mat'].append([bpy.data.materials[i_22F91].name, bpy.data.materials[i_22F91].name, '', load_preview_icon((os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + bpy.data.materials[i_22F91].name + '.png' if 'Sidewalk' in bpy.data.materials[i_22F91].name else os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + 'Custom asset' + '.png'))])
            print(str([bpy.data.materials[i_22F91].name, bpy.data.materials[i_22F91].name, '', load_preview_icon((os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + bpy.data.materials[i_22F91].name + '.png' if 'Sidewalk' in bpy.data.materials[i_22F91].name else os.path.join(os.path.dirname(__file__), 'assets', 'icons') + '//' + 'Custom asset' + '.png'))]))
            return


def sna_sidewalk_mat_enum_items(self, context):
    enum_items = variables['sna_sidewalk_mat']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


class SNA_OT_Refresh_Edit_F156A(bpy.types.Operator):
    bl_idname = "sna.refresh_edit_f156a"
    bl_label = "Refresh edit"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_building_presets_browser_enum_items(self, context):
    enum_items = variables['sna_building_presets_browser']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_park_browser_enum_items(self, context):
    enum_items = variables['sna_park_browser']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_procedural_building_browser_enum_items(self, context):
    enum_items = variables['sna_procedural_building_browser']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_street_asset_browser_enum_items(self, context):
    enum_items = variables['sna_street_asset_browser']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


def sna_landscape_browser_enum_items(self, context):
    enum_items = variables['sna_landscape_browser']
    return [make_enum_item(item[0], item[1], item[2], item[3], i) for i, item in enumerate(enum_items)]


class SNA_OT_Filter_Presets_Fb5A4(bpy.types.Operator):
    bl_idname = "sna.filter_presets_fb5a4"
    bl_label = "Filter Presets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        print('')
        variables['sna_building_presets'] = []
        for i_082B6 in range(len(bpy.data.collections[('ICity_Presets' if 'All' in '' else 'ICity_Presets')].all_objects)):
            variables['sna_building_presets'].append(bpy.data.collections[('ICity_Presets' if 'All' in '' else 'ICity_Presets')].all_objects[i_082B6].name)
        variables['sna_building_presets_browser'] = []
        for i_83ED4 in range(len(variables['sna_building_presets'])):
            print('')
            variables['sna_building_presets_browser'].append([variables['sna_building_presets'][i_83ED4], variables['sna_building_presets'][i_83ED4], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + variables['sna_building_presets'][i_83ED4] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + variables['sna_building_presets'][i_83ED4] + '.png').replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + variables['sna_building_presets'][i_83ED4] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[variables['sna_building_presets'][i_83ED4]].sna_asset_category_path_object)) + '\\' + variables['sna_building_presets'][i_83ED4] + '.png').replace('\\', '/'))))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Procedural_Building_Filter_05Bed(bpy.types.Operator):
    bl_idname = "sna.procedural_building_filter_05bed"
    bl_label = "Procedural building filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        list_names_0_eac41 = sna_generate_icon_list_from_collection_6BD3F_EAC41(bpy.data.collections['ICity_Procedural'].all_objects)
        print(str(list_names_0_eac41))
        variables['sna_procedural_building_browser'] = []
        for i_3BAC1 in range(len(list_names_0_eac41)):
            print(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + list_names_0_eac41[i_3BAC1] + '.png').replace('\\', '/'))
            bpy.data.objects[list_names_0_eac41[i_3BAC1]].modifiers[0]['Socket_0'] = i_3BAC1
            bpy.data.objects[list_names_0_eac41[i_3BAC1]].modifiers[0]['Socket_1'] = bpy.data.objects['ICity building procedural base']
            bpy.data.objects[list_names_0_eac41[i_3BAC1]].update_tag(refresh={'DATA'}, )
            variables['sna_procedural_building_browser'].append([list_names_0_eac41[i_3BAC1], list_names_0_eac41[i_3BAC1], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + list_names_0_eac41[i_3BAC1] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + list_names_0_eac41[i_3BAC1] + '.png').replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + list_names_0_eac41[i_3BAC1] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_eac41[i_3BAC1]].sna_asset_category_path_object)) + '\\' + list_names_0_eac41[i_3BAC1] + '.png').replace('\\', '/'))))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Park_Filter_5A7A2(bpy.types.Operator):
    bl_idname = "sna.park_filter_5a7a2"
    bl_label = "Park filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        list_names_0_b83d7 = sna_generate_icon_list_from_collection_6BD3F_B83D7(bpy.data.collections['ICity_Park'].all_objects)
        print(str(list_names_0_b83d7))
        variables['sna_park_browser'] = []
        for i_5519B in range(len(list_names_0_b83d7)):
            print(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + list_names_0_b83d7[i_5519B] + '.png').replace('\\', '/'))
            variables['sna_park_browser'].append([list_names_0_b83d7[i_5519B], list_names_0_b83d7[i_5519B], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + list_names_0_b83d7[i_5519B] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + list_names_0_b83d7[i_5519B] + '.png').replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + list_names_0_b83d7[i_5519B] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_b83d7[i_5519B]].sna_asset_category_path_object)) + '\\' + list_names_0_b83d7[i_5519B] + '.png').replace('\\', '/'))))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Landscape_Filter_0Bf89(bpy.types.Operator):
    bl_idname = "sna.landscape_filter_0bf89"
    bl_label = "Landscape filter"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        list_names_0_bbaa3 = sna_generate_icon_list_from_collection_6BD3F_BBAA3(bpy.data.collections['ICity_Landscape'].all_objects)
        print(str(list_names_0_bbaa3))
        variables['sna_landscape_browser'] = []
        for i_C2F17 in range(len(list_names_0_bbaa3)):
            print('')
            variables['sna_landscape_browser'].append([list_names_0_bbaa3[i_C2F17], list_names_0_bbaa3[i_C2F17], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + list_names_0_bbaa3[i_C2F17] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + list_names_0_bbaa3[i_C2F17] + '.png').replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + list_names_0_bbaa3[i_C2F17] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_bbaa3[i_C2F17]].sna_asset_category_path_object)) + '\\' + list_names_0_bbaa3[i_C2F17] + '.png').replace('\\', '/'))))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_Filter_Street_Assets_C5C0E(bpy.types.Operator):
    bl_idname = "sna.filter_street_assets_c5c0e"
    bl_label = "Filter street assets"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        if ('Services' in bpy.context.scene.sna_street_asset_type or 'Imperfection' in bpy.context.scene.sna_street_asset_type):
            if (property_exists("bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].children", globals(), locals()) and (len(bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].children) > 0)):
                list_names_0_edbef = sna_generate_icon_list_from_collection_6BD3F_EDBEF(bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].children)
                variables['sna_street_asset_browser'] = []
                for i_2FB8C in range(len(list_names_0_edbef)):
                    variables['sna_street_asset_browser'].append([list_names_0_edbef[i_2FB8C], list_names_0_edbef[i_2FB8C], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + list_names_0_edbef[i_2FB8C] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + list_names_0_edbef[i_2FB8C] + '.png').replace('\\', '/')))) else (load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + 'Custom asset.png').replace('\\', '/')) if (load_preview_icon(r'') == load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + list_names_0_edbef[i_2FB8C] + '.png').replace('\\', '/'))) else load_preview_icon(bpy.path.abspath(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.collections[list_names_0_edbef[i_2FB8C]].sna_asset_category_path_collection)) + '\\' + list_names_0_edbef[i_2FB8C] + '.png').replace('\\', '/'))))])
        else:
            if (property_exists("bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].all_objects", globals(), locals()) and (len(bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].all_objects) > 0)):
                list_names_0_593da = sna_generate_icon_list_from_collection_6BD3F_593DA(bpy.data.collections['ICity_' + bpy.context.scene.sna_street_asset_type].all_objects)
                variables['sna_street_asset_browser'] = []
                for i_EA4BD in range(len(list_names_0_593da)):
                    variables['sna_street_asset_browser'].append([list_names_0_593da[i_EA4BD], list_names_0_593da[i_EA4BD], '', (load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', '16e8992ffebf47daba61aa6815a7177b (1).png')) if (load_preview_icon(r'') == (load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png') if (load_preview_icon(r'') == load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + list_names_0_593da[i_EA4BD] + '.png')) else load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + list_names_0_593da[i_EA4BD] + '.png'))) else (load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + 'Custom asset.png') if (load_preview_icon(r'') == load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + list_names_0_593da[i_EA4BD] + '.png')) else load_preview_icon(os.path.dirname(sna_replace_to_addon_path_4DC0E(bpy.data.objects[list_names_0_593da[i_EA4BD]].sna_asset_category_path_object)) + '\\' + list_names_0_593da[i_EA4BD] + '.png')))])
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def sna_replace_to_addon_path_4DC0E(path):
    addon_assets = bpy.path.abspath(os.path.join(os.path.dirname(__file__), 'assets', 'Assets'))
    return bpy.path.abspath(path).replace('\\', '/')


def sna_is_collection_not_empty_B0A78(Collection_name):
    return (len(bpy.data.collections[Collection_name].all_objects) != 0)

def sna_update_sna_street_asset_type_append(self, context):
    sna_update_sna_street_asset_type_append_FC104(self, context)
    sna_update_sna_street_asset_type_append_F3D9F(self, context)


def sna_update_sna_city_space_type(self, context):
    sna_update_sna_city_space_type_F658C(self, context)
    sna_update_sna_city_space_type_AE473(self, context)


def sna_sidewalk_curb_mat_enum_items(self, context):
    return [("No Items", "No Items", "No generate enum items node found to create items!", "ERROR", 0)]


def sna_append_browser_enum_items(self, context):
    return [("No Items", "No Items", "No generate enum items node found to create items!", "ERROR", 0)]

# 自定义智能生成城市类
import bpy
import bmesh
from SCGS.weather import *
import json
import re
import regex
import numpy as np
import openai
import os
import ast

## 添加的部分！！
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_TEX_BLEND = r"C:\Program Files\Blender Foundation\Blender 4.1\4.1\scripts\addons\SCGS\custom_assets\myroad.blend"
CUSTOM_TEX_NAME = "路面材质" 


# ---------------- SCGS 生态化场景扩展：山峦 / 湖水 / 河流 / 动态船只 ----------------
def scgs_get_or_create_collection(name):
    """获取或创建集合，避免生态对象散落在场景根集合。"""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def scgs_link_object_to_collection(obj, collection):
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    return obj


def scgs_create_principled_mat(name, color, roughness=0.55, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = color
    if alpha < 1.0:
        mat.blend_method = 'BLEND'
        mat.use_screen_refraction = True
        mat.show_transparent_back = True
    return mat


def scgs_create_mountain_ring(collection, radius=360, segments=96, height=85, noise_strength=0.42):
    """在城市外围创建一圈低多边形山峦。"""
    name = "SCGS_Eco_Mountain_Ring"
    old = bpy.data.objects.get(name)
    if old:
        return old
    verts, faces = [], []
    import math, random
    random.seed(42)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        wave = 1.0 + 0.12 * math.sin(i * 0.7) + random.uniform(-noise_strength, noise_strength) * 0.08
        outer = radius * wave
        inner = radius * 0.78 * (1.0 + 0.06 * math.sin(i * 1.3))
        peak = radius * 0.89 * (1.0 + 0.09 * math.cos(i * 0.9))
        verts.append((outer * math.cos(angle), outer * math.sin(angle), -2))
        verts.append((inner * math.cos(angle), inner * math.sin(angle), 0))
        verts.append((peak * math.cos(angle), peak * math.sin(angle), height * (0.55 + random.random() * 0.75)))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i*3, j*3, j*3+2, i*3+2))
        faces.append((i*3+1, i*3+2, j*3+2, j*3+1))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(scgs_create_principled_mat("SCGS_Mountain_Material", (0.18, 0.30, 0.16, 1), 0.9))
    scgs_link_object_to_collection(obj, collection)
    return obj


def scgs_create_lake(collection, center=(280, 250, -0.15), radius_x=100, radius_y=70, segments=96):
    """创建椭圆湖面。"""
    name = "SCGS_Eco_Lake"
    old = bpy.data.objects.get(name)
    if old:
        return old
    import math

    verts = [center]
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((center[0] + radius_x * math.cos(a), center[1] + radius_y * math.sin(a), center[2]))

    faces = []
    for i in range(1, segments + 1):
        next_i = 1 if i == segments else i + 1
        faces.append((0, i, next_i))

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(scgs_create_principled_mat("SCGS_Lake_Water_Material", (0.05, 0.32, 0.55, 0.62), 0.2, 0.0, 0.62))
    scgs_link_object_to_collection(obj, collection)
    return obj


def scgs_create_river(collection):
    """创建一条贴近地面的平面河流，沿山脚蜿蜒并流入湖泊。"""
    name = "SCGS_Eco_River"
    old = bpy.data.objects.get(name)
    if old:
        return old

    import math

    # 绕山脚，最后接近湖泊
    pts = [

    (-80, -317, -0.06),
    (-55, -336, -0.06),
    (-30, -326, -0.06),
    (22, -392, -0.06),
    (50, -391, -0.06),
    (79, -395, -0.06),
    (95, -352, -0.06),
    (133, -281, -0.06),
    (164, -283, -0.06),
    (243, -320, -0.06),
    (263, -296, -0.06),
    (283, -250, -0.06),
    (264, -195, -0.06),
    (267, -153, -0.06),
    (380, -129, -0.06),
    (392, -78, -0.06),
    (338, -21, -0.06),
    (363, 0, -0.06),
    (403, 53, -0.06),
    (400, 78, -0.06),
    (306, 113, -0.06),
    (312, 130, -0.06),
    (305, 153, -0.06),
    (290, 164, -0.06),
    (309, 225, -0.06)

    ]
    river_width = 8

    verts = []
    faces = []

    for i, p in enumerate(pts):
        if i == 0:
            dx = pts[i + 1][0] - p[0]
            dy = pts[i + 1][1] - p[1]
        elif i == len(pts) - 1:
            dx = p[0] - pts[i - 1][0]
            dy = p[1] - pts[i - 1][1]
        else:
            dx = pts[i + 1][0] - pts[i - 1][0]
            dy = pts[i + 1][1] - pts[i - 1][1]

        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            nx, ny = 0, 0
        else:
            nx = -dy / length
            ny = dx / length

        verts.append((p[0] + nx * river_width, p[1] + ny * river_width, p[2]))
        verts.append((p[0] - nx * river_width, p[1] - ny * river_width, p[2]))

    for i in range(len(pts) - 1):
        faces.append((i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2))

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(
        scgs_create_principled_mat(
            "SCGS_River_Water_Material",
            (0.04, 0.26, 0.48, 0.68),
            0.25,
            0.0,
            0.68
        )
    )

    scgs_link_object_to_collection(obj, collection)
    return obj


def scgs_append_custom_boat_if_exists(collection, location):
    """优先加载 custom_assets/myboat.blend 中的 Boat/船 物体；没有则返回 None 使用程序化船。"""
    boat_file = os.path.join(ADDON_DIR, "custom_assets", "myboat.blend")
    if not os.path.exists(boat_file):
        return None
    try:
        with bpy.data.libraries.load(boat_file, link=False) as (data_from, data_to):
            candidates = [n for n in data_from.objects if n.lower() in {"boat", "scgs_boat", "船", "小船"} or "boat" in n.lower() or "船" in n]
            if not candidates:
                return None
            data_to.objects = [candidates[0]]
        obj = bpy.data.objects.get(candidates[0])
        if obj:
            obj.name = "SCGS_Eco_Boat"
            obj.location = location
            scgs_link_object_to_collection(obj, collection)
            return obj
    except Exception as exc:
        print(f"加载自定义船只失败，改用程序化船只: {exc}")
    return None


def scgs_create_procedural_boat(collection):

    # 船体
    bpy.ops.mesh.primitive_cube_add(location=(280, 250, 0.25))
    boat = bpy.context.active_object
    boat.name = "SCGS_Boat"

    boat.scale = (2.8, 1.0, 0.45)

    # 前后收窄，更像船
    mod = boat.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = 0.08
    mod.segments = 3

    bpy.ops.object.shade_smooth()

    # 船体材质
    mat = bpy.data.materials.new(name="Boat_Mat")
    mat.use_nodes = True

    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.15, 0.15, 0.18, 1)
        bsdf.inputs["Roughness"].default_value = 0.6

    boat.data.materials.append(mat)

    # 船舱
    bpy.ops.mesh.primitive_cube_add(location=(280, 250, 0.75))
    cabin = bpy.context.active_object
    cabin.scale = (0.9, 0.55, 0.35)

    cabin_mat = bpy.data.materials.new(name="Cabin_Mat")
    cabin_mat.use_nodes = True

    bsdf2 = next((n for n in cabin_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf2:
        bsdf2.inputs["Base Color"].default_value = (0.8, 0.8, 0.85, 1)
        cabin.data.materials.append(cabin_mat)

    # 合并
    bpy.ops.object.select_all(action='DESELECT')
    boat.select_set(True)
    cabin.select_set(True)

    bpy.context.view_layer.objects.active = boat
    bpy.ops.object.join()

    collection.objects.link(boat)

    return boat


def scgs_animate_boat(boat, lake_center=(280, 250, 1.1), radius_x=70, radius_y=38):
    import math

    # 右边 1/3
    angle_start = -math.pi / 3
    angle_end = math.pi / 3

    for frame, angle in [(1, angle_start), (80, (angle_start+angle_end)/2), (160, angle_end)]:
        boat.location = (
            lake_center[0] + radius_x * math.cos(angle),
            lake_center[1] + radius_y * math.sin(angle),
            lake_center[2]
        )
        boat.rotation_euler[2] = angle + math.pi / 2
        boat.keyframe_insert(data_path="location", frame=frame)
        boat.keyframe_insert(data_path="rotation_euler", frame=frame)
        
    if boat.animation_data and boat.animation_data.action:
        for fc in boat.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return boat

def scgs_clear_old_ecology():
    for obj in list(bpy.data.objects):
        if obj.name.startswith("SCGS_Boat") or obj.name.startswith("SCGS_Eco_"):
            bpy.data.objects.remove(obj, do_unlink=True)

def scgs_generate_ecology_scene():
    """生成城市周边生态化元素，可被城市生成和编辑流程复用。"""
    scgs_clear_old_ecology()
    coll = scgs_get_or_create_collection("SCGS_Ecology")
    mountain = scgs_create_mountain_ring(coll)
    lake = scgs_create_lake(coll)
    river = scgs_create_river(coll)
    boat = scgs_create_procedural_boat(coll)
    scgs_animate_boat(boat)
    print("SCGS生态化场景已生成：山峦、湖水、河流、动态船只")
    return {"mountain": mountain, "lake": lake, "river": river, "boat": boat}



os.environ["http_proxy"] = "http://localhost:7890"
os.environ["https_proxy"] = "http://localhost:7890"

from SCGS.dashscope_client import chat_completions_content

class SNA_OT_Generate_Ecology_9F2A1(bpy.types.Operator):
    bl_idname = "sna.generate_ecology_9f2a1"
    bl_label = "Generate Ecology Scene"
    bl_description = "Generate mountains, lake, river and animated boats around the current city"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0):
            cls.poll_message_set('')
        return True

    def execute(self, context):
        scgs_generate_ecology_scene()
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class SNA_OT_City_Generation(bpy.types.Operator):
    bl_idname = "sna.city_generation"
    bl_label = "3D city generation"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

################################################## 提示词部分 ##################################################################################
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
                - Example3: If the description contains something like "Help me create a Taiwanese style city", you need to return: "Taiwanese type".
                - Return format: [city_type]
            2.weather:
                - weather is selected only from the following list: sunny, rainy, snowy.
                - Example1: If the description contains something like "Help me create a retro-style city for sunny", you need to return: "sunny"
                - Example2: If the description contains something like "Help me create a retro-style city for snowy", you need to return: "snowy"
                - Return format: [weather]


                Output: Provide the information in a valid JSON object. The values for city_type and weather MUST be arrays with exactly one string element. For example:
                {{"city_type": ["modern type"], "weather": ["sunny"]}}
                Do NOT return strings directly like "modern type" - always wrap in an array.
                """

            response_str = chat_completions_content(
                messages=[
                    {"role": "user", "content": context_msg},
                ],
                temperature=0.4,
                max_tokens=4096,
            )
            raw_response = response_str.replace("\n", "").strip()
            start = raw_response.find('{')
            end = raw_response.rfind('}')
            if start >= 0 and end > start:
                response = json.loads(raw_response[start:end + 1])
            else:
                raise ValueError(f"无法从LLM响应中提取JSON: {raw_response[:200]}")

            return response

############################################################ 天气部分 ############################################################
    # 雨天综合函数
    def rain_weather(self,lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,
                     rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                     rain_fall_scale, clouds_loaction, clouds_scale):
        # 添加闪电
        def load_lighting(socket_2_value=5.0, socket_3_value=5.0, socket_4_value=2.0, loaction=(0, 0, 30)):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Lightning"
            object_name = "WI Lightning"

            # 检查文件是否存在
            if not os.path.exists(blend_file_path):
                print(f"指定的文件路径不存在：{blend_file_path}")
                return

            # 打开指定的.blend文件
            with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
                # 检查集合是否存在
                if collection_name in data_from.collections:
                    # 加载集合
                    data_to.collections = [collection_name]
                else:
                    print(f"集合 {collection_name} 不存在于指定文件中。")
                    return

            # 直接按名称获取对象（避免 KeyError）
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                print(f"对象 {object_name} 未加载成功（可能集合/对象名不匹配）。")
                return

            # 将对象链接到当前场景（已存在则跳过）
            try:
                if bpy.context.scene.collection.objects.get(obj.name) is None:
                    bpy.context.scene.collection.objects.link(obj)
            except Exception as e:
                print(f"链接对象 {object_name} 到场景失败：{e}")

            obj.location = loaction
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
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
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Rain"
            object_name = "WI Rain Fall"

            # 检查文件是否存在
            if not os.path.exists(blend_file_path):
                print(f"指定的文件路径不存在：{blend_file_path}")
                return

            # 打开指定的.blend文件
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
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
            obj.select_set(True)
            mod = obj.modifiers.get("WI Rain Fall")
            if mod is None:
                print("未找到 modifier: WI Rain Fall（无法设置 Socket 参数）。")
                return
            mod["Socket_2"] = socket_2_value
            mod["Socket_3"] = socket_3_value
            mod["Socket_4"] = socket_4_value

        def load_clouds(loaction=(0, 0, 30), scale=(1.0, 1.0, 1.0)):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "Collection 5"
            object_name = "Clouds"

            # 检查文件是否存在
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

        # 加载闪电
        load_lighting(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction)
        # 加载雨水下落
        load_rain_fall(rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                       rain_fall_scale)
        # 加载云
        load_clouds(clouds_loaction, clouds_scale)

        # 创建雨天相关物体集合 并且将所有物体加入
        collection_name = "Rain Weather Collection"
        if collection_name not in bpy.data.collections:
            rain_weather_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(rain_weather_collection)
            print(f"集合 '{collection_name}' 已创建。")
        else:
            rain_weather_collection = bpy.data.collections[collection_name]
            print(f"集合 '{collection_name}' 已存在。")

        # 将对象移动到集合
        object_names = ["Clouds", "WI Lightning", "WI Rain Fall"]
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                # 从所有集合中移除
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                # 添加到目标集合
                rain_weather_collection.objects.link(obj)
                print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
            else:
                print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")



    def snow_weather(self,collection, snow_ground_loaction, snow_ground_dimensions, density, thickness, snow_loaction,
                     snow_scale):
        def load_snow_ground(collection_mesh, loaction=(0, 0, 6.2779), dimensions=(0, 0, 0), density=0.8,
                             thickness=0.8):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Snow"
            object_name = "WI Snow Ground"

            # 检查文件是否存在
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
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
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
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Snow"
            object_name = "WI Snow Fall"

            # 检查文件是否存在
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
            # 添加雪景的mesh移动到snow集合里面

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

        move_snow_ground()
        # load_snow_ground(collection, snow_ground_loaction, snow_ground_dimensions, density, thickness)
        snow_fall(snow_loaction, snow_scale)

        # 创建雪天相关物体集合 并且将所有物体加入
        collection_name = "Snow Weather Collection"
        if collection_name not in bpy.data.collections:
            rain_weather_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(rain_weather_collection)
            print(f"集合 '{collection_name}' 已创建。")
        else:
            rain_weather_collection = bpy.data.collections[collection_name]
            print(f"集合 '{collection_name}' 已存在。")

        # 将对象移动到集合
        object_names = ["WI Snow Fall", "WI Snow Ground"]
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                # 从所有集合中移除
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                # 添加到目标集合
                rain_weather_collection.objects.link(obj)
                print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
            else:
                print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")

    ########################################### 主函数部分  ############################################
    def create_city_3D(self,startfile, exist_flag, vertices, edges, Texture_Road, Texture_Curb, Texture_Sidewalk, Tree,
                       Tree_Spacing, Light, Light_Spacing, Light_Energy, Light_color, Bollard, Bollard_Spacing, Bench,
                       Bench_Spacing, Services, Services_Spacing, Sign_Spacing, Road_Lanes_Width, Sidewalk_Width):
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
            # 创建边（去重）
            seen_edges = set()
            for edge in edges:
                key = (min(edge[0], edge[1]), max(edge[0], edge[1]))
                if key not in seen_edges:
                    seen_edges.add(key)
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
            script_dir = os.path.dirname(os.path.abspath(__file__))
            blend_path = os.path.join(script_dir, 'assets', filename)
            print(f"[load_start_template] 尝试加载: {blend_path}")
            if not os.path.exists(blend_path):
                raise FileNotFoundError(f"模板文件不存在: {blend_path}")

            # 使用 bpy.data.libraries.load（不依赖 UI 上下文）
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                if 'ICity' not in data_from.collections:
                    raise RuntimeError(
                        f"'ICity' 集合在 {filename} 中不存在，"
                        f"可用集合: {list(data_from.collections)[:10]}")
                data_to.collections = ['ICity']
                print(f"[load_start_template] libraries.load 完成")

            # 将 ICity 集合链接到场景
            icity = bpy.data.collections.get('ICity')
            if icity is None:
                raise RuntimeError("'ICity' 集合加载后未在 bpy.data.collections 中找到")
            bpy.context.scene.collection.children.link(icity)
            print(f"[load_start_template] ICity 集合已链接到场景")

            if 'ICity Assets' not in bpy.data.collections:
                raise RuntimeError("'ICity Assets' 集合未找到，请检查 .blend 文件完整性")
            bpy.data.collections['ICity Assets'].hide_viewport = True
            bpy.data.collections['ICity Assets'].hide_render = True

            if 'ICity Base' not in bpy.data.objects:
                raise RuntimeError("'ICity Base' 对象未找到，请检查 .blend 文件完整性")
            bpy.context.view_layer.objects.active = bpy.data.objects['ICity Base']
            bpy.data.objects['ICity Road'].hide_select = True
            bpy.data.objects['ICity Road Boundry'].hide_select = True
            bpy.data.objects['ICity Spces'].hide_select = True
            bpy.data.objects['ICity Procedural ground'].hide_select = True
            bpy.data.objects['ICity building procedural base'].hide_select = True
            bpy.data.objects['Procedural building_Default_ICity'].hide_select = True
        # 在设定好的文件中操作不需要start
        # bpy.ops.sna.start_5209e()
        load_start_template(startfile)
        bpy.ops.sna.edit_city_d7cab()



        #将自定义材质添加到ICity_Materials!!!
        custom_tex_name = "路面材质"
        if custom_tex_name in bpy.data.materials:
            mat = bpy.data.materials[custom_tex_name]
            target_obj = bpy.data.objects.get("ICity_Materials")
            if target_obj:
                existing_mats = [slot.material.name for slot in target_obj.material_slots if slot.material]
                if mat.name not in existing_mats:
                    target_obj.data.materials.append(mat)
                    print(f"已将材质 '{mat.name}' 挂载到 ICity_Materials")
                else:
                    print(f"材质 '{mat.name}' 已存在于 ICity_Materials 中")
            else:
                print("警告: 未找到 ICity_Materials 对象")
        else:
            print("警告: 自定义材质尚未导入，请检查导入逻辑")




        # 清除初始加载的内容 切记不能直接删除点 要调用函数 否则的话没办法在地块上生成城市
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.context.scene.sna_citystreet = 'Road'
        bpy.context.scene.sna_street_assetoptions = 'Options'
        bpy.ops.mesh.attribute_set(value_bool=True)
        bpy.ops.sna.remove_road_a2302()

        obj_name = "ICity Base"
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

        # 长椅
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
        if exist_flag[0] == 1:
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

        if exist_flag[1] == 1:
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
        
        # 刷新材质浏览器，让新材质出现在 UI 中
        bpy.ops.sna.material_filter_f04c3()
        bpy.ops.sna.road_materials_filter_6a3ec()


    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        # === 导入自定义资产 ===
        custom_assets_dir = os.path.join(os.path.dirname(__file__), "custom_assets")

        # 导入自定义路面材质 (2D资产)
        custom_tex_name = "路面材质"
        if custom_tex_name not in bpy.data.materials:
            custom_tex_path = os.path.join(custom_assets_dir, "myroad.blend")
            if os.path.exists(custom_tex_path):
                try:
                    with bpy.data.libraries.load(custom_tex_path, link=False) as (data_from, data_to):
                        if custom_tex_name in data_from.materials:
                            data_to.materials = [custom_tex_name]
                            print(f"[custom_asset] 已导入路面材质: {custom_tex_name}")
                        else:
                            print(f"[custom_asset] 文件中找不到材质 '{custom_tex_name}'，可用: {list(data_from.materials)[:10]}")
                except Exception as e:
                    print(f"[custom_asset] 导入路面材质失败: {e}")
            else:
                print(f"[custom_asset] 路面材质文件不存在: {custom_tex_path}")
        else:
            print(f"[custom_asset] 路面材质 '{custom_tex_name}' 已存在，跳过导入")

        # 导入自定义路灯 (3D资产)
        lamp_name = "路灯"
        if lamp_name not in bpy.data.objects:
            lamp_path = os.path.join(custom_assets_dir, "mylight.blend")
            if os.path.exists(lamp_path):
                try:
                    with bpy.data.libraries.load(lamp_path, link=False) as (data_from, data_to):
                        if lamp_name in data_from.objects:
                            data_to.objects = [lamp_name]
                            print(f"[custom_asset] 已导入路灯: {lamp_name}")
                        else:
                            print(f"[custom_asset] 文件中找不到物体 '{lamp_name}'，可用: {list(data_from.objects)[:20]}")
                except Exception as e:
                    print(f"[custom_asset] 导入路灯失败: {e}")
            else:
                print(f"[custom_asset] 路灯文件不存在: {lamp_path}")
        else:
            print(f"[custom_asset] 路灯 '{lamp_name}' 已存在，跳过导入")

        # 确保路灯在 ICity_Light 集合中（使其能在资产列表中被选中）
        lamp_obj = bpy.data.objects.get(lamp_name)
        if lamp_obj and "ICity_Light" in bpy.data.collections:
            light_coll = bpy.data.collections["ICity_Light"]
            if lamp_obj.name not in light_coll.all_objects:
                # 从其他集合中移除
                for coll in list(lamp_obj.users_collection):
                    coll.objects.unlink(lamp_obj)
                light_coll.objects.link(lamp_obj)
                print(f"[custom_asset] 已将路灯链接到 ICity_Light 集合")

        CityGenerator = self.CityGenerator(context.scene.sna_description)
        building_graph = CityGenerator.create_city_diagram()
        # building_graph = {'city_type': ['classical type']}
        # LLM 可能返回列表 ["classical type"] 或字符串 "classical type"，统一处理
        raw_city = building_graph['city_type']
        raw_weather = building_graph['weather']
        if isinstance(raw_city, list):
            city_type_raw = raw_city[0].strip().lower() if raw_city else ""
        else:
            city_type_raw = str(raw_city).strip().lower()
        if isinstance(raw_weather, list):
            weather_val = raw_weather[0].strip().lower() if raw_weather else "sunny"
        else:
            weather_val = str(raw_weather).strip().lower()

        print(f"城市类型是：{city_type_raw}")
        print(f"天气是：{weather_val}")
        bpy.context.scene.sna_weather = weather_val

        valid_city_types = ['classical type', 'ancient type', 'modern type', 'taiwanese type', 'industrial type']
        # LLM 可能返回 "classicaltype"（无空格），统一去除空格后比较
        city_type_normalized = city_type_raw.replace(' ', '')
        if any(vt.replace(' ', '') == city_type_normalized for vt in valid_city_types):
            try:

                vertices = [(-1, 5, 0), (1, 4, 0), (-4, 2, 0), (-2, 2, 0), (1, 2, 0), (2, 2, 0), (3, 2, 0), (-5, -2, 0),
                            (-3, -2, 0), (1, -2, 0), (3, -2, 0), (5, -2, 0), (1, -3, 0), (3, -4, 0), (-4, -5, 0),
                            (1, -5, 0)]
                edges = [(0, 3), (1, 4), (2, 3), (3, 4), (4, 5), (5, 6), (3, 8), (4, 9), (5, 10), (7, 8), (8, 9), (9, 10),
                         (10, 11), (8, 14), (9, 12), (12, 13), (12, 15)]
                mm = 10

                vertices = [(x * mm, y * mm, z * mm) for (x, y, z) in vertices]

                if context.scene.sna_road_type == '2':
                    vertices = [(-200, 200, 0), (-200, 50, 0), (-50, 50, 0), (-50, 100, 0), (-50, 200, 0), (200, 200, 0),
                                (200, 100, 0), (50, 100, 0), (50, -100, 0), (50, -200, 0), (200, -200, 0), (-200, -100, 0),
                                (-200, -200, 0)]
                    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (4, 5), (5, 6), (6, 7), (3, 7), (7, 8), (8, 9),
                             (9, 10),
                             (10, 6), (8, 11), (1, 11), (11, 12), (9, 12)]
                    nn = 1
                    vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]

                # 3类型是自定义图像路网类型
                if context.scene.sna_road_type == '3':
                    input_path=GLOBAL_IMAGE_PATH
                    main_layout = MainPathBuildings()
                    polygons_out, vertices, edges = main_layout.process(input_path)
                    nn = 0.45
                    vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]
                    print(vertices)
                    print(edges)

                # 手动布局模式：当手动字段有内容时使用
                manual_verts = parse_manual_vertices(context.scene.sna_manual_vertices)
                manual_edges_list = parse_manual_edges(context.scene.sna_manual_edges)
                if manual_verts and manual_edges_list:
                    vertices = manual_verts
                    edges = manual_edges_list
                    nn = 1
                    vertices = [(x * nn, y * nn, z * nn) for (x, y, z) in vertices]
                elif context.scene.sna_road_type == '4':
                    if not manual_verts:
                        raise ValueError(
                            "无法解析手动输入的顶点。格式：(x,y,z),(x,y,z),... 如 "
                            f"(0,0,0),(50,0,0),(50,50,0),(0,50,0)\n当前值: '{context.scene.sna_manual_vertices[:100]}'"
                        )
                    if not manual_edges_list:
                        raise ValueError(
                            "无法解析手动输入的边。格式：(i,j),(i,j),... 如 "
                            f"(0,1),(1,2),(2,3),(3,0)\n当前值: '{context.scene.sna_manual_edges[:100]}'"
                        )

                script_dir = os.path.dirname(os.path.abspath(__file__))
                car_blend = os.path.join(script_dir, "assets", "car.blend")
                print(f"[city_gen] 加载 car.blend: {car_blend}")
                with bpy.data.libraries.load(car_blend, link=False) as (data_from, data_to):
                    car_colls = list(data_from.collections)
                    print(f"[city_gen] car.blend 可用集合: {car_colls[:5]}")
                    if 'car_mesh' in data_from.collections:
                        data_to.collections = ['car_mesh']
                    elif car_colls:
                        # 尝试加载第一个集合
                        data_to.collections = [car_colls[0]]
                        print(f"[city_gen] 未找到 'car_mesh'，改为加载: {car_colls[0]}")
                    else:
                        print("[city_gen] car.blend 中没有任何集合！")
                print(f"[city_gen] car.blend 加载完成")

                # 创建汽车路径
                # 创建一个新的网格
                mesh = bpy.data.meshes.new(name="road")
                # 使用BMesh来创建顶点和边
                bm = bmesh.new()
                for v in vertices:
                    bm.verts.new(v)
                bm.verts.ensure_lookup_table()
                seen_edges = set()
                for e in edges:
                    key = (min(e[0], e[1]), max(e[0], e[1]))
                    if key not in seen_edges:
                        seen_edges.add(key)
                        bm.edges.new((bm.verts[e[0]], bm.verts[e[1]]))
                # 将BMesh数据写入网格
                bm.to_mesh(mesh)
                bm.free()
                # 创建一个新的对象并将其链接到场景中
                obj = bpy.data.objects.new("road", mesh)
                bpy.context.collection.objects.link(obj)
                # 选中并激活新创建的对象
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                print("对象 'road' 创建完成！")
                # 替换汽车路径
                bpy.data.node_groups["节点城市"].nodes["Object Info.001"].inputs[0].default_value = bpy.data.objects["road"]


                # filename = 'ICity start.blend'
                # filename = 'ICity start - GLASS.blend'
                # filename = 'ICity start - colorbuilding.blend'

                filename = "ICity start - generatorcity_building.blend"
                Texture_Road = 'ICity_Road 11 dirty_Default'
                Texture_Curb = 'ICity_Curb grey 2_Default'
                Texture_Sidewalk = 'ICity_Sidewalk 1_Default'
                # Tree = 'Tree12_Tree_ICity_Default'
                Tree = 'Tree1_Tree_ICity_Default'
                # Tree = 'Tree_pink'
                # if 'Tree_pink' in bpy.data.objects:
                #     Tree = 'Tree_pink'
                Tree_Spacing = 21
                Light = 'Light4_Light_ICity_Default'
                Light_Spacing = 21
                Light_Energy = 300
                Light_color = (1, 0.587094, 0.150187)
                Bollard = 'Bollard1_Bollard_Default_ICity'
                Bollard_Spacing = 0.501
                Bench = 'Bench1_Bench_ICity_Default'
                Bench_Spacing = 51
                Services = 'Services_Default'
                Services_Spacing = 21
                Sign_Spacing = 61
                Road_Lanes_Width = -1
                Sidewalk_Width = -1
                # 树木、路灯，长椅、周边设施、护栏、路标标志、路面落叶、路沿落叶、小垃圾、水洼存在标志,
                # 为1的时候代表需要删除
                exist_flag = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

                self.create_city_3D(filename, exist_flag, vertices, edges, Texture_Road, Texture_Curb, Texture_Sidewalk, Tree,
                               Tree_Spacing, Light, Light_Spacing, Light_Energy, Light_color, Bollard, Bollard_Spacing,
                               Bench, Bench_Spacing, Services, Services_Spacing, Sign_Spacing, Road_Lanes_Width,
                               Sidewalk_Width)

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.report({'ERROR'}, f'城市生成阶段出错: {str(e)}')
        else:
            print(f"[city_gen] 未知城市类型: '{city_type_raw}'，跳过城市生成")
            self.report({'WARNING'}, f"未知城市类型 '{city_type_raw}'，仅生成天气效果。支持的类型: {', '.join(valid_city_types)}")

        if weather_val == "rainy":
            # 闪电尺寸
            lighting_socket_2_value = 5.0
            # 闪电速率
            lighting_socket_3_value = 10.0
            # 闪电密度
            lighting_socket_4_value = 10.0
            # z轴的坐标
            lighting_loaction = (0, 0, 50)

            # 雨水速率
            rain_fall_socket_2_value = 3.0
            # 雨水长度
            rain_fall_socket_3_value = 11.0
            # 雨水密度
            rain_fall_socket_4_value = 14.0
            rain_fall_location = (0, 0, 60)
            rain_fall_scale = (100, 100, 100)

            clouds_loaction = (0, 0, 80)
            clouds_scale = (100, 100, 1)
            self.rain_weather(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,
                         rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value,
                         rain_fall_location, rain_fall_scale, clouds_loaction, clouds_scale)

        if weather_val == "snowy":
            # 雪天参数
            collection = "snow"
            snow_loaction = (-50, 0, 50)
            snow_scale = (0, 0, 0)
            snow_ground_loaction = (-50, 0, 6.2779)
            snow_ground_dimensions = (0, 0, 0)
            # snow_ground_dimensions = (120, 120, 2)
            density = 0.8  # 雪密度
            thickness = 0.5  # 雪厚度
            self.snow_weather(collection, snow_ground_loaction, snow_ground_dimensions, density, thickness, snow_loaction,snow_scale)



        # 第二个任务：生成城市周边生态化场景，并让湖面船只产生关键帧动画。
        scgs_clear_old_ecology()
        scgs_generate_ecology_scene()

        print(context.scene.sna_road_type)
        print(context.scene.sna_description)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)

class SNA_OT_City_Edit(bpy.types.Operator):
    bl_idname = "sna.city_edit"
    bl_label = "3D city editing"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

################################################## 城市生成提示词部分 ##################################################################################
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
                - Example3: If the description contains something like "Help me create a Taiwanese style city", you need to return: "Taiwanese type".
                - Return format: [city_type]
            2.weather:
                - weather is selected only from the following list: sunny, rainy, snowy.
                - Example1: If the description contains something like "Help me create a retro-style city for sunny", you need to return: "sunny"
                - Example2: If the description contains something like "Help me create a retro-style city for snowy", you need to return: "snowy"
                - Return format: [weather]


                Output: Provide the information in a valid JSON object. The values for city_type and weather MUST be arrays with exactly one string element. For example:
                {{"city_type": ["modern type"], "weather": ["sunny"]}}
                Do NOT return strings directly like "modern type" - always wrap in an array.
                """

            response_str = chat_completions_content(
                messages=[
                    {"role": "user", "content": context_msg},
                ],
                temperature=0.4,
                max_tokens=4096,
            )
            raw_response = response_str.replace("\n", "").strip()
            start = raw_response.find('{')
            end = raw_response.rfind('}')
            if start >= 0 and end > start:
                response = json.loads(raw_response[start:end + 1])
            else:
                raise ValueError(f"无法从LLM响应中提取JSON: {raw_response[:200]}")

            return response

        ################################################## 城市编辑提示词部分 ##################################################################################
    class FunctionGenerator:
        def __init__(self, description):
            self.description = description

        def create_function(self):
            # Generate a graph from description using GPT-4
            context_msg = f"""
            Task: You are a programmed 3D urban planner. Currently, there are some functions for building 3D cities. You need to select the functions that need to be executed in sequence based on the user's description {self.description} and the description of the functions' functions, and return the complete names of the functions that need to be executed in sequence in the form of a list.

            Requirements:
            1.function_list:
                - function_list is a list of executed functions. The list is sequential. Among them, the functions in front of the list need to be executed first, and the functions after the list need to be executed later. In the list of functions can choose from the following list: [create_city_3D (),change_snow_weather(),change_rain_weather(),change_sunny_weather()], The explanations of these functions are as follows:
                    change_snow_weather():change_snow_weather() is a function for controlling the weather. Its role is to adjust the weather of the current city to a snowy day.
                    change_rain_weather():change_rain_weather() is a function for controlling the weather. Its role is to adjust the current weather of the city to rainy.
                    change_sunny_weather():change_sunny_weather() is a function for controlling the weather. Its role is to clear all weather effects, remove rain and snow, and set the scene to sunny daytime.
                    turn_to_day():The role of the turn_to_day() function is to adjust the current scene to daytime. It is used when there is a statement similar to "adjust the scene to daytime" in {self.description}.
                    turn_to_night():The role of the turn_to_night() function is to adjust the current scene to night. It is used when there is a statement similar to "adjust the scene to night" in {self.description}.
                    make_road_clean():The function make_road_clean() is used to remove fallen leaves and small garbage from the road surface. It is called when there is a statement similar to "remove weeds and small garbage from the road surface" in {self.description}.
                    make_road_dirty():The function make_road_dirty() is used to add fallen leaves and small garbage on the road surface. It is called when there is a statement similar to "add weeds and small garbage on the road surface" in {self.description}.
                - Attention:
                    To simplify the output, each function is numbered. The correspondence between the function and the number is as follows:
                        ["change_snow_weather()" : "1",
                         "change_rain_weather()" : "2",
                         "change_sunny_weather()" : "7",
                         "turn_to_day()" : "3",
                         "turn_to_night()" : "4",
                         "make_road_clean()":5,
                         "make_road_dirty()": 6,]
                    therefore, If you determine that The function list should be [change_snow_weather()], the final output result should be [1]; If you determine that The function list should be [change_rain_weather()], the final output result should be [2]; If you determine that The function list should be [change_sunny_weather()], the final output result should be [7].
                    The function controlling the weather can only appear once, that is, the functions in the following list can only appear once: [1,2,7]
                    The total number of functions in the list is greater than or equal to 1, and the specific number depends on the situation.
                - Example1: If {self.description} is "Please change the weather to rainy days.", Then you the returned list is [2].
                - Example2: If {self.description} is "Please change the weather to snowy days.", Then you the returned list is [1].
                - Example2b: If {self.description} is "Please change the weather to sunny.", Then you the returned list is [7].
                - Example3: If {self.description} is "adjust the scene to daytime",Then you the returned list is [3].
                - Example4: If {self.description} is "adjust the scene to night",Then you the returned list is [4].
                - Example5: If {self.description} is "change the weather to rainy days and then adjust the scene to night",Then you the returned list is [2,4].
                - Example6: If {self.description} is "remove weeds and small garbage from the road surface.",Then you the returned list is [5].
                - Example7: If {self.description} is "add weeds and small garbage on the road surface.",Then you the returned list is [6].
                - Return format: [function1,function2,...]


                Output: Provide the information in a valid JSON structure with no spaces. I'll give you 100 bucks if you help me design a perfect scene and return it in the right format:
                {{
                    "function_list": [...]
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
            start = raw_response.find('{')
            end = raw_response.rfind('}')
            if start >= 0 and end > start:
                response = json.loads(raw_response[start:end + 1])
            else:
                raise ValueError(f"无法从LLM响应中提取JSON: {raw_response[:200]}")

            return response

############################################################白天黑夜#########################################################
    def turn_to_day(self):
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    def turn_to_night(self):
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.0748147, 0.0748147, 0.0748147, 1)

############################################################ 天气部分 ############################################################
    # 雨天综合函数
    def rain_weather(self,lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,
                     rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                     rain_fall_scale, clouds_loaction, clouds_scale):
        # 添加闪电
        def load_lighting(socket_2_value=5.0, socket_3_value=5.0, socket_4_value=2.0, loaction=(0, 0, 30)):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Lightning"
            object_name = "WI Lightning"

            # 检查文件是否存在
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
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
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
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Rain"
            object_name = "WI Rain Fall"

            # 检查文件是否存在
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
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
            obj.select_set(True)
            mod = obj.modifiers.get("WI Rain Fall")
            if mod is None:
                print("未找到 modifier: WI Rain Fall（无法设置 Socket 参数）。")
                return
            mod["Socket_2"] = socket_2_value
            mod["Socket_3"] = socket_3_value
            mod["Socket_4"] = socket_4_value

        def load_clouds(loaction=(0, 0, 30), scale=(1.0, 1.0, 1.0)):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "Collection 5"
            object_name = "Clouds"

            # 检查文件是否存在
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

        # 加载闪电
        load_lighting(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction)
        # 加载雨水下落
        load_rain_fall(rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value, rain_fall_location,
                       rain_fall_scale)
        # 加载云
        load_clouds(clouds_loaction, clouds_scale)

        # 创建雨天相关物体集合 并且将所有物体加入
        collection_name = "Rain Weather Collection"
        if collection_name not in bpy.data.collections:
            rain_weather_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(rain_weather_collection)
            print(f"集合 '{collection_name}' 已创建。")
        else:
            rain_weather_collection = bpy.data.collections[collection_name]
            print(f"集合 '{collection_name}' 已存在。")

        # 将对象移动到集合
        object_names = ["Clouds", "WI Lightning", "WI Rain Fall"]
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                # 从所有集合中移除
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                # 添加到目标集合
                rain_weather_collection.objects.link(obj)
                print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
            else:
                print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")



    def snow_weather(self,collection, snow_ground_loaction, snow_ground_dimensions, density, thickness, snow_loaction,
                     snow_scale):
        def load_snow_ground(collection_mesh, loaction=(0, 0, 6.2779), dimensions=(100, 100, 6.37), density=0.8,
                             thickness=0.8):
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Snow"
            object_name = "WI Snow Ground"

            # 检查文件是否存在
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
            # 设置为活动物体
            bpy.context.view_layer.objects.active = obj
            # 选择该物体
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
            # 指定文件路径
            blend_file_path = bpy.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "Weather It.blend"))

            # 指定集合名称和对象名称
            collection_name = "WI Snow"
            object_name = "WI Snow Fall"

            # 检查文件是否存在
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
            # 添加雪景的mesh移动到snow集合里面

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

        move_snow_ground()
        # load_snow_ground(collection, snow_ground_loaction, snow_ground_dimensions, density, thickness)
        snow_fall(snow_loaction, snow_scale)

        # 创建雪天相关物体集合 并且将所有物体加入
        collection_name = "Snow Weather Collection"
        if collection_name not in bpy.data.collections:
            rain_weather_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(rain_weather_collection)
            print(f"集合 '{collection_name}' 已创建。")
        else:
            rain_weather_collection = bpy.data.collections[collection_name]
            print(f"集合 '{collection_name}' 已存在。")

        # 将对象移动到集合
        object_names = ["WI Snow Fall", "WI Snow Ground"]
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                # 从所有集合中移除
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                # 添加到目标集合
                rain_weather_collection.objects.link(obj)
                print(f"对象 '{obj_name}' 已移动到集合 '{collection_name}'。")
            else:
                print(f"对象 '{obj_name}' 未找到，请确保其已存在于场景中。")

    def del_weather(self, collection_name):
        # 隐藏指定集合中的所有物体
        if collection_name in bpy.data.collections:
            # 获取集合
            collection = bpy.data.collections[collection_name]

            # 遍历集合中的所有对象并隐藏
            for obj in collection.objects:
                obj.hide_set(True)  # 隐藏对象
            print(f"集合 '{collection_name}' 中的所有物体已被隐藏。")
        else:
            print(f"集合 '{collection_name}' 不存在。")

    def show_weather_collection(self,collection_name):
        # 检查集合是否存在
        if collection_name in bpy.data.collections:
            # 获取集合
            collection = bpy.data.collections[collection_name]

            # 遍历集合中的所有对象并设置为可见
            for obj in collection.objects:
                # 设置对象在视图中可见
                obj.hide_set(False)  # 取消隐藏
                obj.hide_viewport = False  # 确保在视图中可见

                # 设置对象在渲染中可见
                obj.hide_render = False

            print(f"集合 '{collection_name}' 中的所有物体的可见性已打开。")
        else:
            print(f"集合 '{collection_name}' 不存在。")

    def change_snow_weather(self):
        self.del_weather("Rain Weather Collection")
        if "Snow Weather Collection" in bpy.data.collections:
            self.show_weather_collection("Snow Weather Collection")
        else:
            collection = "snow"
            snow_loaction = (-50, 0, 50)
            snow_scale = (0, 0, 0)
            snow_ground_loaction = (-50, 0, 6.2779)
            snow_ground_dimensions = (250, 150, 6.2770)
            density = 0.8  # 雪密度
            thickness = 0.5  # 雪厚度
            self.snow_weather(collection, snow_ground_loaction, snow_ground_dimensions, density, thickness, snow_loaction,
                              snow_scale)
            bpy.context.scene.sna_weather = "snowy"

    def change_rain_weather(self):
        self.del_weather("Snow Weather Collection")
        if "Rain Weather Collection" in bpy.data.collections:
            self.show_weather_collection("Rain Weather Collection")
        else:
            # 闪电尺寸
            lighting_socket_2_value = 5.0
            # 闪电速率
            lighting_socket_3_value = 10.0
            # 闪电密度
            lighting_socket_4_value = 10.0
            # z轴的坐标
            lighting_loaction = (0, 0, 50)

            # 雨水速率
            rain_fall_socket_2_value = 3.0
            # 雨水长度
            rain_fall_socket_3_value = 11.0
            # 雨水密度
            rain_fall_socket_4_value = 14.0
            rain_fall_location = (0, 0, 60)
            rain_fall_scale = (100, 100, 100)

            clouds_loaction = (0, 0, 80)
            clouds_scale = (100, 100, 1)
            self.rain_weather(lighting_socket_2_value, lighting_socket_3_value, lighting_socket_4_value, lighting_loaction,
                              rain_fall_socket_2_value, rain_fall_socket_3_value, rain_fall_socket_4_value,
                              rain_fall_location, rain_fall_scale, clouds_loaction, clouds_scale)
            bpy.context.scene.sna_weather = "rainy"

    def change_sunny_weather(self):
        """切换为晴天：隐藏所有天气效果"""
        self.del_weather("Rain Weather Collection")
        self.del_weather("Snow Weather Collection")
        self.turn_to_day()
        bpy.context.scene.sna_weather = "sunny"

    # 让路面变干净
    def make_road_clean(self):
        # 路边落叶间距
        bpy.data.node_groups["Road 2"].nodes["Group.012"].inputs[2].default_value = 10000
        #路沿落叶密度
        bpy.data.node_groups["Road 2"].nodes["Group.054"].inputs[2].default_value = 0
        bpy.data.node_groups["Road 2"].nodes["Value"].outputs[0].default_value = 0
        bpy.data.node_groups["Road 2"].nodes["Value.001"].outputs[0].default_value = 0
        # 水洼密度
        bpy.data.node_groups["Road 2"].nodes["Group"].inputs[2].default_value = 0
        # 路面裂缝密度
        bpy.data.node_groups["Road 2"].nodes["Group.013"].inputs[2].default_value = 0

    def make_road_dirty(self):
        bpy.data.node_groups["Road 2"].nodes["Group.012"].inputs[2].default_value = 2
        bpy.data.node_groups["Road 2"].nodes["Group.054"].inputs[2].default_value = 0.2
        bpy.data.node_groups["Road 2"].nodes["Value"].outputs[0].default_value = 10
        bpy.data.node_groups["Road 2"].nodes["Value.001"].outputs[0].default_value = 10
        bpy.data.node_groups["Road 2"].nodes["Group"].inputs[2].default_value = 0
        bpy.data.node_groups["Road 2"].nodes["Group.013"].inputs[2].default_value = 0


    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        # 执行函数
        Edit_Function = self.FunctionGenerator(context.scene.sna_edit)
        editfunction = Edit_Function.create_function()
        print(editfunction)
        # 提取键 'function_list' 对应的值（即列表）
        function_list = editfunction.get('function_list', [])

        # 使用循环遍历列表中的每个元素
        for value in function_list:
            print(value)
            if value == 1:
                self.change_snow_weather()
            elif value == 2:
                self.change_rain_weather()
            elif value == 3:
                self.turn_to_day()
            elif value == 4:
                self.turn_to_night()
            elif value == 5:
                self.make_road_clean()
            elif value == 6:
                self.make_road_dirty()
            elif value == 7:
                self.change_sunny_weather()

        # print(context.scene.sna_road_type)
        # print(context.scene.sna_description)
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


# Operator class definition (this would go in your operator definitions)
# 全局变量存储最终选择的图片路径
GLOBAL_IMAGE_PATH = ""
class SNA_OT_SelectImage(bpy.types.Operator):
    bl_idname = "sna.select_image"
    bl_label = "Select Image"
    bl_description = "Select an image from the plugin's img folder"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp",
        options={'HIDDEN'}
    )

    def execute(self, context):
        global GLOBAL_IMAGE_PATH

        # 获取用户最终选择的文件路径
        selected_file = self.filepath
        if not os.path.exists(selected_file):
            self.report({'ERROR'}, "File does not exist!")
            return {'CANCELLED'}

        # 存储到全局变量
        GLOBAL_IMAGE_PATH = selected_file
        print(f"Selected image: {GLOBAL_IMAGE_PATH}")

        return {'FINISHED'}

    def invoke(self, context, event):
        # 获取当前插件所在目录的 img 子目录
        script_dir = os.path.dirname(os.path.realpath(__file__))
        img_dir = os.path.join(script_dir, "img")

        # 如果目录不存在，则创建
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        # 设置文件选择窗口的默认目录（不预设文件名）
        self.filepath = img_dir

        # 打开文件选择窗口
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SNA_OT_ExtractLayout(bpy.types.Operator):
    """从所选图像提取道路布局并填入手动布局字段"""
    bl_idname = "sna.extract_layout"
    bl_label = "Extract Layout from Image"
    bl_description = "Run road detection on selected image and fill manual layout fields"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global GLOBAL_IMAGE_PATH
        if not GLOBAL_IMAGE_PATH or not os.path.exists(GLOBAL_IMAGE_PATH):
            self.report({'ERROR'}, "No image selected! Use 'Select Image' first.")
            return {'CANCELLED'}

        try:
            main_layout = MainPathBuildings(tolerance=30, merge_threshold=20.0, rdp_epsilon=2.0)
            _, vertices, edges = main_layout.process(GLOBAL_IMAGE_PATH)

            vert_text = ",".join(f"({v[0]:.1f},{v[1]:.1f},{v[2]:.1f})" for v in vertices)
            edge_text = ",".join(f"({e[0]},{e[1]})" for e in edges)

            context.scene.sna_manual_vertices = vert_text
            context.scene.sna_manual_edges = edge_text

            self.report({'INFO'}, f"Extracted {len(vertices)} vertices, {len(edges)} edges")
            return {'FINISHED'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Extraction failed: {str(e)}")
            return {'CANCELLED'}


class SNA_PT_ICITY_EDITOR_6D34D(bpy.types.Panel):
    bl_label = 'SCGS editor'
    bl_idname = 'SNA_PT_ICITY_EDITOR_6D34D'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = ''
    bl_category = 'SCGS'
    bl_order = 0
    bl_ui_units_x=0

    @classmethod
    def poll(cls, context):
        return not (False)

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        box_7C4E0 = layout.box()
        box_7C4E0.alert = False
        box_7C4E0.enabled = True
        box_7C4E0.active = True
        box_7C4E0.use_property_split = False
        box_7C4E0.use_property_decorate = False
        box_7C4E0.alignment = 'Expand'.upper()
        box_7C4E0.scale_x = 1.0
        box_7C4E0.scale_y = 1.0
        if not True: box_7C4E0.operator_context = "EXEC_DEFAULT"
        row_C774B = box_7C4E0.row(heading='', align=True)
        row_C774B.alert = False
        row_C774B.enabled = True
        row_C774B.active = True
        row_C774B.use_property_split = False
        row_C774B.use_property_decorate = False
        row_C774B.scale_x = 1.0
        row_C774B.scale_y = 1.0
        row_C774B.alignment = 'Center'.upper()
        row_C774B.operator_context = "INVOKE_DEFAULT" if False else "EXEC_DEFAULT"
        row_C774B.template_icon(icon_value=load_preview_icon(os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')), scale=(6 if property_exists("bpy.data.collections['ICity']", globals(), locals()) else 6))

        # 资产追加面板入口按钮
        append_btn = row_C774B.row(align=True)
        append_btn.alignment = 'RIGHT'
        append_btn.operator('sna.append_panel_lunch_221d5', text='+', emboss=True, depress=False)

        box_7C4E0.separator(factor=0.5)

        col_28D9D = box_7C4E0.row(heading='', align=False)
        col_28D9D.alert = False
        col_28D9D.enabled = True
        col_28D9D.active = True
        col_28D9D.use_property_split = False
        col_28D9D.use_property_decorate = False
        col_28D9D.scale_x = 1.0
        col_28D9D.scale_y = 1.0
        col_28D9D.alignment = 'Expand'.upper()
        col_28D9D.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        col_28D9D.alignment = 'CENTER'  # 设置行的对齐方式为居中
        col_28D9D.label(text="***  Road Type  ***")

        col_28D9C = box_7C4E0.row(heading='', align=False)
        col_28D9C.alert = False
        col_28D9C.enabled = True
        col_28D9C.active = True
        col_28D9C.use_property_split = False
        col_28D9C.use_property_decorate = False
        col_28D9C.scale_x = 1.0
        col_28D9C.scale_y = 1.0
        col_28D9C.alignment = 'Expand'.upper()
        col_28D9C.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        col_28D9C.prop(context.scene, "sna_road_type",text="")

        Description = box_7C4E0.row(heading='', align=False)
        Description.alert = False
        Description.enabled = True
        Description.active = True
        Description.use_property_split = False
        Description.use_property_decorate = False
        Description.scale_x = 1.0
        Description.scale_y = 1.0
        Description.alignment = 'Expand'.upper()
        Description.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        Description.alignment = 'CENTER'  # 设置行的对齐方式为居中
        Description.label(text="***  Description  ***")

        Description1 = box_7C4E0.row(heading='', align=False)
        Description1.alert = False
        Description1.enabled = True
        Description1.active = True
        Description1.use_property_split = False
        Description1.use_property_decorate = False
        Description1.scale_x = 2.0
        Description1.scale_y = 2.0
        Description1.alignment = 'Expand'.upper()
        Description1.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        Description1.prop(context.scene, "sna_description", text="")

        # 手动布局输入区
        manual_box = box_7C4E0.box()
        manual_box_1 = manual_box.row()
        manual_box_1.alignment = 'CENTER'
        manual_box_1.label(text="***  Manual Layout  ***")

        vert_row = manual_box.row()
        vert_row.scale_y = 1.5
        vert_row.prop(context.scene, "sna_manual_vertices", text="Vertices")

        edge_row = manual_box.row()
        edge_row.scale_y = 1.5
        edge_row.prop(context.scene, "sna_manual_edges", text="Edges")

        img_tools = manual_box.row(align=True)
        img_tools.operator('sna.select_image', text='Select Image', icon='IMAGE')
        img_tools.operator('sna.extract_layout', text='Extract', icon='IMPORT')

        IMG_PREVIEW = manual_box.row()
        IMG_PREVIEW.alignment = 'CENTER'
        if GLOBAL_IMAGE_PATH and os.path.exists(GLOBAL_IMAGE_PATH):
            IMG_PREVIEW.template_icon(icon_value=load_preview_icon(GLOBAL_IMAGE_PATH), scale=6)
        else:
            IMG_PREVIEW.label(text="No RoadMap Selected", icon='IMAGE_DATA')

        box_6BBDC = box_7C4E0.box()
        box_6BBDC.alert = False
        box_6BBDC.enabled = True
        box_6BBDC.active = True
        box_6BBDC.use_property_split = False
        box_6BBDC.use_property_decorate = False
        box_6BBDC.alignment = 'Expand'.upper()
        box_6BBDC.scale_x = 2.559999942779541
        box_6BBDC.scale_y = 2.259999990463257
        if not True: box_6BBDC.operator_context = "EXEC_DEFAULT"

        # 创建按钮，不设置 depress=True
        op = box_6BBDC.operator('sna.city_generation', text='Generate City', icon_value=0, emboss=True, depress=False)

        Editing = box_7C4E0.row(heading='', align=False)
        Editing.alert = False
        Editing.enabled = True
        Editing.active = True
        Editing.use_property_split = False
        Editing.use_property_decorate = False
        Editing.scale_x = 1.0
        Editing.scale_y = 1.0
        Editing.alignment = 'Expand'.upper()
        Editing.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        Editing.alignment = 'CENTER'  # 设置行的对齐方式为居中
        Editing.label(text="***  Edit  ***")

        Editing1 = box_7C4E0.row(heading='', align=False)
        Editing1.alert = False
        Editing1.enabled = True
        Editing1.active = True
        Editing1.use_property_split = False
        Editing1.use_property_decorate = False
        Editing1.scale_x = 2.0
        Editing1.scale_y = 2.0
        Editing1.alignment = 'Expand'.upper()
        Editing1.operator_context = "INVOKE_DEFAULT" if True else "EXEC_DEFAULT"
        # 要改
        Editing1.prop(context.scene, "sna_edit", text="")

        edit_start = box_7C4E0.box()
        edit_start.alert = False
        edit_start.enabled = True
        edit_start.active = True
        edit_start.use_property_split = False
        edit_start.use_property_decorate = False
        edit_start.alignment = 'Expand'.upper()
        edit_start.scale_x = 2.559999942779541
        edit_start.scale_y = 2.259999990463257
        if not True: edit_start.operator_context = "EXEC_DEFAULT"
        # 要改
        op = edit_start.operator('sna.city_edit', text='Edit City', icon_value=0, emboss=True, depress=False)
        
        # 添加模板配置区块
        template_box = box_7C4E0.box()
        template_box.alert = False
        template_box.enabled = True
        template_box.active = True
        template_box.use_property_split = False
        template_box.use_property_decorate = False
        template_box.alignment = 'Expand'.upper()
        
        # 模板标题
        template_label = template_box.row()
        template_label.label(text="场景模板配置")
        
        # 模板选择行
        template_row = template_box.row()
        template_row.prop(context.scene, "sna_template_selection", text="模板选择")
        template_row.operator('sna.apply_template', text="应用模板", icon_value=0)
        
        # AI指令区块
        ai_box = box_7C4E0.box()
        ai_box.alert = False
        ai_box.enabled = True
        ai_box.active = True
        ai_box.use_property_split = False
        ai_box.use_property_decorate = False
        ai_box.alignment = 'Expand'.upper()
        
        # AI指令标题
        ai_label = ai_box.row()
        ai_label.label(text="AI自然语言指令")
        
        # AI指令输入行
        ai_row = ai_box.row()
        ai_row.prop(context.scene, "sna_ai_instruction", text="指令")
        ai_row.operator('sna.process_ai_instruction', text="执行", icon_value=0)
        
        # AI说明信息
        ai_info = ai_box.row()
        ai_info.label(text="示例: 树木1, 道路2, 座椅1 或选择模板 0-4")





def register():
    global _icons
    _icons = bpy.utils.previews.new()
    bpy.types.Scene.sna_citystreet = bpy.props.EnumProperty(name='city-street', description='', items=[('City', 'City', '', 0, 0), ('Road', 'Road', '', 0, 1)])
    bpy.types.Scene.sna_citystreet_append = bpy.props.EnumProperty(name='city-street append', description='', items=[('City', 'City', '', 0, 0), ('Road', 'Road', '', 0, 1)])
    bpy.types.Scene.sna_city_space_type_append = bpy.props.EnumProperty(name='City space type append', description='', items=[('Procedural', 'Procedural', '', 0, 0), ('Park', 'Park', '', 0, 1), ('Presets', 'Presets', '', 0, 2)], update=sna_update_sna_city_space_type_append_A7B1C)
    bpy.types.Scene.sna_street_asset_type_append = bpy.props.EnumProperty(name='street asset type append', description='', items=[('Light', 'Light', '', 0, 0), ('Bench', 'Bench', '', 0, 1), ('Tree', 'Tree', '', 0, 2), ('Services', 'Services', '', 0, 3), ('Bollard', 'Bollard', '', 0, 4), ('Traffic light', 'Traffic light', '', 0, 5), ('Cars', 'Cars', '', 0, 6), ('Sign', 'Sign', '', 0, 7), ('Texture', 'Texture', '', 0, 8), ('Imperfection', 'Imperfection', '', 0, 9)], update=sna_update_sna_street_asset_type_append)
    bpy.types.Scene.sna_street_assetoptions = bpy.props.EnumProperty(name='street asset-options', description='', items=[('Assets', 'Assets', '', 0, 0), ('Options', 'Options', '', 0, 1)])
    bpy.types.Scene.sna_street_asset_type = bpy.props.EnumProperty(name='street asset type', description='', items=[('Light', 'Light', '', 0, 0), ('Bench', 'Bench', '', 0, 1), ('Tree', 'Tree', '', 0, 2), ('Services', 'Services', '', 0, 3), ('Bollard', 'Bollard', '', 0, 4), ('Traffic light', 'Traffic light', '', 0, 5), ('Cars', 'Cars', '', 0, 6), ('Sign', 'Sign', '', 0, 7), ('Texture', 'Texture', '', 0, 8), ('Imperfection', 'Imperfection', '', 0, 9)], update=sna_update_sna_street_asset_type_BF136)
    bpy.types.Scene.sna_landscape_browser_append = bpy.props.EnumProperty(name='Landscape browser append', description='', items=sna_landscape_browser_append_enum_items)
    bpy.types.Scene.sna_street_asset_browser = bpy.props.EnumProperty(name='Street asset browser', description='', items=sna_street_asset_browser_enum_items)
    bpy.types.Scene.sna_procedural_building_browser = bpy.props.EnumProperty(name='Procedural building browser', description='', items=sna_procedural_building_browser_enum_items)
    bpy.types.Scene.sna_city_space_type = bpy.props.EnumProperty(name='City space type', description='', items=[('Procedural', 'Procedural', '', 0, 0), ('Park', 'Park', '', 0, 1), ('Presets', 'Presets', '', 0, 2)], update=sna_update_sna_city_space_type)
    bpy.types.Scene.sna_city_building_presets_type = bpy.props.EnumProperty(name='City building presets type', description='', items=[('Skyscrapper', 'Skyscrapper', '', 0, 0), ('Court', 'Court', '', 0, 1), ('Market', 'Market', '', 0, 2), ('Fire station', 'Fire station', '', 0, 3), ('Police station', 'Police station', '', 0, 4), ('Hospital', 'Hospital', '', 0, 5)], update=sna_update_sna_city_building_presets_type_FB155)
    bpy.types.Scene.sna_city_building_presets_type_append = bpy.props.EnumProperty(name='City building presets type append', description='', items=[('Skyscrapper', 'Skyscrapper', '', 0, 0), ('Court', 'Court', '', 0, 1), ('Market', 'Market', '', 0, 2), ('Fire station', 'Fire station', '', 0, 3), ('Police station', 'Police station', '', 0, 4), ('Hospital', 'Hospital', '', 0, 5)], update=sna_update_sna_city_building_presets_type_append_A77BA)
    bpy.types.Scene.sna_road_materials_type_append = bpy.props.EnumProperty(name='Road materials type append', description='', items=[('Road', 'Road', '', 0, 0), ('Curb', 'Curb', '', 0, 1), ('Sidewalk', 'Sidewalk', '', 0, 2)], update=sna_update_sna_road_materials_type_append_CB7F1)
    bpy.types.Scene.sna_building_presets_browser = bpy.props.EnumProperty(name='Building presets browser', description='', items=sna_building_presets_browser_enum_items)
    bpy.types.Scene.sna_style = bpy.props.EnumProperty(name='Style', description='', items=[('All', 'All', '', 0, 0), ('General', 'General', '', 0, 1), ('Chicago', 'Chicago', '', 0, 2)])
    bpy.types.Scene.sna_park_browser = bpy.props.EnumProperty(name='Park browser', description='', items=sna_park_browser_enum_items)
    bpy.types.Scene.sna_sidewalk_mat = bpy.props.EnumProperty(name='Sidewalk mat', description='', items=sna_sidewalk_mat_enum_items)
    bpy.types.Scene.sna_sidewalk_curb_mat = bpy.props.EnumProperty(name='Sidewalk Curb mat', description='', items=sna_sidewalk_curb_mat_enum_items)
    bpy.types.Scene.sna_landscape_browser = bpy.props.EnumProperty(name='Landscape browser', description='', items=sna_landscape_browser_enum_items)
    bpy.types.Scene.sna_theme = bpy.props.EnumProperty(name='THEME', description='', items=sna_theme_enum_items, options={'ENUM_FLAG'}, update=sna_update_sna_theme_88C83)
    bpy.types.Scene.sna_append_browser = bpy.props.EnumProperty(name='Append browser', description='', items=sna_append_browser_enum_items)
    bpy.types.Scene.sna_test = bpy.props.EnumProperty(name='Test', description='', items=sna_test_enum_items)
    bpy.types.Scene.sna_city_browser_append = bpy.props.EnumProperty(name='City browser append', description='', items=sna_city_browser_append_enum_items)
    bpy.types.Scene.sna_road_browser_append = bpy.props.EnumProperty(name='Road browser append', description='', items=sna_road_browser_append_enum_items)
    bpy.types.Scene.sna_assets_folder_path = bpy.props.StringProperty(name='Assets folder path', description='', default='', subtype='FILE_PATH', maxlen=0)
    bpy.types.Object.sna_asset_category_path_object = bpy.props.StringProperty(name='Asset category path object', description='', default='', subtype='NONE', maxlen=0)
    bpy.types.Collection.sna_asset_category_path_collection = bpy.props.StringProperty(name='Asset category path collection', description='', default='', subtype='FILE_PATH', maxlen=0)
    bpy.types.Material.sna_asset_category_path_material = bpy.props.StringProperty(name='Asset category path material', description='', default='', subtype='FILE_PATH', maxlen=0)
    bpy.types.Scene.sna_road_materials_browser = bpy.props.EnumProperty(name='Road materials browser', description='', items=sna_road_materials_browser_enum_items)
    bpy.types.Scene.sna_road_materials_browser_append = bpy.props.EnumProperty(name='Road materials browser append', description='', items=sna_road_materials_browser_append_enum_items)
    bpy.types.Scene.sna_road_materials_type_ = bpy.props.EnumProperty(name='Road materials type ', description='', items=[('Road', 'Road', '', 0, 0), ('Curb', 'Curb', '', 0, 1), ('Sidewalk', 'Sidewalk', '', 0, 2)], update=sna_update_sna_road_materials_type__75061)
    bpy.types.Scene.sna_light_mode = bpy.props.BoolProperty(name='Light mode', description='', default=False)
    bpy.types.Scene.sna_proxy_mode = bpy.props.BoolProperty(name='Proxy mode', description='', default=False, update=sna_update_sna_proxy_mode_0EBCB)
    bpy.types.Scene.sna_road_type = bpy.props.StringProperty(default="2")
    bpy.types.Scene.sna_description = bpy.props.StringProperty(default="Please help me generate a classic city on a rainy day!")
    bpy.types.Scene.sna_edit = bpy.props.StringProperty(default="Please change the weather to sunny.")
    bpy.types.Scene.sna_weather = bpy.props.StringProperty(default="")
    bpy.types.Scene.sna_template_selection = bpy.props.StringProperty(
        name="模板选择",
        description="输入模板编号(0-4)或模板名称以应用预定义配置",
        default="0"
    )
    bpy.types.Scene.sna_ai_instruction = bpy.props.StringProperty(
        name="AI指令",
        description="输入自然语言指令，系统会自动解析并配置场景参数",
        default=""
    )
    bpy.types.Scene.sna_manual_vertices = bpy.props.StringProperty(
        name="Manual Vertices",
        description="手动道路顶点，格式：(x,y,z),(x,y,z),...",
        default=""
    )
    bpy.types.Scene.sna_manual_edges = bpy.props.StringProperty(
        name="Manual Edges",
        description="手动道路边，格式：(i,j),(i,j),...",
        default=""
    )
    bpy.utils.register_class(SNA_OT_City_Edit)
    bpy.utils.register_class(SNA_OT_SelectImage)
    bpy.utils.register_class(SNA_OT_ExtractLayout)
    bpy.utils.register_class(SNA_OT_Store_All_Assets_5B09E)
    bpy.utils.register_class(SNA_OT_Refresh_Theme_443Bd)
    bpy.utils.register_class(SNA_OT_Refresh_C6Cb8)
    bpy.utils.register_class(SNA_OT_Read_97C87)
    bpy.utils.register_class(SNA_OT_Filter_City_Assets_Ea982)
    bpy.utils.register_class(SNA_OT_Filter_Road_Bc600)
    bpy.utils.register_class(SNA_OT_Filter_Theme_31D4C)
    bpy.utils.register_class(SNA_OT_Apply_Template)
    bpy.utils.register_class(SNA_OT_Process_AI_Instruction)
    bpy.utils.register_class(SNA_MT_89AD5)
    bpy.utils.register_class(SNA_MT_8CD9F)
    bpy.utils.register_class(SNA_MT_0BED6)
    bpy.utils.register_class(SNA_OT_Append_Panel_Lunch_221D5)
    bpy.utils.register_class(SNA_PT_APPEND_PANEL_590A1)
    bpy.utils.register_class(SNA_OT_Open_Addon_Prefrences_34Afe)
    bpy.utils.register_class(SNA_OT_Hide_Park_R_192D6)
    bpy.utils.register_class(SNA_OT_Grass_R_E07D4)
    bpy.utils.register_class(SNA_OT_Grass_V_4Cdd7)
    bpy.utils.register_class(SNA_OT_Trees_R_164C2)
    bpy.utils.register_class(SNA_OT_Trees_V_25C59)
    bpy.utils.register_class(SNA_OT_Hide_Park_3Ea8F)
    # bpy.utils.register_class(SNA_PT_ICITY_754AD)
    bpy.utils.register_class(SNA_OT_Material_Filter_F04C3)
    bpy.utils.register_class(SNA_OT_Road_Materials_Filter_6A3Ec)
    bpy.utils.register_class(SNA_OT_Start_5209E)
    bpy.utils.register_class(SNA_OT_City_Apply_Dae66)
    bpy.app.handlers.depsgraph_update_pre.append(depsgraph_update_pre_handler_361D3)
    bpy.utils.register_class(SNA_OT_Road_Apply_5C3Ab)
    bpy.utils.register_class(SNA_OT_Sync_City_76707)
    bpy.utils.register_class(SNA_OT_Floor_Count_Min_C2Cf8)
    bpy.utils.register_class(SNA_OT_Floor_Count_Max_Db555)
    bpy.utils.register_class(SNA_OT_Offset_X_A87Eb)
    bpy.utils.register_class(SNA_OT_Offset_Y_45B11)
    bpy.utils.register_class(SNA_OT_Rotation_Z_4Edcd)
    bpy.utils.register_class(SNA_OT_Offset_X_Preset_5A427)
    bpy.utils.register_class(SNA_OT_Offset_Y_Preset_Dcad4)
    bpy.utils.register_class(SNA_OT_Rotation_Z_Preset_60648)
    bpy.app.handlers.depsgraph_update_pre.append(depsgraph_update_pre_handler_59166)
    bpy.utils.register_class(SNA_OT_Set_Side_Count_49527)
    bpy.utils.register_class(SNA_OT_Assign_Road_Deef9)
    bpy.utils.register_class(SNA_OT_Remove_Road_A2302)
    bpy.utils.register_class(SNA_OT_Road_Lanes_Width_93562)
    bpy.utils.register_class(SNA_OT_Sidewalk_Width_99Dc0)
    bpy.utils.register_class(SNA_OT_Crosswalk_Offset_B1E82)
    bpy.utils.register_class(SNA_OT_Append_Assets_Ffd74)
    bpy.utils.register_class(SNA_OT_Append_Landscape_C97Bb)
    bpy.utils.register_class(SNA_OT_Intersection_Offset_16E01)
    bpy.utils.register_class(SNA_OT_Edit_City_D7Cab)
    bpy.utils.register_class(SNA_OT_Delete_From_Scene_City_324Ff)
    bpy.utils.register_class(SNA_OT_Light_City_20Ca9)
    bpy.utils.register_class(SNA_OT_Delete_From_Scene_7C7D8)
    bpy.utils.register_class(SNA_OT_Road_Remove_Aa51D)
    bpy.utils.register_class(SNA_AddonPreferences_7CCE1)
    bpy.utils.register_class(SNA_OT_Test_Assets_B9626)
    bpy.utils.register_class(SNA_OT_Refresh_Edit_F156A)
    bpy.utils.register_class(SNA_OT_Filter_Presets_Fb5A4)
    bpy.utils.register_class(SNA_OT_Procedural_Building_Filter_05Bed)
    bpy.utils.register_class(SNA_OT_Park_Filter_5A7A2)
    bpy.utils.register_class(SNA_OT_Landscape_Filter_0Bf89)
    bpy.utils.register_class(SNA_OT_Filter_Street_Assets_C5C0E)
    bpy.utils.register_class(SNA_PT_ICITY_EDITOR_6D34D)
    bpy.utils.register_class(SNA_OT_City_Generation)
    bpy.utils.register_class(SNA_OT_Generate_Ecology_9F2A1)
    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.new(name='Window', space_type='EMPTY')
    kmi = km.keymap_items.new('sna.open_addon_prefrences_34afe', 'M', 'PRESS',
        ctrl=False, alt=False, shift=True, repeat=False)
    addon_keymaps['0285F'] = (km, kmi)


def unregister():
    global _icons
    bpy.utils.previews.remove(_icons)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    for km, kmi in addon_keymaps.values():
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    del bpy.types.Scene.sna_proxy_mode
    del bpy.types.Scene.sna_road_type
    del bpy.types.Scene.sna_description
    del bpy.types.Scene.sna_edit
    del bpy.types.Scene.sna_weather
    del bpy.types.Scene.sna_template_selection
    del bpy.types.Scene.sna_ai_instruction
    del bpy.types.Scene.sna_manual_vertices
    del bpy.types.Scene.sna_manual_edges
    del bpy.types.Scene.sna_light_mode
    del bpy.types.Scene.sna_road_materials_type_
    del bpy.types.Scene.sna_road_materials_browser_append
    del bpy.types.Scene.sna_road_materials_browser
    del bpy.types.Material.sna_asset_category_path_material
    del bpy.types.Collection.sna_asset_category_path_collection
    del bpy.types.Object.sna_asset_category_path_object
    del bpy.types.Scene.sna_assets_folder_path
    del bpy.types.Scene.sna_road_browser_append
    del bpy.types.Scene.sna_city_browser_append
    del bpy.types.Scene.sna_test
    del bpy.types.Scene.sna_append_browser
    del bpy.types.Scene.sna_theme
    del bpy.types.Scene.sna_landscape_browser
    del bpy.types.Scene.sna_sidewalk_curb_mat
    del bpy.types.Scene.sna_sidewalk_mat
    del bpy.types.Scene.sna_park_browser
    del bpy.types.Scene.sna_style
    del bpy.types.Scene.sna_building_presets_browser
    del bpy.types.Scene.sna_road_materials_type_append
    del bpy.types.Scene.sna_city_building_presets_type_append
    del bpy.types.Scene.sna_city_building_presets_type
    del bpy.types.Scene.sna_city_space_type
    del bpy.types.Scene.sna_procedural_building_browser
    del bpy.types.Scene.sna_street_asset_browser
    del bpy.types.Scene.sna_landscape_browser_append
    del bpy.types.Scene.sna_street_asset_type
    del bpy.types.Scene.sna_street_assetoptions
    del bpy.types.Scene.sna_street_asset_type_append
    del bpy.types.Scene.sna_city_space_type_append
    del bpy.types.Scene.sna_citystreet_append
    del bpy.types.Scene.sna_citystreet
    bpy.utils.unregister_class(SNA_OT_City_Edit)
    bpy.utils.unregister_class(SNA_OT_SelectImage)
    bpy.utils.unregister_class(SNA_OT_ExtractLayout)
    bpy.utils.unregister_class(SNA_OT_Store_All_Assets_5B09E)
    bpy.utils.unregister_class(SNA_OT_Refresh_Theme_443Bd)
    bpy.utils.unregister_class(SNA_OT_Refresh_C6Cb8)
    bpy.utils.unregister_class(SNA_OT_Read_97C87)
    bpy.utils.unregister_class(SNA_OT_Filter_City_Assets_Ea982)
    bpy.utils.unregister_class(SNA_OT_Filter_Road_Bc600)
    bpy.utils.unregister_class(SNA_OT_Filter_Theme_31D4C)
    bpy.utils.unregister_class(SNA_OT_Apply_Template)
    bpy.utils.unregister_class(SNA_OT_Process_AI_Instruction)
    bpy.utils.unregister_class(SNA_MT_89AD5)
    bpy.utils.unregister_class(SNA_MT_8CD9F)
    bpy.utils.unregister_class(SNA_MT_0BED6)
    bpy.utils.unregister_class(SNA_OT_Append_Panel_Lunch_221D5)
    bpy.utils.unregister_class(SNA_PT_APPEND_PANEL_590A1)
    bpy.utils.unregister_class(SNA_OT_Open_Addon_Prefrences_34Afe)
    bpy.utils.unregister_class(SNA_OT_Hide_Park_R_192D6)
    bpy.utils.unregister_class(SNA_OT_Grass_R_E07D4)
    bpy.utils.unregister_class(SNA_OT_Grass_V_4Cdd7)
    bpy.utils.unregister_class(SNA_OT_Trees_R_164C2)
    bpy.utils.unregister_class(SNA_OT_Trees_V_25C59)
    bpy.utils.unregister_class(SNA_OT_Hide_Park_3Ea8F)
    # bpy.utils.unregister_class(SNA_PT_ICITY_754AD)
    bpy.utils.unregister_class(SNA_OT_Material_Filter_F04C3)
    bpy.utils.unregister_class(SNA_OT_Road_Materials_Filter_6A3Ec)
    bpy.utils.unregister_class(SNA_OT_Start_5209E)
    bpy.utils.unregister_class(SNA_OT_City_Apply_Dae66)
    bpy.app.handlers.depsgraph_update_pre.remove(depsgraph_update_pre_handler_361D3)
    bpy.utils.unregister_class(SNA_OT_Road_Apply_5C3Ab)
    bpy.utils.unregister_class(SNA_OT_Sync_City_76707)
    bpy.utils.unregister_class(SNA_OT_Floor_Count_Min_C2Cf8)
    bpy.utils.unregister_class(SNA_OT_Floor_Count_Max_Db555)
    bpy.utils.unregister_class(SNA_OT_Offset_X_A87Eb)
    bpy.utils.unregister_class(SNA_OT_Offset_Y_45B11)
    bpy.utils.unregister_class(SNA_OT_Rotation_Z_4Edcd)
    bpy.utils.unregister_class(SNA_OT_Offset_X_Preset_5A427)
    bpy.utils.unregister_class(SNA_OT_Offset_Y_Preset_Dcad4)
    bpy.utils.unregister_class(SNA_OT_Rotation_Z_Preset_60648)
    bpy.app.handlers.depsgraph_update_pre.remove(depsgraph_update_pre_handler_59166)
    bpy.utils.unregister_class(SNA_OT_Set_Side_Count_49527)
    bpy.utils.unregister_class(SNA_OT_Assign_Road_Deef9)
    bpy.utils.unregister_class(SNA_OT_Remove_Road_A2302)
    bpy.utils.unregister_class(SNA_OT_Road_Lanes_Width_93562)
    bpy.utils.unregister_class(SNA_OT_Sidewalk_Width_99Dc0)
    bpy.utils.unregister_class(SNA_OT_Crosswalk_Offset_B1E82)
    bpy.utils.unregister_class(SNA_OT_Append_Assets_Ffd74)
    bpy.utils.unregister_class(SNA_OT_Append_Landscape_C97Bb)
    bpy.utils.unregister_class(SNA_OT_Intersection_Offset_16E01)
    bpy.utils.unregister_class(SNA_OT_Edit_City_D7Cab)
    bpy.utils.unregister_class(SNA_OT_Delete_From_Scene_City_324Ff)
    bpy.utils.unregister_class(SNA_OT_Light_City_20Ca9)
    bpy.utils.unregister_class(SNA_OT_Delete_From_Scene_7C7D8)
    bpy.utils.unregister_class(SNA_OT_Road_Remove_Aa51D)
    bpy.utils.unregister_class(SNA_AddonPreferences_7CCE1)
    bpy.utils.unregister_class(SNA_OT_Test_Assets_B9626)
    bpy.utils.unregister_class(SNA_OT_Refresh_Edit_F156A)
    bpy.utils.unregister_class(SNA_OT_Filter_Presets_Fb5A4)
    bpy.utils.unregister_class(SNA_OT_Procedural_Building_Filter_05Bed)
    bpy.utils.unregister_class(SNA_OT_Park_Filter_5A7A2)
    bpy.utils.unregister_class(SNA_OT_Landscape_Filter_0Bf89)
    bpy.utils.unregister_class(SNA_OT_Filter_Street_Assets_C5C0E)
    bpy.utils.unregister_class(SNA_PT_ICITY_EDITOR_6D34D)
    bpy.utils.unregister_class(SNA_OT_Generate_Ecology_9F2A1)
    bpy.utils.unregister_class(SNA_OT_City_Generation)




