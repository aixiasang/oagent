"""
实现工具注册 
目前schema仅仅支持openai格式的
"""
import inspect
import json
import re
from typing import Dict, List, Callable, Optional
import logging
logger = logging.getLogger(__name__)
_local_registered_tools: Dict[str, Dict] = {}
_mcp_registered_tools: Dict[str, Dict] = {}


def _get_local_tools():
    return [{"type": "function", "function": tool["def"]} for tool in _local_registered_tools.values()] 
def _get_mcp_tools():
    return [{"type": "function", "function": tool["def"]} for tool in _mcp_registered_tools.values()]

def _search_tool(tool_name: str,flag='all') -> Optional[Dict]:
    
    result_tools=None
    if tool_name in _local_registered_tools:
        result_tools=_local_registered_tools[tool_name]
        if flag=='local':
            return result_tools
    if tool_name in _mcp_registered_tools:
        result_tools=_mcp_registered_tools[tool_name]
        if flag=='mcp':
            return result_tools
    return result_tools

def get_registered_tools() -> List[Dict]:
    return _get_local_tools() + _get_mcp_tools()

def get_registered_tool(tool_name: str) -> Dict:
    return _search_tool(tool_name) or {}

def get_tools_list(tools:List[str],has_mcp:bool=False) -> List[Dict]:
    all=tool_def=_get_mcp_tools() if has_mcp else []
    for tool in tools:
        _target_tool=_search_tool(tool,'local')
        if _target_tool:
            tool_def.append({
                "type": "function",
                "function": _target_tool["def"]
            })
    return tool_def 

def execute_tool(tool_name: str, arguments: Dict) -> str:
    _ok_tool = _search_tool(tool_name)
    if _ok_tool:
        tool_info = _ok_tool
    else:
        return f"Error: Tool '{tool_name}' not found"
    try:
        result = tool_info["fn"](**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"
def execute_tool(tool_name: str, arguments: Dict,search_tools:Callable=_search_tool) -> str:
    _ok_tool = search_tools(tool_name)
    if _ok_tool:
        tool_info = _ok_tool
    else:
        return f"Error: Tool '{tool_name}' not found"
    try:
        result = tool_info["fn"](**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

"""
本地工具注册到local_registered_tools
"""
def _base_regsiter(
    name: Optional[str] = None, 
    description: Optional[str] = None, 
    allow_overwrite: bool = False,
    register_map:Dict=_local_registered_tools,
):
    if callable(name):
        func = name
        return _base_regsiter()(func)
    def decorator(func: Callable):
        nonlocal name, description
        tool_name = name or func.__name__
        docstring = func.__doc__ or ""
        tool_description = description or docstring.strip() or f"Function {tool_name}"
        json_match = re.search(r'\{.*\}', docstring, re.DOTALL)
        custom_params = {}
        if json_match:
            try:
                json_def = json.loads(json_match.group())
                if "fn" in json_def and not description:
                    tool_description = json_def["fn"]
                if "args" in json_def:
                    custom_params = json_def["args"]
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in {func.__name__} docstring: {e}")
                raise
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
            param_type = "string"  
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    List: "array",
                    dict: "object",
                    Dict: "object"
                }
                param_type = type_map.get(param.annotation, "string")
            param_description = custom_params.get(param_name, f"Parameter {param_name}")
            parameters["properties"][param_name] = {
                "type": param_type,
                "description": param_description
            }
        tool_definition = {
            "name": tool_name,
            "description": tool_description,
            "parameters": parameters
        }
        if tool_name in _local_registered_tools and not allow_overwrite:
            if allow_overwrite:
                return func
        register_map[tool_name] = {
            "def": tool_definition,
            "fn": func
        }
        return func
    return decorator

def register_tool(
    name: Optional[str] = None, 
    description: Optional[str] = None, 
    allow_overwrite: bool = False,
) -> None:
    return _base_regsiter(name, description, allow_overwrite,register_map=_local_registered_tools)



if __name__ == "__main__":
    @register_tool
    def calculate_area(length: float, width: float) -> float:
        """
        {
            "fn": "Calculate the area of a rectangle",
            "args": {
                "length": "Length of the rectangle",
                "width": "Width of the rectangle"
            }
        }
        """
        return length * width

    @register_tool(name="weather_lookup")
    def get_weather(city: str, country: str = "US") -> str:
        """
        {
            "fn": "Get current weather information for a specific location",
            "args": {
                "city": "Name of the city",
                "country": "Two-letter country code (default: US)"
            }
        }
        """
        return f"Current weather in {city}, {country}: 72°F, Sunny"

    @register_tool
    def generate_greeting(name: str, formal: bool = False) -> str:
        """
        {
            "fn": "Generate a personalized greeting",
            "args": {
                "name": "Name of the person to greet",
                "formal": "Whether to use a formal greeting"
            }
        }
        """
        if formal:
            return f"Good day, {name}. It is a pleasure to make your acquaintance."
        else:
            return f"Hi {name}! How are you doing?"
    print("Registered Tools:")
    for tool in get_registered_tools():
        func = tool["function"]
        print(f"- {func['name']}: {func['description']}")
    
    print("\nTool Execution Examples:")
    print("Area Calculation:", execute_tool("calculate_area", {"length": 5, "width": 3}))
    print("Weather Lookup:", execute_tool("weather_lookup", {"city": "New York"}))
    print("Greeting:", execute_tool("generate_greeting", {"name": "Alice", "formal": True}))
    import os
    case1={
    "mcpServers": {
        "zhipu-web-search-sse": {
        "url": f"https://open.bigmodel.cn/api/mcp/web_search/sse?Authorization={os.getenv('zhipuai')}"
        }
    } 
    }
    # init_mcp_tools(case1)
    # print(get_registered_tools())
    # ans=["<function>"+str(tool)+"</function>" for tool in get_registered_tools()]
    # print('\n'.join(ans))
    # ans=execute_tool("mcp_zhipu-web-search-sse_web_search",{"search_query":"what is the weather in beijing"})
    # print(ans)