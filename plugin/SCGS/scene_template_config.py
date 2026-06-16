# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""
场景模板配置模块

提供预定义的模板配置，支持一键应用多个参数。
包括树木类型、道路纹理、路边座椅、天气等的配置。
"""

import json


class SceneTemplate:
    """场景模板配置类"""

    # 资产名称映射（资产索引 -> 资产名称/ID）
    ASSET_NAMES = {
        "tree": {
            "1": "Tree1_Tree_ICity_Default",
            "2": "Tree4_Tree_ICity_Default",
            "3": "Tree8_Tree_ICity_Default",
            "4": "Tree12_Tree_ICity_Default"
        },
        "road": {
            "1": "ICity_Road 1 clean_Default",
            "2": "ICity_Road 3 clean_Default",
            "3": "ICity_Road 8 dirty_Default",
            "4": "ICity_Road 11 dirty_Default"
        },
        "bench": {
            "1": "Bench1_Bench_ICity_Default",
            "2": "Bench4_Bench_ICity_Default",
            "3": "Bench8_Bench_ICity_Default",
            "4": "Bench11_Bench_ICity_Default"
        }
    }

    TEMPLATES = {
        "0": {
            "name": "现代风格",
            "description": "现代城市风格，晴天，树木类型1，道路类型2，座椅类型1",
            "tree": "1",
            "road": "2",
            "bench": "1",
            "weather": "sunny"
        },
        "1": {
            "name": "古典风格",
            "description": "古典城市风格，雨天，树木类型2，道路类型1，座椅类型2",
            "tree": "2",
            "road": "1",
            "bench": "2",
            "weather": "rainy"
        },
        "2": {
            "name": "绿色生态",
            "description": "生态城市风格，晴天，树木类型3，道路类型3，座椅类型3",
            "tree": "3",
            "road": "3",
            "bench": "3",
            "weather": "sunny"
        },
        "3": {
            "name": "工业风格",
            "description": "工业城市风格，雨天，树木类型1，道路类型4，座椅类型1",
            "tree": "1",
            "road": "4",
            "bench": "1",
            "weather": "rainy"
        },
        "4": {
            "name": "台湾风格",
            "description": "台湾城市风格，雪天，树木类型4，道路类型2，座椅类型4",
            "tree": "4",
            "road": "2",
            "bench": "4",
            "weather": "snowy",
            "snow_loaction": (-50, 0, 50),
            "snow_scale": (50, 50, 50),
            "snow_ground_loaction": (-50, 0, 6.2779),
            "snow_ground_dimensions": (250, 150, 6.277),
            "density": 0.8,
            "thickness": 0.5
        }
    }

    @classmethod
    def get_asset_name(cls, asset_type, index):
        if asset_type in cls.ASSET_NAMES and index in cls.ASSET_NAMES[asset_type]:
            return cls.ASSET_NAMES[asset_type][index]
        return None

    @classmethod
    def get_template(cls, template_id):
        template_id_str = str(template_id)
        if template_id_str in cls.TEMPLATES:
            return cls.TEMPLATES[template_id_str]
        return None

    @classmethod
    def get_all_templates(cls):
        return cls.TEMPLATES

    @classmethod
    def list_templates(cls):
        result = []
        for template_id, config in cls.TEMPLATES.items():
            result.append({
                "id": template_id,
                "name": config.get("name", "未命名"),
                "description": config.get("description", "")
            })
        return result

    @classmethod
    def get_weather_params(cls, template_id):
        """获取指定模板的天气参数"""
        template = cls.get_template(template_id)
        if not template:
            return {"weather": "sunny"}
        weather_params = {"weather": template.get("weather", "sunny")}
        if weather_params["weather"] == "snowy":
            weather_params.update({
                "snow_loaction": template.get("snow_loaction", (-50, 0, 50)),
                "snow_scale": template.get("snow_scale", (50, 50, 50)),
                "snow_ground_loaction": template.get("snow_ground_loaction", (-50, 0, 6.2779)),
                "snow_ground_dimensions": template.get("snow_ground_dimensions", (250, 150, 6.277)),
                "density": template.get("density", 0.8),
                "thickness": template.get("thickness", 0.5)
            })
        return weather_params

    @classmethod
    def create_prompt_for_parsing(cls):
        templates_info = json.dumps(cls.list_templates(), ensure_ascii=False, indent=2)
        prompt = f"""你是一个Blender插件助手，负责解析用户的自然语言指令并生成场景配置参数。

预定义的模板（可输入模板ID或名称来一键应用完整配置）：
{templates_info}

可以设置的参数包括：
- 树木类型(tree): 数字1-4表示不同的树木模型
- 道路纹理(road): 数字1-4表示不同的道路纹理
- 座椅类型(bench): 数字1-4表示不同的座椅模型
- 天气(weather): sunny（晴天）、rainy（雨天）、snowy（雪天）

解析规则（按优先级）：
1. 如果用户提到"模板X"（如 "模板4"、"选择模板0"、"应用模板2"），直接返回该模板的完整配置
2. 如果用户通过模板名称匹配（如 "现代风格"、"古典风格"），同样返回对应模板的完整配置
3. 如果用户输入是纯数字（如 "0"、"1"），作为模板ID并返回完整配置
4. 如果用户显式指定了某个参数（如 "树木2, 道路3"），直接提取对应数值
5. 如果用户描述为自然语言，根据语义选择合适的配置

请将以下用户指令转换为JSON格式的配置参数：
指令: {{INSTRUCTION}}

必须返回以下JSON格式（如果是模板，必须包含 tree, road, bench, weather 四项）：
{{
    "tree": "1",
    "road": "2",
    "bench": "1",
    "weather": "sunny"
}}

如果是模板ID输入，同时返回模板信息：
{{
    "template_id": "0",
    "template_name": "现代风格",
    "tree": "1",
    "road": "2",
    "bench": "1",
    "weather": "sunny"
}}"""
        return prompt


class ConfigParser:
    """配置解析器，负责解析LLM的响应"""

    @staticmethod
    def parse_response(response_text):
        try:
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            config = json.loads(response_text)
            valid_config = {}
            for key in ["tree", "road", "bench"]:
                if key in config:
                    value = str(config[key])
                    if value.isdigit() and 1 <= int(value) <= 4:
                        valid_config[key] = value
            if "weather" in config:
                w = str(config["weather"]).lower().strip()
                if w in ("sunny", "rainy", "snowy"):
                    valid_config["weather"] = w
            if "template_id" in config:
                valid_config["template_id"] = str(config["template_id"])
            if "template_name" in config:
                valid_config["template_name"] = str(config["template_name"])
            return valid_config
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {str(e)}")

    @staticmethod
    def validate_config(config):
        if not isinstance(config, dict):
            return False, "配置必须是字典类型"
        valid_keys = {"tree", "road", "bench", "template_id", "template_name", "weather"}
        invalid_keys = set(config.keys()) - valid_keys
        if invalid_keys:
            return False, f"包含无效参数: {invalid_keys}"
        for key in ["tree", "road", "bench"]:
            if key in config:
                value = config[key]
                if not isinstance(value, (str, int)):
                    return False, f"参数 {key} 必须是字符串或数字"
                try:
                    num_value = int(value)
                    if not (1 <= num_value <= 4):
                        return False, f"参数 {key} 的值必须在1-4之间"
                except ValueError:
                    return False, f"参数 {key} 必须是有效的数字"
        if "weather" in config:
            if config["weather"] not in ("sunny", "rainy", "snowy"):
                return False, f"天气参数必须是 sunny、rainy 或 snowy"
        return True, ""
