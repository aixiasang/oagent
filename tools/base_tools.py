import os
import requests
from .register import register_tool

@register_tool(description="获取指定城市的天气信息", name="get_weather", allow_overwrite=True)
def get_weather(city: str):
    """
    {
        "fn": "获取指定城市的天气信息",
        "args": {
            "city": "城市名称,必须使用拼音或者英文来进行访问"
        }
    }
    """
    api_key = os.getenv("WEATHERAPI_KEY")  
    base_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        'key': api_key,
        'q': city,
        'aqi': 'no' 
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        weather = data['current']['condition']['text']
        temperature = data['current']['temp_c']
        return f"The weather in {city} is {weather} with a temperature of {temperature}°C."
    else:
        return f"Could not retrieve weather information for {city}."    
    
if __name__ == '__main__':
    from .register import get_registered_tools
    from ._mcp import init_mcp_tools
    mcp_cfg={
    "mcpServers": {
        "context7": {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"]
        }
    }
    }

    # init_mcp_tools(mcp_cfg)
    print(get_registered_tools())