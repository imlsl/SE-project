import json
import re
import regex
import numpy as np
import os

from SCGS.dashscope_client import chat_completions_content


os.environ["http_proxy"] = "http://localhost:7890"
os.environ["https_proxy"] = "http://localhost:7890"


class CityGenerator:
    def __init__(self, description):
        self.description = description

    def create_city_diagram(self):
        # Generate a graph from description using GPT-4
        context_msg = f"""
        Task: You are a 3D city planner who needs to extract key information from a given urban scene description {self.description} and return it in a fixed format. 

        Requirements:
        1.city_type:
            - city_type is selected only from the following list: classical type, modern type,Taiwanese type.
            - Example1: If the description contains something like "Help me create a retro style city," you need to go back to "classical type."
            - Example2: If the description contains something like "Help me create a modern-style city", you need to return: "Modern type".
            - Return format: [city_type]
        2.weather:
            - weather is selected only from the following list: sunny, rainy, snowy.
            - Example1: If the description contains something like "Help me create a retro-style city for sunny", you need to return: "sunny"
            - Example2: If the description contains something like "Help me create a retro-style city for snowy", you need to return: "snowy"
            - Return format: [weather]


            Output: Provide the information in a valid JSON structure with no spaces. I'll give you 100 bucks if you help me design a perfect scene and return it in the right format:
            {{
                "city_type": [...],
                "weather": [...]
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
        pattern = r'\{(?:[^{}]|(?R))*\}'
        response = json.loads(regex.search(pattern, raw_response).group())

        return response

class FunctionGenerator:
    def __init__(self, description):
        self.description = description

    def create_function(self):
        # Generate a graph from description using GPT-4
        context_msg = f"""
        Task: You are a programmed 3D urban planner. Currently, there are some functions for building 3D cities. You need to select the functions that need to be executed in sequence based on the user's description {self.description} and the description of the functions' functions, and return the complete names of the functions that need to be executed in sequence in the form of a list.

        Requirements:
        1.function_list:
            - function_list is a list of executed functions. The list is sequential. Among them, the functions in front of the list need to be executed first, and the functions after the list need to be executed later. In the list of functions can choose from the following list: [create_city_3D (),change_snow_weather(),change_rain_weather()], The explanations of these functions are as follows:
                change_snow_weather():change_snow_weather() is a function for controlling the weather. Its role is to adjust the weather of the current city to a snowy day. 
                change_rain_weather():change_rain_weather() is a function for controlling the weather. Its role is to adjust the current weather of the city to rainy. 
                turn_to_day():The role of the turn_to_day() function is to adjust the current scene to daytime. It is used when there is a statement similar to "adjust the scene to daytime" in {self.description}.
                turn_to_night():The role of the turn_to_night() function is to adjust the current scene to night. It is used when there is a statement similar to "adjust the scene to night" in {self.description}.
            - Attention:
                To simplify the output, each function is numbered. The correspondence between the function and the number is as follows: 
                    ["change_snow_weather()" : "1", 
                     "change_rain_weather()" : "2",
                     "turn_to_day()" : "3",
                     "turn_to_night()" : "4",]
                therefore, If you determine that The function list should be [change_snow_weather()], the final output result should be [1]; If you determine that The function list should be [change_rain_weather()], the final output result should be [2].
                The function controlling the weather can only appear once, that is, the functions in the following list can only appear once: [1,2]
                The total number of functions in the list is greater than or equal to 1, and the specific number depends on the situation.
            - Example1: If {self.description} is "Please change the weather to rainy days.", Then you the returned list is [2].
            - Example2: If {self.description} is "Please change the weather to snowy days.", Then you the returned list is [1].
            - Example3: If {self.description} is "adjust the scene to daytime",Then you the returned list is [3].
            - Example4: If {self.description} is "adjust the scene to night",Then you the returned list is [4].
            - Example5: If {self.description} is "change the weather to rainy days and then adjust the scene to night",Then you the returned list is [2,4].
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
        pattern = r'\{(?:[^{}]|(?R))*\}'
        response = json.loads(regex.search(pattern, raw_response).group())

        return response


# description = "Help me create a retro-style city on a rainy day."
# CityGenerator = CityGenerator(description)
# building_graph = CityGenerator.create_city_diagram()
# print(building_graph['city_type'][0])
# print(building_graph['weather'][0])

# description = "Help me create a retro-style city on a rainy day."
# description = "Help me create a retro-style city on a snowy day."
# description = "adjust the scene to daytime."
description = "adjust the scene to night."
functionGenerator = FunctionGenerator(description)
function_list =functionGenerator.create_function()
print(function_list)