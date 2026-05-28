# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""
模板和AI指令操作符

处理场景模板的应用和LLM指令的解析执行。
"""

import bpy
import json
import re
import regex
from SCGS.scene_template_config import SceneTemplate, ConfigParser


class SNA_OT_Apply_Template(bpy.types.Operator):
    """应用预定义的场景模板"""
    bl_idname = "sna.apply_template"
    bl_label = "应用模板"
    bl_description = "根据选择的模板编号自动配置树木、道路和座椅类型"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        template_input = context.scene.sna_template_selection.strip()
        
        if not template_input:
            self.report({'ERROR'}, "请输入模板编号或模板名称")
            return {"CANCELLED"}
        
        # 支持多种输入格式：纯数字、带前缀的ID
        template_id = None
        
        # 如果是纯数字，直接用作ID
        if template_input.isdigit():
            template_id = template_input
        else:
            # 尝试从模板名称或描述中匹配
            all_templates = SceneTemplate.get_all_templates()
            for tid, config in all_templates.items():
                if template_input.lower() in config.get("name", "").lower() or \
                   template_input.lower() in config.get("description", "").lower():
                    template_id = tid
                    break
        
        if template_id is None:
            template_id = template_input  # 尝试作为ID
        
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
        """应用配置到场景"""
        if "tree" in config:
            self._apply_tree_config(context, config["tree"])
        
        if "road" in config:
            self._apply_road_config(context, config["road"])
        
        if "bench" in config:
            self._apply_bench_config(context, config["bench"])
    
    def _apply_tree_config(self, context, tree_type):
        """应用树木配置"""
        context.scene.sna_street_asset_type_append = 'Tree'
        context.scene.sna_street_asset_type = 'Tree'
        # 获取对应的资产名称
        tree_asset = SceneTemplate.get_asset_name("tree", tree_type)
        if tree_asset:
            context.scene.sna_street_asset_browser = tree_asset
        try:
            bpy.ops.sna.filter_street_assets_c5c0e('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用树木配置时出错: {e}")
    
    def _apply_road_config(self, context, road_type):
        """应用道路配置"""
        context.scene.sna_road_materials_type_append = 'Road'
        context.scene.sna_road_materials_type_ = 'Road'
        # 获取对应的资产名称
        road_asset = SceneTemplate.get_asset_name("road", road_type)
        if road_asset:
            context.scene.sna_road_materials_browser = road_asset
        try:
            bpy.ops.sna.road_materials_filter_6a3ec('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用道路配置时出错: {e}")
    
    def _apply_bench_config(self, context, bench_type):
        """应用座椅配置"""
        context.scene.sna_street_asset_type_append = 'Bench'
        context.scene.sna_street_asset_type = 'Bench'
        # 获取对应的资产名称
        bench_asset = SceneTemplate.get_asset_name("bench", bench_type)
        if bench_asset:
            context.scene.sna_street_asset_browser = bench_asset
        try:
            bpy.ops.sna.filter_street_assets_c5c0e('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用座椅配置时出错: {e}")


class SNA_OT_Process_AI_Instruction(bpy.types.Operator):
    """处理AI自然语言指令"""
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
            # 尝试导入LLM客户端
            try:
                from SCGS.dashscope_client import chat_completions_content
                has_llm = True
            except ImportError:
                self.report({'WARNING'}, "未找到LLM客户端，使用本地解析")
                has_llm = False
            
            if has_llm:
                config = self._parse_with_llm(instruction)
            else:
                config = self._parse_locally(instruction)
            
            # 验证配置
            is_valid, error_msg = ConfigParser.validate_config(config)
            if not is_valid:
                self.report({'ERROR'}, f"配置无效: {error_msg}")
                return {"CANCELLED"}
            
            # 应用配置
            self._apply_config(context, config)
            
            # 生成返回消息
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
        """使用LLM解析指令"""
        try:
            from SCGS.dashscope_client import chat_completions_content
        except ImportError:
            raise ImportError("无法导入dashscope_client")
        
        prompt = SceneTemplate.create_prompt_for_parsing().replace(
            "{INSTRUCTION}", instruction
        )
        
        try:
            response_str = chat_completions_content(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as e:
            raise RuntimeError(f"LLM API调用失败: {str(e)}")
        
        # 解析响应
        config = ConfigParser.parse_response(response_str)
        return config
    
    def _parse_locally(self, instruction):
        """本地解析指令（不使用LLM）"""
        config = {}
        
        # 检查是否是模板ID
        if instruction.strip().isdigit():
            template = SceneTemplate.get_template(instruction.strip())
            if template:
                config.update({
                    "tree": template.get("tree"),
                    "road": template.get("road"),
                    "bench": template.get("bench")
                })
                return config
        
        # 根据关键词解析
        instruction_lower = instruction.lower()
        
        # 提取数字类型参数
        # 查找模式: "树木" 或 "tree" 后跟数字
        tree_patterns = [
            r'树木[：:=\s]+(\d)',
            r'tree[：:=\s]+(\d)',
            r'树[：:=\s]+(\d)',
        ]
        for pattern in tree_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["tree"] = match.group(1)
                break
        
        # 查找模式: "道路" 或 "road" 后跟数字
        road_patterns = [
            r'道路[：:=\s]+(\d)',
            r'road[：:=\s]+(\d)',
            r'路[：:=\s]+(\d)',
        ]
        for pattern in road_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["road"] = match.group(1)
                break
        
        # 查找模式: "座椅" 或 "bench" 后跟数字
        bench_patterns = [
            r'座椅[：:=\s]+(\d)',
            r'bench[：:=\s]+(\d)',
            r'椅[：:=\s]+(\d)',
        ]
        for pattern in bench_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                config["bench"] = match.group(1)
                break
        
        # 如果没有提取到任何参数，尝试模糊匹配
        if not config:
            # 查找所有连续的数字
            numbers = re.findall(r'\d', instruction)
            if numbers:
                # 简单策略：按顺序分配给tree、road、bench
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
            self._apply_tree_config(context, config["tree"])
        
        if "road" in config:
            self._apply_road_config(context, config["road"])
        
        if "bench" in config:
            self._apply_bench_config(context, config["bench"])
    
    def _apply_tree_config(self, context, tree_type):
        """应用树木配置"""
        context.scene.sna_street_asset_type_append = 'Tree'
        context.scene.sna_street_asset_type = 'Tree'
        tree_asset = SceneTemplate.get_asset_name("tree", str(tree_type))
        if tree_asset:
            context.scene.sna_street_asset_browser = tree_asset
        try:
            bpy.ops.sna.filter_street_assets_c5c0e('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用树木配置时出错: {e}")
    
    def _apply_road_config(self, context, road_type):
        """应用道路配置"""
        context.scene.sna_road_materials_type_append = 'Road'
        context.scene.sna_road_materials_type_ = 'Road'
        road_asset = SceneTemplate.get_asset_name("road", str(road_type))
        if road_asset:
            context.scene.sna_road_materials_browser = road_asset
        try:
            bpy.ops.sna.road_materials_filter_6a3ec('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用道路配置时出错: {e}")
    
    def _apply_bench_config(self, context, bench_type):
        """应用座椅配置"""
        context.scene.sna_street_asset_type_append = 'Bench'
        context.scene.sna_street_asset_type = 'Bench'
        bench_asset = SceneTemplate.get_asset_name("bench", str(bench_type))
        if bench_asset:
            context.scene.sna_street_asset_browser = bench_asset
        try:
            bpy.ops.sna.filter_street_assets_c5c0e('INVOKE_DEFAULT')
        except Exception as e:
            print(f"应用座椅配置时出错: {e}")
