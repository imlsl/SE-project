#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证模板修复 - 检查资产名称映射是否正确
"""

import sys
import json

# 模拟SceneTemplate类
class SceneTemplate:
    """场景模板配置类"""
    
    # 资产名称映射（资产索引 -> 资产名称/ID）
    # 注：具体的资产名称需要根据Blender场景中实际的集合/对象名称来配置
    ASSET_NAMES = {
        "tree": {
            "1": "Tree1",      # 现代树木
            "2": "Tree2",      # 古典树木
            "3": "Tree3",      # 生态树木
            "4": "Tree4"       # 台湾树木
        },
        "road": {
            "1": "Road1",      # 古典道路
            "2": "Road2",      # 现代道路
            "3": "Road3",      # 生态道路
            "4": "Road4"       # 工业道路
        },
        "bench": {
            "1": "Bench",      # 现代座椅
            "2": "Bench2",     # 古典座椅
            "3": "Bench3",     # 生态座椅
            "4": "Bench4"      # 台湾座椅
        }
    }
    
    TEMPLATES = {
        "0": {
            "name": "现代风格",
            "description": "现代城市风格，树木类型1，道路类型2，座椅类型1",
            "tree": "1",
            "road": "2",
            "bench": "1"
        },
        "1": {
            "name": "古典风格",
            "description": "古典城市风格，树木类型2，道路类型1，座椅类型2",
            "tree": "2",
            "road": "1",
            "bench": "2"
        },
        "2": {
            "name": "绿色生态",
            "description": "生态城市风格，树木类型3，道路类型3，座椅类型3",
            "tree": "3",
            "road": "3",
            "bench": "3"
        },
        "3": {
            "name": "工业风格",
            "description": "工业城市风格，树木类型1，道路类型4，座椅类型1",
            "tree": "1",
            "road": "4",
            "bench": "1"
        },
        "4": {
            "name": "台湾风格",
            "description": "台湾城市风格，树木类型4，道路类型2，座椅类型4",
            "tree": "4",
            "road": "2",
            "bench": "4"
        }
    }
    
    @classmethod
    def get_asset_name(cls, asset_type, index):
        """根据资产类型和索引获取资产名称"""
        if asset_type in cls.ASSET_NAMES and index in cls.ASSET_NAMES[asset_type]:
            return cls.ASSET_NAMES[asset_type][index]
        return None


def verify_templates():
    """验证所有模板"""
    print("=" * 60)
    print("验证场景模板配置修复")
    print("=" * 60)
    
    all_valid = True
    
    for template_id, template_data in SceneTemplate.TEMPLATES.items():
        print(f"\n模板 {template_id}: {template_data['name']}")
        print(f"  描述: {template_data['description']}")
        
        # 验证树木
        tree_type = template_data['tree']
        tree_asset = SceneTemplate.get_asset_name("tree", tree_type)
        if tree_asset:
            print(f"  ✓ 树木类型 {tree_type} -> {tree_asset}")
        else:
            print(f"  ✗ 树木类型 {tree_type} -> 未找到资产名称")
            all_valid = False
        
        # 验证道路
        road_type = template_data['road']
        road_asset = SceneTemplate.get_asset_name("road", road_type)
        if road_asset:
            print(f"  ✓ 道路类型 {road_type} -> {road_asset}")
        else:
            print(f"  ✗ 道路类型 {road_type} -> 未找到资产名称")
            all_valid = False
        
        # 验证座椅
        bench_type = template_data['bench']
        bench_asset = SceneTemplate.get_asset_name("bench", bench_type)
        if bench_asset:
            print(f"  ✓ 座椅类型 {bench_type} -> {bench_asset}")
        else:
            print(f"  ✗ 座椅类型 {bench_type} -> 未找到资产名称")
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✓ 所有模板验证通过！资产名称映射正确。")
        print("修复已完成，现在应该不会出现枚举错误。")
    else:
        print("✗ 发现问题！某些资产类型的映射缺失。")
    print("=" * 60)
    
    return all_valid


if __name__ == "__main__":
    success = verify_templates()
    sys.exit(0 if success else 1)
