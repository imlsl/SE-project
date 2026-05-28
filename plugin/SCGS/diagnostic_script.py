#!/usr/bin/env python3
"""
Blender Collection Diagnostic Script
将此脚本在 Blender 的 Python 控制台中运行，以诊断可用的集合
"""

import bpy
import json

def diagnose_collections():
    """诊断 Blender 场景中的所有集合"""
    
    print("\n" + "="*80)
    print("SCGS 插件 - 集合诊断工具")
    print("="*80)
    
    # 获取所有集合
    all_collections = list(bpy.data.collections)
    
    if not all_collections:
        print("\n❌ 错误：Blender 场景中没有任何集合！")
        print("   这是问题的根本原因。")
        return
    
    print(f"\n✓ 找到 {len(all_collections)} 个集合：\n")
    
    # 按类型分类
    tree_collections = []
    road_collections = []
    bench_collections = []
    other_collections = []
    
    for col in all_collections:
        name = col.name.lower()
        if 'tree' in name:
            tree_collections.append(col.name)
        elif 'road' in name:
            road_collections.append(col.name)
        elif 'bench' in name or 'chair' in name or 'seat' in name:
            bench_collections.append(col.name)
        else:
            other_collections.append(col.name)
    
    # 打印树木集合
    if tree_collections:
        print("🌲 树木相关集合:")
        for name in tree_collections:
            print(f"   - {name}")
    else:
        print("🌲 树木相关集合: ❌ 未找到")
    
    # 打印道路集合
    if road_collections:
        print("\n🛣️  道路相关集合:")
        for name in road_collections:
            print(f"   - {name}")
    else:
        print("\n🛣️  道路相关集合: ❌ 未找到")
    
    # 打印座椅集合
    if bench_collections:
        print("\n🪑 座椅相关集合:")
        for name in bench_collections:
            print(f"   - {name}")
    else:
        print("\n🪑 座椅相关集合: ❌ 未找到")
    
    # 打印其他集合
    if other_collections:
        print("\n📦 其他集合:")
        for name in other_collections:
            print(f"   - {name}")
    
    # 打印所有集合的完整列表
    print("\n" + "-"*80)
    print("完整的集合名称列表（复制用于配置）:\n")
    
    for i, col in enumerate(all_collections, 1):
        print(f"{i:2d}. {col.name}")
    
    # 生成 Python 字典格式
    print("\n" + "-"*80)
    print("Python 字典格式（可用于 ASSET_NAMES 配置）:\n")
    
    config = {
        "tree": {
            "1": tree_collections[0] if tree_collections else "NONE"
        },
        "road": {
            "1": road_collections[0] if road_collections else "NONE"
        },
        "bench": {
            "1": bench_collections[0] if bench_collections else "NONE"
        }
    }
    
    print("ASSET_NAMES = {")
    for asset_type, values in config.items():
        print(f'    "{asset_type}": {{')
        for key, val in values.items():
            print(f'        "{key}": "{val}",')
        print("    },")
    print("}")
    
    # 检查是否存在我们期望的集合
    print("\n" + "-"*80)
    print("预期集合检查:\n")
    
    expected = [
        "Tree1_Tree_ICity_Default",
        "ICity_Road 11 dirty_Default",
        "Bench1_Bench_ICity_Default"
    ]
    
    all_names = [col.name for col in all_collections]
    
    for exp_name in expected:
        if exp_name in all_names:
            print(f"✓ {exp_name}")
        else:
            print(f"✗ {exp_name} (不存在)")
    
    # 最后的建议
    print("\n" + "="*80)
    print("📝 建议:")
    print("="*80)
    
    if not tree_collections:
        print("⚠️  警告: 未找到树木集合")
        print("   - 检查您的 Blender 文件是否包含树木资产")
        print("   - 检查集合是否被隐藏或禁用")
    
    if not road_collections:
        print("⚠️  警告: 未找到道路集合")
        print("   - 检查您的 Blender 文件是否包含道路资产")
        print("   - 检查集合是否被隐藏或禁用")
    
    if not bench_collections:
        print("⚠️  警告: 未找到座椅集合")
        print("   - 检查您的 Blender 文件是否包含座椅资产")
        print("   - 检查集合是否被隐藏或禁用")
    
    if tree_collections and road_collections and bench_collections:
        print("✓ 所有必需的资产类型都已找到！")
        print("✓ 使用上面的 Python 字典格式更新 ASSET_NAMES 配置")
    
    print("\n" + "="*80 + "\n")


def check_enum_property():
    """检查 EnumProperty 的当前状态"""
    
    print("\n" + "="*80)
    print("EnumProperty 状态检查")
    print("="*80 + "\n")
    
    scene = bpy.context.scene
    
    # 检查属性是否存在
    if hasattr(scene, 'sna_street_asset_browser'):
        print("✓ sna_street_asset_browser 属性存在")
        
        # 获取属性定义
        prop = type(scene).sna_street_asset_browser
        print(f"  属性类型: {type(prop)}")
        print(f"  当前值: {scene.sna_street_asset_browser}")
        
        # 尝试获取枚举项
        try:
            print("  (无法直接读取枚举项，需要通过 Blender UI 查看)")
        except:
            pass
    else:
        print("✗ sna_street_asset_browser 属性不存在")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    print("\n运行诊断工具...\n")
    diagnose_collections()
    check_enum_property()
    print("诊断完成！请复制上面的信息并发送给开发者。")
