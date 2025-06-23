import inspect
import json
import re
from typing import Dict, List, Callable, Optional
import asyncio
import threading
import time
import atexit
import uuid
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)


registered_tools: Dict[str, Dict] = {}

def get_registered_tools() -> List[Dict]:
    return [{"type": "function", "function": tool["def"]} for tool in registered_tools.values()]

def get_registered_tool(tool_name: str) -> Dict:
    if tool_name not in registered_tools:
        return None
    return registered_tools[tool_name]
def get_tool_list(tools:List[Dict]):
    tool_def=[]
    for tool in tools:
        if tool in registered_tools:
            tool_def.append({
                "type": "function",
                "function": registered_tools[tool]["def"]
            })
    return tool_def

def execute_tool(tool_name: str, arguments: Dict) -> str:
    if tool_name not in registered_tools:
        return f"Error: Tool '{tool_name}' is not registered"
    tool_info = registered_tools[tool_name]
    try:
        result = tool_info["func"](**arguments)
        return str(result)
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

def register_tool(
    name: Optional[str] = None, 
    description: Optional[str] = None, 
    allow_overwrite: bool = False
):
    if callable(name):
        func = name
        return register_tool()(func)
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
                if "func" in json_def and not description:
                    tool_description = json_def["func"]
                if "params" in json_def:
                    custom_params = json_def["params"]
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
        if tool_name in registered_tools:
            if allow_overwrite:
                return func
        registered_tools[tool_name] = {
            "def": tool_definition,
            "func": func
        }
        return func
    return decorator

class MCPManager:
    """
    对于mcp的工具的注册 以及 工具的执行
    代码参考qwen-agent:Qwen-Agent-main/qwen_agent/tools/mcp_manager.py
    """
    _instance = None  

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'clients'):
            self.clients: dict = {}
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(target=self.start_loop, daemon=True)
            self.loop_thread.start()
            self.processes = []
            self.monkey_patch_mcp_create_platform_compatible_process()
    
    def monkey_patch_mcp_create_platform_compatible_process(self):
        try:
            import mcp.client.stdio
            target = mcp.client.stdio._create_platform_compatible_process
        except (ModuleNotFoundError, AttributeError) as e:
            raise ImportError(
                'MCP process cleanup patch requires updated MCP. Install with `pip install -U mcp`.'
            ) from e

        async def _monkey_patched_create_platform_compatible_process(*args, **kwargs):
            process = await target(*args, **kwargs)
            self.processes.append(process)
            return process
        mcp.client.stdio._create_platform_compatible_process = _monkey_patched_create_platform_compatible_process

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def is_valid_mcp_servers(self, config: dict):
        if not isinstance(config, dict) or 'mcpServers' not in config or not isinstance(config['mcpServers'], dict):
            return False
        mcp_servers = config['mcpServers']
        for key in mcp_servers:
            server = mcp_servers[key]
            if not isinstance(server, dict):
                return False
            if 'command' in server:
                if not isinstance(server['command'], str):
                    return False
                if 'args' not in server or not isinstance(server['args'], list):
                    return False
            if 'url' in server:
                if not isinstance(server['url'], str):
                    return False
                if 'headers' in server and not isinstance(server['headers'], dict):
                    return False
            if 'env' in server and not isinstance(server['env'], dict):
                return False
        return True

    def init_config(self, config: Dict):
        if not self.is_valid_mcp_servers(config):
            raise ValueError('Invalid MCP server configuration')
        logger.info(f'Initializing MCP tools from servers: {list(config["mcpServers"].keys())}')
        future = asyncio.run_coroutine_threadsafe(self.init_config_async(config), self.loop)
        try:
            return future.result() 
        except Exception as e:
            logger.error(f'Failed to initialize MCP tools: {e}')
            raise

    async def init_config_async(self, config: Dict):
        tools: list = []
        mcp_servers = config['mcpServers']
        for server_name in mcp_servers:
            client = MCPClient()
            server = mcp_servers[server_name]
            await client.connect_to_server(server_name, server)  

            client_id = f"{server_name}_{uuid.uuid4()}"
            self.clients[client_id] = client  
            
            for tool in client.tools:   
                parameters = tool.inputSchema
                required_fields = {'type', 'properties', 'required'}
                if not all(field in parameters for field in required_fields):
                    raise ValueError(f'Missing required fields in schema: {required_fields - parameters.keys()}')

                cleaned_parameters = {
                    'type': parameters['type'],
                    'properties': parameters['properties'],
                    'required': parameters.get('required', [])
                }
                
                register_name = f"mcp_{server_name}_{tool.name}"
                
                tool_definition = {
                    "name": register_name,
                    "description": tool.description,
                    "parameters": cleaned_parameters
                }
                
                def create_tool_func(client_id, tool_name):
                    def tool_func(**kwargs):
                        manager = MCPManager()
                        client = manager.clients[client_id]
                        future = asyncio.run_coroutine_threadsafe(
                            client.execute_function(tool_name, kwargs), 
                            manager.loop
                        )
                        try:
                            return future.result()
                        except Exception as e:
                            logger.error(f'Failed to execute MCP tool: {e}')
                            return f"Tool execution error: {str(e)}"
                    return tool_func
                
                registered_tools[register_name] = {
                    "def": tool_definition,
                    "func": create_tool_func(client_id, tool.name)
                }
                
                tools.append(tool_definition)
        
        return tools

    def shutdown(self):
        futures = []
        for client_id in list(self.clients.keys()):
            client = self.clients[client_id]
            future = asyncio.run_coroutine_threadsafe(client.cleanup(), self.loop)
            futures.append(future)
            del self.clients[client_id]
        time.sleep(1)  
        
        if any(task for task in asyncio.all_tasks(self.loop) if not task.done()):
            logger.info('Forcibly terminating MCP tool processes')
            for process in self.processes:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass  
        
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.loop_thread.is_alive():
            self.loop_thread.join(timeout=5)

class MCPClient:
    def __init__(self):
        self.session = None
        self.tools = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_name, server_config):
        if 'url' in server_config:
            self._streams_context = sse_client(
                url=server_config.get('url'), 
                headers=server_config.get('headers', {"Accept": "text/event-stream"})
            )
            streams = await self.exit_stack.enter_async_context(self._streams_context)
            self._session_context = ClientSession(*streams)
            self.session = await self.exit_stack.enter_async_context(self._session_context)
        else:
            server_params = StdioServerParameters(
                command=server_config["command"],
                args=server_config["args"],
                env=server_config.get("env", None)
            )
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            logger.info(f'Initializing MCP stdio_client for {server_name}')

        await self.session.initialize()
        list_tools = await self.session.list_tools()
        self.tools = list_tools.tools

    async def execute_function(self, tool_name, tool_args: dict):
        response = await self.session.call_tool(tool_name, tool_args)
        texts = []
        for content in response.content:
            if content.type == 'text':
                texts.append(content.text)
        return '\n\n'.join(texts) if texts else 'No text response'

    async def cleanup(self):
        await self.exit_stack.aclose()

def _cleanup_mcp():
    if MCPManager._instance is not None:
        manager = MCPManager()
        manager.shutdown()

atexit.register(_cleanup_mcp)

def init_mcp_tools(config: Dict) -> List[Dict]:
    manager = MCPManager()
    return manager.init_config(config)


if __name__ == "__main__":
    @register_tool
    def calculate_area(length: float, width: float) -> float:
        """
        {
            "func": "Calculate the area of a rectangle",
            "params": {
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
            "func": "Get current weather information for a specific location",
            "params": {
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
            "func": "Generate a personalized greeting",
            "params": {
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
        print(f"- {tool['name']}: {tool['description']}")
    
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
    print(get_registered_tools())
    ans=["<function>"+str(tool)+"</function>" for tool in get_registered_tools()]
    print('\n'.join(ans))
    # ans=execute_tool("mcp_zhipu-web-search-sse_web_search",{"search_query":"what is the weather in beijing"})
    # print(ans)