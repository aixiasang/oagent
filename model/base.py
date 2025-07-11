import json
from .msg import Message
from typing import Any, Generator, Optional,Dict,Callable,Union,List
from openai import OpenAI
import concurrent.futures

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
class OpenaiLLM:
    def __init__(self,llm_config:Optional[Dict]=None):
        llm_config = llm_config or {}
        def get_config(cfg_name:str,default={}):
            return llm_config.get(cfg_name,default)
        self.client_cfg = get_config("client_cfg",{})
        self.generation_cfg = get_config("generation_cfg",{})
        self.embedding_cfg = get_config("embedding_cfg",{})
        def _chat(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.chat.completions.create(*args,**{**self.generation_cfg,**kwargs})
        def _embed(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.embeddings.create(*args,**{**self.embedding_cfg,**kwargs})
        def _completion(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.completions.create(*args,**{**self.generation_cfg,**kwargs})
        def _fn_chat(fn:Callable,model:Callable,*args,**kwargs):
            return fn(model(*args,**kwargs))
        def _img_gen(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.images.generate(*args,**kwargs)

        self._chat = _chat
        self._embed=_embed
        self._completion = _completion    
        self._fn_chat=_fn_chat  
        self._img_gen=_img_gen
    
    def simple_chat(self,messages:list[Message],**kwargs)-> Generator[Message, Any, None]:
        kwargs['messages']=[m.to_dict() for m in messages]
        def _stream_chat(resp):
            content=''
            reasoning_content=''
            for chunk in resp:
                id=chunk.id
                created=chunk.created
                delta=chunk.choices[0].delta
                if hasattr(delta,"content") and delta.content:
                    content+=delta.content
                    yield Message.bot(id,created,content=delta.content)
                if hasattr(delta,"reasoning_content") and delta.reasoning_content:
                    reasoning_content+=delta.reasoning_content
                    yield Message.bot(id,created,reasoning_content=delta.reasoning_content)
            messages.append(Message.bot(id,created,content=content,reasoning_content=reasoning_content))
        def _no_stream_chat(resp):
            msg=resp.choices[0].message
            id=resp.id
            created=resp.created
            if hasattr(msg, 'content') and msg.content:
                content=msg.content
            if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                reasoning_content=msg.reasoning_content
            yield Message.bot(id,created,content, reasoning_content)
            messages.append(Message.bot(id,created,content, reasoning_content))
        fn=_stream_chat if kwargs.get("stream",False) else _no_stream_chat
        return self._fn_chat(fn,self._chat,**kwargs)
    
    def chat(self,messages:list[Message],func_call:Callable=execute_func,parallel_tool_calls:bool=True,**kwargs):
        return self._base_chat(messages=messages,model=self._chat,func_call=func_call,parallel_tool_calls=parallel_tool_calls,**kwargs)
        
    def _base_chat(self,messages:list[Message],model:Callable,func_call:Callable=execute_func,parallel_tool_calls:bool=True,**kwargs)-> Generator[Message, Any, None]:
        kwargs['messages']=[m.to_dict() for m in messages]
        def _stream_chat(resp,func_call):
            content = ""
            reasoning_content = ""
            tool_calls = []
            has_tool_calls = False
            for chunk in resp:
                id = chunk.id
                created = chunk.created
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content += delta.content
                    yield Message.bot(id,created,content=delta.content)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
                    yield Message.bot(id,created,content="", reasoning_content=delta.reasoning_content)
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    has_tool_calls = True
                    for tool_call_delta in delta.tool_calls:
                        while len(tool_calls) <= tool_call_delta.index:
                            tool_calls.append({
                                "id": "",
                                "function": {"name": "", "arguments": ""}
                            })
                        current_tool_call = tool_calls[tool_call_delta.index]
                        if hasattr(tool_call_delta, 'id') and tool_call_delta.id:
                            current_tool_call["id"] = tool_call_delta.id
                        if hasattr(tool_call_delta, 'function') and tool_call_delta.function:
                            if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                                current_tool_call["function"]["name"] = tool_call_delta.function.name
                            if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                                current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments
            if has_tool_calls and tool_calls:
                msg=Message.tool_call_response(id,created,content,tool_calls)
                yield msg
                messages.append(msg)

                if parallel_tool_calls:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        future_to_tool_call = {executor.submit(func_call, tool_call): tool_call for tool_call in tool_calls}
                        for future in concurrent.futures.as_completed(future_to_tool_call):
                            tool_call = future_to_tool_call[future]
                            try:
                                result = future.result()
                                curr_msg = Message.tool_result(
                                    tool_call_id=tool_call['id'],
                                    content=str(result)
                                )
                                yield curr_msg
                                messages.append(curr_msg)
                            except Exception as exc:
                                curr_msg = Message.tool_result(
                                    tool_call_id=tool_call['id'],
                                    content=f'Error: {exc}'
                                )
                                yield curr_msg
                                messages.append(curr_msg)
                else:
                    # 顺序执行工具调用
                    for tool_call in tool_calls:
                        try:
                            result = func_call(tool_call)
                            tool_result_msg = Message.tool_result(
                                tool_call_id=tool_call['id'],
                                content=str(result)
                            )
                            yield tool_result_msg
                            messages.append(tool_result_msg)
                        except Exception as exc:
                            tool_result_msg = Message.tool_result(
                                tool_call_id=tool_call['id'],
                                content=f'Error: {exc}'
                            )
                            yield tool_result_msg
                            messages.append(tool_result_msg)
            else:
                msg=Message.bot(
                    id,
                    created,
                    content=content,
                    reasoning_content=reasoning_content,
                )
                messages.append(msg)

        def _no_stream_chat(resp,func_call):
            id=resp.id
            created=resp.created
            resp_msg =resp.choices[0].message
            content=resp_msg.content
            reasoning_content=getattr(resp_msg, 'reasoning_content', "") or ""
            func_call_flag=resp.choices[0].finish_reason =="tool_calls"
            if not func_call_flag:
                curr_msg=Message.bot(
                    id,created,
                    content=content,
                    reasoning_content=reasoning_content,
                )
                yield curr_msg
                messages.append(curr_msg)
            else:
                meta_data=resp.choices[0].message.model_dump()
                msg = Message.bot(
                    id,
                    created,
                    **meta_data
                )
                yield msg
                messages.append(msg)
                tool_calls = resp_msg.tool_calls
                
                # 根据参数决定是否使用并发调用
                if parallel_tool_calls:
                    # 并发执行工具调用
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        future_to_tool_call = {executor.submit(func_call, tool_call): tool_call for tool_call in tool_calls}
                        for future in concurrent.futures.as_completed(future_to_tool_call):
                            tool_call = future_to_tool_call[future]
                            try:
                                result = future.result()
                                curr_msg = Message.tool_result(
                                    tool_call_id=tool_call.id,
                                    content=str(result)
                                )
                                yield curr_msg
                                messages.append(curr_msg)
                            except Exception as exc:
                                curr_msg = Message.tool_result(
                                    tool_call_id=tool_call.id,
                                    content=f'Error: {exc}'
                                )
                                yield curr_msg
                                messages.append(curr_msg)
                else:
                    # 顺序执行工具调用
                    for tool_call in tool_calls:
                        try:
                            result_content = func_call(tool_call)
                            curr_msg = Message.tool_result(
                                tool_call_id=tool_call.id,
                                content=str(result_content)
                            )
                            yield curr_msg
                            messages.append(curr_msg)
                        except Exception as exc:
                            curr_msg = Message.tool_result(
                                tool_call_id=tool_call.id,
                                content=f'Error: {exc}'
                            )
                            yield curr_msg
                            messages.append(curr_msg)
                
        fn = (lambda resp: _stream_chat(resp, func_call)) if kwargs.get("stream", False) else (lambda resp: _no_stream_chat(resp, func_call))
        return self._fn_chat(fn,model,**kwargs)

    def embed(self,*args,**kwargs):
        return self._embed(*args,**kwargs)
    
    def completion(self,text:str,**kwargs):
        return self._completion(prompt=text,**kwargs)
    
    def fn_chat(self,fn:Callable,*args,**kwargs):
        return self._fn_chat(fn,self._chat,*args,**kwargs)

    def img_gen(self,*args,**kwargs):
        return self._img_gen(*args,**kwargs)
if __name__ == "__main__":
    from config import get_siliconflow_model
    openai_llm=OpenaiLLM(get_siliconflow_model())
    msgs=[
        Message.system("你是一个助手"),
        Message.user("查看一下天气？北京的上海的和西安(xian)的")
    ]
    from tools import get_weather,get_registered_tools
    tools=get_registered_tools()
    for msg in openai_llm.chat(messages=msgs,tools=tools,tool_choice='auto',stream=True):
        if msg.reasoning_content:
            print(msg.reasoning_content,end="",flush=True)
        if msg.content:
            print(msg.content,end="",flush=True)
    
    print("-------------------")
    # print(msgs)
    for msg in msgs:
        print(msg)
    # fn=lambda x:print(x)
    # fn(12)
    # openai_llm.fn_chat(
    #     fn=fn,
    #     messages=[i.to_dict() for i in msg]
    # )