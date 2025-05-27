import os
from openai import OpenAI
from sympy import im

api_key = os.getenv("ARK_API_KEY")
base_url = "https://ark.cn-beijing.volces.com/api/v3"
model = "deepseek-v3-250324"
llm_config={
    "client_cfg": {
        "api_key": api_key,
        "base_url": base_url,
    },
    "generation_cfg": {
        "model": model,
        "temperature": 0.4,
        "max_tokens": 2048,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
}
from typing import Dict,List,Optional,Union
from .tools import execute_tool
class Message:
    @staticmethod
    def user(content:  Union[str, Dict, List]) -> Dict[str, str]:
        return {"role": "user", "content": content}
    @staticmethod
    def bot(content: Union[str, Dict, List]) -> Dict[str, str]:
        return {"role": "assistant", "content": content}
    @staticmethod
    def system(content:  Union[str, Dict, List]) -> Dict[str, str]:
        return {"role": "system", "content": content}
    @staticmethod
    def tool_call(tool_id: str, name: str, arguments: str) -> Dict:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": arguments
                }
            }]
        }
    @staticmethod
    def tool_result(tool_call_id: str, content: str) -> Dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }
    
class LLM:
    def __init__(self, llm_config:Dict):
        client_cfg = llm_config.get("client_cfg", {})
        self.generation_cfg = llm_config.get("generation_cfg", {})
        def _chat(*args, **kwargs):
            client = OpenAI(**client_cfg)
            return client.chat.completions.create(*args,**{**self.generation_cfg, **kwargs})
        self._chat = _chat
    
    def chat(self,message:List[Dict], stream=True, **kwargs):
        return self._chat(messages=message,stream=stream, **{**self.generation_cfg, **kwargs})
    
    def process_tool_calls(self, response, add_to_messages=None):

        if not hasattr(response.choices[0].message, 'tool_calls') or not response.choices[0].message.tool_calls:
            return None
            
        results = []
        for tool_call in response.choices[0].message.tool_calls:
            function_name = tool_call.function.name
            function_args = eval(tool_call.function.arguments)
            
            try:
                function_result = execute_tool(function_name, **function_args)
                results.append({
                    "tool_call_id": tool_call.id,
                    "function_name": function_name,
                    "result": function_result
                })
                
                if add_to_messages is not None:
                    add_to_messages.append(
                        Message.tool_call(
                            tool_id=tool_call.id,
                            name=function_name,
                            arguments=tool_call.function.arguments
                        )
                    )
                    
                    add_to_messages.append(
                        Message.tool_result(
                            tool_call_id=tool_call.id,
                            content=str(function_result)
                        )
                    )
            except Exception as e:
                print(f"Error executing tool {function_name}: {e}")
                    
        return results

    def chat_with_tools(self, messages, tools):
        
        formatted_tools = [{"type": "function", "function": f} for f in tools]
        response = self._chat(
            messages=messages,
            tools=formatted_tools,
            stream=False
        )
        
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            tool_results = self.process_tool_calls(response,messages)
            print("tool_results:", tool_results)
            
            content_chunks = []
            
            for chunk in self._chat(messages=messages, stream=True):
                if hasattr(chunk.choices[0], 'delta') and chunk.choices[0].delta.content:
                    content_chunks.append(chunk.choices[0].delta.content)
                yield chunk

                
            final_content = "".join(content_chunks)
            messages.append(Message.bot(final_content))
        else:
            yield response
            
            if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
                messages.clear()
                messages.append(Message.bot(response.choices[0].message.content))

    def chat_with_tools_stream(self, messages, tools):
        formatted_tools = [{"type": "function", "function": f} for f in tools]
        accumulated_chunks = []
        accumulated_tool_calls = []
        current_tool_call = None
        
        response = self._chat(
            messages=messages,
            tools=formatted_tools,
            stream=True
        )
        
        for chunk in response:
            if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'tool_calls'):
                delta_tool_calls = chunk.choices[0].delta.tool_calls
                
                if delta_tool_calls and delta_tool_calls[0].index is not None:
                    idx = delta_tool_calls[0].index
                    if idx >= len(accumulated_tool_calls):
                        accumulated_tool_calls.append({
                            "id": delta_tool_calls[0].id or "",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        })
                    current_tool_call = accumulated_tool_calls[idx]
                
                if delta_tool_calls and delta_tool_calls[0].id:
                    current_tool_call["id"] = delta_tool_calls[0].id
                
                if delta_tool_calls and hasattr(delta_tool_calls[0], 'function') and delta_tool_calls[0].function.name:
                    current_tool_call["function"]["name"] = delta_tool_calls[0].function.name
                
                if delta_tool_calls and hasattr(delta_tool_calls[0], 'function') and delta_tool_calls[0].function.arguments:
                    current_tool_call["function"]["arguments"] += delta_tool_calls[0].function.arguments
            
            elif hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                accumulated_chunks.append(chunk.choices[0].delta.content)
            
            if chunk.choices[0].finish_reason == "tool_calls" and accumulated_tool_calls:
                for tool_call in accumulated_tool_calls:
                    function_name = tool_call["function"]["name"]
                    try:
                        function_args = eval(tool_call["function"]["arguments"])
                        
                        messages.append(
                            Message.tool_call(
                                tool_id=tool_call["id"],
                                name=function_name,
                                arguments=tool_call["function"]["arguments"]
                            )
                        )
                        
                        function_result = execute_tool(function_name, **function_args)
                        
                        messages.append(
                            Message.tool_result(
                                tool_call_id=tool_call["id"],
                                content=str(function_result)
                            )
                        )
                        
                        print(f"Tool call: {function_name} with args {function_args}")
                        print(f"Tool result: {function_result}")
                    except Exception as e:
                        print(f"Error executing tool {function_name}: {e}")
                
                second_response = self._chat(messages=messages, stream=True)
                for second_chunk in second_response:
                    if hasattr(second_chunk.choices[0], 'delta') and second_chunk.choices[0].delta.content:
                        yield second_chunk
                
                final_content = "".join(accumulated_chunks)
                if final_content:
                    messages.append(Message.bot(final_content))
                return
            
            yield chunk
        
        final_content = "".join(accumulated_chunks)
        if final_content:
            messages.append(Message.bot(final_content))

if __name__ == "__main__":
    llm = LLM(llm_config)
    print("\n--- 函数调用示例 ---")
    
    # 加载系统提示和工具
    from prompts.role_play import default_role_paly
    messages = [Message.system(default_role_paly())]
    
    # 初始化工具
    from .tools import get_registered_tools, init_mcp_tools
    import json
    try:
        with open("utils/mcp.json", "r") as f:
            mcp_js = json.load(f)
        init_mcp_tools(mcp_js)
    except Exception as e:
        print(f"初始化MCP工具失败: {e}")
    
    # 获取所有可用工具
    tools = get_registered_tools()
    print(f"已加载 {len(tools)} 个工具")
    
    # 交互式对话循环
    while True:
        user_input = input("\nuser> ")
        if user_input.lower() in ["q", "quit", "exit"]:
            break
        
        # 添加用户消息
        messages.append(Message.user(user_input))
        
        # 使用流式工具调用进行回复
        print("ai> ", end="", flush=True)
        for chunk in llm.chat_with_tools_stream(messages, tools):
            if hasattr(chunk.choices[0], 'delta'):
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="", flush=True)
        print()  # 换行
  