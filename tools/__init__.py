
from .register import register_tool,execute_tool,get_registered_tools
from .base_tools import get_weather
from .with_os import get_os_info,get_current_time
all=[
    register_tool,
    execute_tool,
    get_registered_tools,
    get_weather,
    get_os_info,
    get_current_time
]