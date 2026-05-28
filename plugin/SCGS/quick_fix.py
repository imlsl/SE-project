#!/usr/bin/env python3
"""
⚡ 快速修复指南 (3 行代码诊断)
复制到 Blender Python 控制台运行
"""

import bpy

# 找出您的集合名称
print("\n=== 您的 Blender 集合 ===\n")
for col in bpy.data.collections:
    print(f"• {col.name}")

print("\n✅ 从上面选择相应的集合名称，复制到 scene_template_config.py 中\n")
