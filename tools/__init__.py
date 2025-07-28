
from .register import register_tool,execute_tool,get_registered_tools,get_tools_list
from .base_tools import get_weather
from .with_os import get_os_info,get_current_time
from ._mcp import init_mcp_tools
all=[
    register_tool,
    execute_tool,
    get_tools_list,
    get_registered_tools,
    get_weather,
    get_os_info,
    get_current_time,
    init_mcp_tools
]