import os
import requests
from .tools import register_tool

@register_tool(description="获取指定城市的天气信息", name="local_get_weather", allow_overwrite=True)
def get_weather(city: str):
    """
    {
        "func": "获取指定城市的天气信息",
        "params": {
            "city": "城市名称,必须使用拼音或者英文来进行访问"
        }
    }
    """
    # 使用 WeatherAPI 的 API 来获取天气信息
    api_key = os.getenv("WEATHERAPI_KEY")  # 替换为你自己的 WeatherAPI APIKEY
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        'key': api_key,
        'q': city,
        'aqi': 'no'  # 不需要空气质量数据
    }
    
    # 调用天气 API
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        weather = data['current']['condition']['text']
        temperature = data['current']['temp_c']
        return f"The weather in {city} is {weather} with a temperature of {temperature}°C."
    else:
        return f"Could not retrieve weather information for {city}."    