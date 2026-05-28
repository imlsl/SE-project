from PIL import Image
from sklearn.cluster import KMeans
from skimage.measure import label, regionprops
import cv2
import numpy as np
from skimage.morphology import skeletonize
import sknw
import networkx as nx
from scipy.spatial import cKDTree



def detect_dominant_colors(image_path, num_colors=2, white_threshold=240):
    """ 检测图像中排除白色后的主色调 """
    img = Image.open(image_path).convert('RGBA')

    # 收集非透明+非白色的有效像素
    pixels = []
    for pixel in img.getdata():
        r, g, b, a = pixel
        # 过滤条件：透明像素或接近白色的像素
        if a == 0 or (r >= white_threshold and g >= white_threshold and b >= white_threshold):
            continue
        pixels.append(pixel[:3])

    # 有效性检查
    if len(pixels) < num_colors:
        raise ValueError(f"错误：有效像素不足{num_colors}种颜色")

    # K-means聚类
    kmeans = KMeans(n_clusters=num_colors, random_state=0)
    kmeans.fit(pixels)

    # 获取颜色并排序（降序）
    colors = [tuple(map(int, c)) for c in kmeans.cluster_centers_]
    colors.sort(key=lambda c: sum(c), reverse=True)

    return colors


def create_color_mask(image, target_color, tolerance=30):
    """ 生成指定颜色的透明遮罩图像 """
    img = image.convert('RGBA')
    new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    pixels = img.load()
    new_pixels = new_img.load()

    # 颜色比较函数
    is_target = lambda p: all(
        abs(p[i] - target_color[i]) <= tolerance
        for i in range(3)
    )

    for x in range(img.width):
        for y in range(img.height):
            r, g, b, a = pixels[x, y]
            # 自动保留全透明区域
            if a == 0:
                continue
            # 白色背景过滤（二次验证）
            if (r >= 240 and g >= 240 and b >= 240):
                new_pixels[x, y] = (0, 0, 0, 0)
                continue
            # 颜色匹配
            if is_target((r, g, b)):
                new_pixels[x, y] = (r, g, b, a)

    return new_img


def split_colors(input_path, tolerance=30):
    """ 主分离函数 """
    # 步骤1：检测需要分离的颜色
    colors = detect_dominant_colors(input_path)

    # 步骤2：加载原始图像
    src_img = Image.open(input_path).convert('RGBA')

    # 步骤3：创建两个颜色通道图像
    mask1 = create_color_mask(src_img, colors[0], tolerance)
    mask2 = create_color_mask(src_img, colors[1], tolerance)

    mask_2png = [mask1,mask2]

    return mask_2png



def count_rings(mask):
    """统计掩膜中内层轮廓（孔洞）的数量，每个孔洞对应一个环状结构"""
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return 0
    # 遍历所有轮廓，统计父节点不为-1的内层轮廓
    return sum(1 for h in hierarchy[0] if h[3] != -1)


def detect_ring_counts(two_image_1):
    # 读取图像并转换为RGBA数组
    # img = Image.open(image_path).convert("RGBA")
    data = np.array(two_image_1)
    rows, cols = data.shape[0], data.shape[1]

    # 创建颜色编码矩阵，透明像素为0，非透明像素编码为唯一整数
    alpha = data[:, :, 3]
    color_matrix = np.zeros((rows, cols), dtype=np.int64)
    for r in range(rows):
        for c in range(cols):
            if alpha[r, c] != 0:
                rgba = data[r, c]
                color_code = (rgba[0] << 24) | (rgba[1] << 16) | (rgba[2] << 8) | rgba[3]
                color_matrix[r, c] = color_code

    # 连通区域标记，背景为0，使用四连通
    labels = label(color_matrix, connectivity=1, background=0)

    # 分析每个区域的环状结构数量
    ring_counts = []
    for region in regionprops(labels):
        min_row, min_col, max_row, max_col = region.bbox
        # 提取局部标签并生成二值掩膜
        local_labels = labels[min_row:max_row, min_col:max_col]
        mask = (local_labels == region.label).astype(np.uint8) * 255
        # 统计环的数量
        ring_counts.append(count_rings(mask))

    return ring_counts


# 识别无环坐标
def detect_transparent_polygons_noring(pil_image):
    # 读取带透明通道的PNG
    # img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    img_array = np.array(pil_image)
    img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)

    # 分离颜色和透明通道
    bgra = cv2.split(img)
    alpha_channel = bgra[3]
    color_channel = cv2.merge(bgra[:3])  # 合并RGB通道

    # 创建基于透明通道的掩码
    _, mask = cv2.threshold(alpha_channel, 127, 255, cv2.THRESH_BINARY)

    # 中心坐标系参数
    height, width = img.shape[:2]
    center = (width / 2, height / 2)

    # 查找轮廓（使用透明通道作为掩码）
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    polygons = []
    for contour in contours:
        # 精确多边形近似
        # 调整精确参数
        epsilon = 0.0005 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) < 3:
            continue

        # 强制转换为顺时针顺序
        if cv2.contourArea(approx, oriented=True) > 0:
            approx = approx[::-1]

        # 坐标转换（考虑透明边界）
        vertices = []
        for point in approx:
            original_x = point[0][0]
            original_y = point[0][1]
            # 转换为中心坐标系
            x = round(original_x - center[0], 2)
            y = round(center[1] - original_y, 2)
            vertices.append((x, y, 0))

        polygons.append(vertices)

    return polygons


# def perpendicular_dist(point, start, end):
#     """计算点到线段的最短距离"""
#     p = np.array(point)
#     s = np.array(start)
#     e = np.array(end)
#
#     if np.allclose(s, e):
#         return np.linalg.norm(p - s)
#     return np.abs(np.cross(e - s, s - p)) / np.linalg.norm(e - s)


def perpendicular_dist(point, start, end):
    """计算点到线段的最短距离（兼容三维向量）"""
    p = np.array(point)
    s = np.array(start)
    e = np.array(end)

    # 处理线段退化为点的情况
    if np.allclose(s, e):
        return np.linalg.norm(p - s)

    # 扩展为三维向量（添加z=0）
    def to_3d(vec):
        return np.hstack((vec, 0)) if vec.size == 2 else vec

    s3 = to_3d(s)
    e3 = to_3d(e)
    p3 = to_3d(p)

    # 计算向量和投影参数
    vec_se = e3 - s3  # 线段方向向量
    vec_sp = p3 - s3  # 起点到点的向量
    t = np.dot(vec_sp, vec_se) / np.dot(vec_se, vec_se)  # 投影参数

    if t <= 0:
        return np.linalg.norm(p - s)  # 最近点为起点
    elif t >= 1:
        return np.linalg.norm(p - e)  # 最近点为终点
    else:
        # 叉积计算距离（取三维叉积的模）
        cross = np.cross(vec_se, vec_sp)
        return np.linalg.norm(cross) / np.linalg.norm(vec_se)


def rdp_simplify(points, epsilon=2.0):
    """Ramer-Douglas-Peucker路径简化算法"""
    if len(points) <= 2:
        return [tuple(p) for p in points]

    points = [np.array(p) for p in points]
    start, end = points[0], points[-1]

    max_dist = 0
    index = 0
    for i in range(1, len(points) - 1):
        dist = perpendicular_dist(points[i], start, end)
        if dist > max_dist:
            max_dist = dist
            index = i

    if max_dist > epsilon:
        left = rdp_simplify(points[:index + 1], epsilon)
        right = rdp_simplify(points[index:], epsilon)
        return left[:-1] + right
    else:
        return [tuple(start), tuple(end)]


def merge_close_nodes(nodes, connections, threshold=5.0):

    if not nodes:
        return [], []

    # 构建KDTree加速邻近搜索
    node_points = np.array([(n[0], n[1]) for n in nodes])
    tree = cKDTree(node_points)

    # 寻找邻近簇
    clusters = tree.query_ball_tree(tree, threshold)

    # 去重处理
    seen = set()
    unique_clusters = []
    for i, cluster in enumerate(clusters):
        if i not in seen:
            unique_clusters.append(cluster)
            seen.update(cluster)

    # 生成合并后的节点
    merged_nodes = []
    index_mapping = np.zeros(len(nodes), dtype=int)
    for cluster in unique_clusters:
        # 计算簇中心
        cluster_points = node_points[cluster]
        center = np.mean(cluster_points, axis=0)
        merged_nodes.append((center[0], center[1], 0))
        # 建立索引映射
        for idx in cluster:
            index_mapping[idx] = len(merged_nodes) - 1

    # 更新连接关系
    merged_conn = set()
    for a, b in connections:
        new_a = index_mapping[a]
        new_b = index_mapping[b]
        if new_a != new_b:  # 过滤自连接
            merged_conn.add((new_a, new_b) if new_a < new_b else (new_b, new_a))

    return merged_nodes, list(merged_conn)


def detect_transparent_polygons_ring(pil_image):
    img_array = np.array(pil_image)
    if pil_image.mode == 'RGBA':
        img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)  # 网页1推荐的转换方式
    else:
        raise ValueError("输入图像必须为RGBA模式")

    # 分离透明通道生成二值图像（优化网页3的通道处理逻辑）
    alpha_channel = img[:, :, 3]
    binary_image = np.where(alpha_channel > 0, 255, 0).astype(np.uint8)

    # 骨架化处理
    skeleton = skeletonize(binary_image // 255)
    skeleton_uint16 = skeleton.astype(np.uint16)

    # 构建骨架图
    graph = sknw.build_sknw(skeleton_uint16)

    # 图结构优化
    # 过滤短边
    min_branch = 10
    edges_to_remove = []
    for s, e, attr in graph.edges(data=True):
        pts = attr['pts']
        if len(pts) < 2:
            edges_to_remove.append((s, e))
            continue
        total_length = sum(np.linalg.norm(np.array(pts[i]) - np.array(pts[i - 1]))
                           for i in range(1, len(pts)))
        if total_length < min_branch:
            edges_to_remove.append((s, e))
    graph.remove_edges_from(edges_to_remove)

    # 清理孤立节点
    graph.remove_nodes_from(list(nx.isolates(graph)))

    # ------------------------- 关键点检测 -------------------------
    height, width = binary_image.shape
    nodes = []
    coord_map = {}

    # 处理原始节点
    for node in graph.nodes():
        y, x = graph.nodes[node]['o']  # sknw坐标格式(y, x)
        conv_x = x - width / 2
        conv_y = -(y - height / 2)
        key = (round(conv_x, 2), round(conv_y, 2))
        if key not in coord_map:
            nodes.append((conv_x, conv_y, 0))
            coord_map[key] = len(nodes) - 1

    # 处理边路径增强检测
    new_connections = []
    rdp_epsilon = 2.0
    for s, e, attr in graph.edges(data=True):
        raw_points = [np.array([x, y]) for y, x in attr['pts']]
        converted_points = [(p[0] - width / 2, -(p[1] - height / 2)) for p in raw_points]

        key_points = rdp_simplify(converted_points, epsilon=rdp_epsilon)

        prev_idx = None
        for point in key_points:
            x, y = point
            key = (round(x, 2), round(y, 2))

            if key not in coord_map:
                nodes.append((x, y, 0))
                coord_map[key] = len(nodes) - 1

            current_idx = coord_map[key]
            if prev_idx is not None:
                if (prev_idx, current_idx) not in new_connections and \
                        (current_idx, prev_idx) not in new_connections:
                    new_connections.append((prev_idx, current_idx))
            prev_idx = current_idx


    merge_threshold = 20.0
    merged_nodes, merged_conn = merge_close_nodes(
        nodes,
        new_connections,
        threshold=merge_threshold
    )

    vertices = [(round(float(x)), round(float(y)), z) for x, y, z in merged_nodes]
    edges = [(int(x), int(y)) for x, y in merged_conn]

    return vertices, edges




def process_main(img_path):
    separate_png = split_colors(
        input_path=img_path,
        tolerance=30  # 可调整匹配敏感度
    )

    for i in separate_png:
        rings = detect_ring_counts(i)
        if all(x == 0 for x in rings):
            # print("无环")
            polygons = detect_transparent_polygons_noring(i)
            polygons_out = []
            for j in polygons:
                converted = [(float(x), float(y), z) for x, y, z in j]
                polygons_out.append(converted)
            # print(len(polygons_out))
            # print(polygons_out)

        else:
            # print(polygons)
            # print("有环")
            vertices, edges = detect_transparent_polygons_ring(i)
            # print(vertices)
            # print(len(vertices))
            # print(edges)
            # print(len(edges))

    return polygons_out,vertices,edges




input_path="image_in/img_2.png"
# process_main(input_path)
polygons_out,vertices,edges = process_main(input_path)
print("无环坐标")
print(polygons_out)
print("有环坐标及连线")
print(vertices)
print(edges)


