# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""
场景模板功能测试脚本

在Blender Python控制台中运行此文件以验证功能。
"""


def test_scene_template():
    """测试SceneTemplate类"""
    print("=" * 60)
    print("测试 SceneTemplate 类")
    print("=" * 60)
    
    from SCGS.scene_template_config import SceneTemplate
    
    # 测试1: 获取所有模板
    print("\n测试1: 获取所有模板")
    all_templates = SceneTemplate.get_all_templates()
    print(f"总模板数: {len(all_templates)}")
    for tid, config in all_templates.items():
        print(f"  {tid}: {config['name']}")
    
    # 测试2: 获取特定模板
    print("\n测试2: 获取特定模板")
    template_0 = SceneTemplate.get_template("0")
    if template_0:
        print(f"模板0: {template_0}")
    else:
        print("ERROR: 未找到模板0")
    
    # 测试3: 列出所有模板信息
    print("\n测试3: 列出所有模板信息")
    templates_list = SceneTemplate.list_templates()
    for t in templates_list:
        print(f"  ID: {t['id']}, 名称: {t['name']}")
        print(f"     {t['description']}")
    
    # 测试4: 生成LLM提示词
    print("\n测试4: 生成LLM提示词")
    prompt = SceneTemplate.create_prompt_for_parsing()
    print(f"提示词长度: {len(prompt)} 字符")
    print(f"包含模板数: {prompt.count('id')}")
    
    print("\n✓ SceneTemplate 类测试完成")


def test_config_parser():
    """测试ConfigParser类"""
    print("\n" + "=" * 60)
    print("测试 ConfigParser 类")
    print("=" * 60)
    
    from SCGS.scene_template_config import ConfigParser
    
    # 测试1: 解析JSON响应
    print("\n测试1: 解析JSON响应")
    response1 = '{"tree": "1", "road": "2", "bench": "1"}'
    config1 = ConfigParser.parse_response(response1)
    print(f"输入: {response1}")
    print(f"输出: {config1}")
    
    # 测试2: 解析带markdown的响应
    print("\n测试2: 解析带markdown的响应")
    response2 = '```json\n{"tree": "2", "road": "3", "bench": "4"}\n```'
    config2 = ConfigParser.parse_response(response2)
    print(f"输入: {response2}")
    print(f"输出: {config2}")
    
    # 测试3: 验证有效配置
    print("\n测试3: 验证有效配置")
    valid_config = {"tree": "1", "road": "2", "bench": "3"}
    is_valid, msg = ConfigParser.validate_config(valid_config)
    print(f"配置: {valid_config}")
    print(f"有效: {is_valid}, 消息: {msg}")
    
    # 测试4: 验证无效配置（参数超出范围）
    print("\n测试4: 验证无效配置")
    invalid_config = {"tree": "5", "road": "2"}  # tree超出范围
    is_valid, msg = ConfigParser.validate_config(invalid_config)
    print(f"配置: {invalid_config}")
    print(f"有效: {is_valid}, 消息: {msg}")
    
    print("\n✓ ConfigParser 类测试完成")


def test_local_parsing():
    """测试本地指令解析"""
    print("\n" + "=" * 60)
    print("测试本地指令解析")
    print("=" * 60)
    
    from SCGS.template_operators import SNA_OT_Process_AI_Instruction
    
    operator = SNA_OT_Process_AI_Instruction()
    
    test_cases = [
        "树木1, 道路2, 座椅1",
        "tree 1 road 2 bench 3",
        "树木：1，道路：2，座椅：3",
        "1 2 3",
        "tree = 1, road = 2, bench = 1",
    ]
    
    print("\n测试各种输入格式:")
    for instruction in test_cases:
        config = operator._parse_locally(instruction)
        print(f"  输入: '{instruction}'")
        print(f"  结果: {config}")


def test_template_validation():
    """测试模板验证"""
    print("\n" + "=" * 60)
    print("测试模板验证")
    print("=" * 60)
    
    from SCGS.scene_template_config import SceneTemplate, ConfigParser
    
    print("\n验证所有预定义模板:")
    all_templates = SceneTemplate.get_all_templates()
    for tid, template in all_templates.items():
        config = {
            "tree": template["tree"],
            "road": template["road"],
            "bench": template["bench"]
        }
        is_valid, msg = ConfigParser.validate_config(config)
        status = "✓" if is_valid else "✗"
        print(f"  {status} 模板 {tid} ({template['name']}): {config}")
        if not is_valid:
            print(f"      错误: {msg}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("场景模板功能测试")
    print("=" * 60)
    
    try:
        test_scene_template()
        test_config_parser()
        test_local_parsing()
        test_template_validation()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
