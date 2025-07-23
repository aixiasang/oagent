"""
实现对于函数调用的执行
支持并行和非并行执行
"""
import json
from typing import Callable, Dict, List,  Union,Any,Generator
from .msg import Message
import concurrent
MAX_WORKERS=5
def execute_func(tool_call):
    tool_result=None
    try:
        from tools import execute_tool
        tool_name = tool_call['function']['name']
        args = json.loads(tool_call['function']['arguments'])
        tool_result = execute_tool(tool_name, args)
    except  Exception as e:
        tool_result=f"error:{e}"
    return str(tool_result)

def _parallel_func_call(tool_calls: List[Dict[str, Union[str, Dict]]], func_call: Callable[[Dict[str, Union[str, Dict]]], Any]) -> Generator[Message, None, None]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_tool_call = {executor.submit(func_call, tool_call): tool_call for tool_call in tool_calls}
        for future in concurrent.futures.as_completed(future_to_tool_call):
            tool_call = future_to_tool_call[future]
            try:
                result = future.result()
                print(f"Tool call {tool_call} result: {result}")
                curr_msg = Message.tool_result(
                    tool_call_id=tool_call['id'],
                    content=str(result)
                )
                yield curr_msg
            except Exception as exc:
                curr_msg = Message.tool_result(
                    tool_call_id=tool_call['id'],
                    content=f'Error: {exc}'
                )
                yield curr_msg

def _normal_func_call(tool_calls: List[Dict[str, Union[str, Dict]]], func_call: Callable[[Dict[str, Union[str, Dict]]], Any]) -> Generator[Message, None, None]:
    for tool_call in tool_calls:
        try:
            result_content = func_call(tool_call)
            curr_msg = Message.tool_result(
                tool_call_id=tool_call.id,
                content=str(result_content)
            )
            yield curr_msg
        except Exception as exc:
            curr_msg = Message.tool_result(
                tool_call_id=tool_call.id,
                content=f'Error: {exc}'
            )
            yield curr_msg

def func_call(tool_calls: List[Dict[str, Union[str, Dict]]], func_call: Callable[[Dict[str, Union[str, Dict]]], Any]=execute_func, parallel: bool = True) -> Generator[Message, None, None]:
    if parallel:
        return _parallel_func_call(tool_calls, func_call)
    else:
        return _normal_func_call(tool_calls, func_call)