import asyncio
import threading
import uuid
import atexit
import time
import logging
import inspect
from contextlib import AsyncExitStack
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

registered_tools = {}

def register_tool(name=None, description=None, allow_overwrite=False):
    """工具注册装饰器
    
    用于将函数注册为可供LLM调用的工具。从函数的文档字符串中提取参数信息。
    支持在文档字符串中使用简单JSON格式定义参数详情：
    
    {
        "func": "函数描述",
        "params": {
            "参数1": "参数1的描述",
            "参数2": "参数2的描述"
        }
    }
    
    Args:
        name: 工具名称，如果不提供则使用函数名
        description: 工具描述，如果不提供则使用函数的文档字符串
        allow_overwrite: 是否允许覆盖已注册的同名工具，默认为False
    """
    def decorator(func):
        nonlocal name, description
        original_name = name or func.__name__
        
        docstring = func.__doc__ or ""
        tool_description = description or docstring.strip() or f"Function {original_name}"
        
        import re
        import json
        json_match = re.search(r'\{.*\}', docstring, re.DOTALL)
        custom_params = {}
        
        if json_match:
            try:
                json_def = json.loads(json_match.group())
                if "func" in json_def and not description:
                    tool_description = json_def["func"]
                
                if "params" in json_def:
                    custom_params = json_def["params"]
            except json.JSONDecodeError:
                pass 

        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)
            
            param_type = "string"  # default type
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_type = "string"
                elif param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list or param.annotation == List:
                    param_type = "array"
                elif param.annotation == dict or param.annotation == Dict:
                    param_type = "object"
            
            param_description = custom_params.get(param_name, f"Parameter {param_name}")
            parameters["properties"][param_name] = {
                "type": param_type,
                "description": param_description
            }
        
        
        names_to_register = []
        
        if not original_name.startswith("mcp_"):
            names_to_register.append(original_name)
        
        local_name = f"local_{original_name}"
        if not local_name.startswith("mcp_") and not original_name.startswith("local_"):
            names_to_register.append(local_name)
        
        for tool_name in names_to_register:
            if tool_name in registered_tools and not allow_overwrite:
                logger.warning(f"工具 '{tool_name}' 已注册，由于allow_overwrite=False，忽略此次注册")
                continue
                
            tool_definition = {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters
            }
            
            if tool_name in registered_tools and allow_overwrite:
                logger.info(f"工具 '{tool_name}' 已存在，正在覆盖")
                
            registered_tools[tool_name] = {
                "definition": tool_definition,
                "function": func
            }
        
        return func
    
    return decorator

def get_registered_tools() -> List[Dict]:
    return [tool["definition"] for tool in registered_tools.values()]

def execute_tool(tool_name: str, **kwargs) -> Any:
    """执行指定名称的工具函数
    
    支持以下工具类型：
    1. 本地工具（以local_开头）
    2. MCP工具（通常包含mcp_前缀）
    3. 常规工具（无特殊前缀）
    
    Args:
        tool_name: 工具名称
        **kwargs: 传递给工具函数的参数
        
    Returns:
        工具函数的执行结果
    """
    original_tool_name = tool_name
    
    if tool_name in registered_tools:
        pass
    elif tool_name.startswith("local_"):
        base_name = tool_name[6:]  
        if base_name in registered_tools:
            logger.info(f"将 '{tool_name}' 重定向到 '{base_name}'")
            tool_name = base_name
        else:
            raise ValueError(f"未找到名为 '{tool_name}' 或 '{base_name}' 的工具")
    else:
        local_name = f"local_{tool_name}"
        if local_name in registered_tools:
            logger.info(f"将 '{tool_name}' 重定向到 '{local_name}'")
            tool_name = local_name
        else:
            possible_tools = [t for t in registered_tools.keys() if t.endswith(tool_name) or tool_name.endswith(t)]
            if possible_tools:
                tool_name = possible_tools[0]
                logger.info(f"找到可能的工具匹配，将 '{original_tool_name}' 重定向到 '{tool_name}'")
            else:
                raise ValueError(f"未找到名为 '{tool_name}' 的工具。可用的工具: {list(registered_tools.keys())}")
    
    tool_func = registered_tools[tool_name]["function"]
    return tool_func(**kwargs)


class MCPManager:
    _instance = None  

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'clients'):
            try:
                import mcp
            except ImportError as e:
                raise ImportError('Failed to import mcp module. Please install mcp with `pip install -U mcp`.') from e

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
                'LLM system requires a patch for MCP process cleanup. Please upgrade MCP with `pip install -U mcp`.'
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

    def initConfig(self, config: Dict):
        if not self.is_valid_mcp_servers(config):
            raise ValueError('Invalid MCP server config')
        logger.info(f'Initializing MCP tools from servers: {list(config["mcpServers"].keys())}')
        future = asyncio.run_coroutine_threadsafe(self.init_config_async(config), self.loop)
        try:
            result = future.result() 
            return result
        except Exception as e:
            logger.info(f'Failed to initialize MCP tools: {e}')
            raise e

    async def init_config_async(self, config: Dict):
        tools: list = []
        mcp_servers = config['mcpServers']
        for server_name in mcp_servers:
            client = MCPClient()
            server = mcp_servers[server_name]
            await client.connection_server(mcp_server_name=server_name, mcp_server=server)  

            client_id = server_name + '_' + str(uuid.uuid4())  
            self.clients[client_id] = client  
            for tool in client.tools:   
                parameters = tool.inputSchema
                if 'required' not in parameters:
                    parameters['required'] = []
                required_fields = {'type', 'properties', 'required'}
                missing_fields = required_fields - parameters.keys()
                if missing_fields:
                    raise ValueError(f'Missing required fields in schema: {missing_fields}')

                cleaned_parameters = {
                    'type': parameters['type'],
                    'properties': parameters['properties'],
                    'required': parameters['required']
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
                            logger.info(f'Failed to execute MCP tool: {e}')
                            raise e
                    return tool_func
                
                registered_tools[register_name] = {
                    "definition": tool_definition,
                    "function": create_tool_func(client_id, tool.name)
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
        
        if asyncio.all_tasks(self.loop):
            logger.info('There are still tasks in `MCPManager().loop`, forcibly terminating MCP tool processes. Some exceptions may occur.')
            for process in self.processes:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass  
        
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join()


class MCPClient:

    def __init__(self):
        try:
            from mcp import ClientSession
        except ImportError as e:
            raise ImportError('无法导入mcp模块。请使用`pip install -U mcp`安装mcp。') from e

        self.session = None
        self.tools = None
        self.exit_stack = AsyncExitStack()

    async def connection_server(self, mcp_server_name, mcp_server):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.client.sse import sse_client
            
            if 'url' in mcp_server:
                self._streams_context = sse_client(
                    url=mcp_server.get('url'), 
                    headers=mcp_server.get('headers', {"Accept": "text/event-stream"})
                )
                streams = await self.exit_stack.enter_async_context(self._streams_context)
                self._session_context = ClientSession(*streams)
                self.session = await self.exit_stack.enter_async_context(self._session_context)
            else:
                server_params = StdioServerParameters(
                    command=mcp_server["command"],
                    args=mcp_server["args"],
                    env=mcp_server.get("env", None)
                )
                stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                self.stdio, self.write = stdio_transport
                self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
                logger.info(f'正在初始化MCP stdio_client，如果一直无响应，请检查该MCP服务器的配置: {mcp_server_name}')

            await self.session.initialize()
            list_tools = await self.session.list_tools()
            self.tools = list_tools.tools
        except Exception as e:
            logger.info(f"连接到MCP服务器失败: {e}")
            raise e

    async def execute_function(self, tool_name, tool_args: dict):
        response = await self.session.call_tool(tool_name, tool_args)   # type: ignore
        texts = []
        for content in response.content:
            if content.type == 'text':
                texts.append(content.text)
        if texts:
            return '\n\n'.join(texts)
        else:
            return 'execute error'

    async def cleanup(self):
        await self.exit_stack.aclose()


def _cleanup_mcp(_sig_num=None, _frame=None):
    if MCPManager._instance is None:
        return
    manager = MCPManager()
    manager.shutdown()


if threading.current_thread() is threading.main_thread():
    atexit.register(_cleanup_mcp)


def init_mcp_tools(config: Dict) -> List[Dict]:
    manager = MCPManager()
    return manager.initConfig(config)


def list_registered_tools():
    return {
        "total_tools": len(registered_tools),
        "tool_names": list(registered_tools.keys()),
        "local_tools": [name for name in registered_tools.keys() if name.startswith("local_")],
        "mcp_tools": [name for name in registered_tools.keys() if name.startswith("mcp_")],
        "regular_tools": [name for name in registered_tools.keys() 
                         if not name.startswith("local_") and not name.startswith("mcp_")]
    }
if __name__=="__main__":
    print(list_registered_tools())