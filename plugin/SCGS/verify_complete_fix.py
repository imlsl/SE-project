#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证所有修复已正确应用到各个文件中
"""

import os
import re

def check_file_content(file_path, pattern_name, pattern_regex):
    """检查文件中是否包含特定的模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if re.search(pattern_regex, content):
            return True, "✓ 找到"
        else:
            return False, "✗ 未找到"
    except Exception as e:
        return False, f"✗ 错误: {str(e)}"

def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🔍 枚举错误修复验证")
    print("=" * 70)
    
    # 检查项目
    checks = [
        {
            "name": "scene_template_config.py - ASSET_NAMES 常量",
            "file": os.path.join(base_path, "scene_template_config.py"),
            "pattern": r'ASSET_NAMES\s*=\s*\{.*?"tree".*?"road".*?"bench"',
            "description": "资产名称映射表"
        },
        {
            "name": "scene_template_config.py - get_asset_name 方法",
            "file": os.path.join(base_path, "scene_template_config.py"),
            "pattern": r'def get_asset_name\(cls.*asset_type.*index',
            "description": "获取资产名称的方法"
        },
        {
            "name": "__init__.py - 导入 SceneTemplate",
            "file": os.path.join(base_path, "__init__.py"),
            "pattern": r'from SCGS\.scene_template_config import SceneTemplate',
            "description": "在 __init__.py 中导入 SceneTemplate"
        },
        {
            "name": "__init__.py - 模板应用处的修复",
            "file": os.path.join(base_path, "__init__.py"),
            "pattern": r'tree_asset\s*=\s*SceneTemplate\.get_asset_name\("tree".*template\["tree"\]\)',
            "description": "第 1205 行附近的树木类型修复"
        },
        {
            "name": "__init__.py - AI 指令处的修复",
            "file": os.path.join(base_path, "__init__.py"),
            "pattern": r'tree_asset\s*=\s*SceneTemplate\.get_asset_name\("tree".*config\["tree"\]\)',
            "description": "第 1273 行附近的树木类型修复"
        },
        {
            "name": "template_operators.py - 导入 SceneTemplate",
            "file": os.path.join(base_path, "template_operators.py"),
            "pattern": r'from SCGS\.scene_template_config import SceneTemplate',
            "description": "在 template_operators.py 中导入 SceneTemplate"
        },
        {
            "name": "template_operators.py - Apply 操作符修复",
            "file": os.path.join(base_path, "template_operators.py"),
            "pattern": r'class SNA_OT_Apply_Template.*get_asset_name',
            "description": "SNA_OT_Apply_Template 中使用 get_asset_name"
        },
        {
            "name": "template_operators.py - AI 操作符修复",
            "file": os.path.join(base_path, "template_operators.py"),
            "pattern": r'class SNA_OT_Process_AI_Instruction.*get_asset_name',
            "description": "SNA_OT_Process_AI_Instruction 中使用 get_asset_name"
        }
    ]
    
    all_passed = True
    results = []
    
    for check in checks:
        exists = os.path.exists(check["file"])
        if not exists:
            results.append({
                "name": check["name"],
                "status": False,
                "message": f"✗ 文件不存在: {check['file']}"
            })
            all_passed = False
            continue
        
        found, message = check_file_content(check["file"], check["name"], check["pattern"])
        results.append({
            "name": check["name"],
            "status": found,
            "message": message,
            "description": check["description"]
        })
        
        if not found:
            all_passed = False
    
    # 输出结果
    for result in results:
        status = "✓" if result["status"] else "✗"
        print(f"\n{status} {result['name']}")
        print(f"   {result['message']}")
        if "description" in result:
            print(f"   📝 {result['description']}")
    
    # 总结
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 所有修复已正确应用！")
        print("\n下一步:")
        print("  1. 在 Blender 中重新加载插件")
        print("  2. 应用模板或 AI 指令")
        print("  3. 验证不出现 TypeError")
        return 0
    else:
        print("❌ 发现问题！请检查以上 ✗ 标记的项目")
        print("\n常见原因:")
        print("  - 文件未保存")
        print("  - 文件路径不正确")
        print("  - 导入语句有误")
        return 1
    
    print("=" * 70)

if __name__ == "__main__":
    exit(main())
