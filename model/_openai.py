"""
Openai LLM 模型的实现
实现了OpenAI的聊天、嵌入、文本生成等功能
"""
import numpy as np
import requests
from .msg import Message,Messages
from typing import Any, Generator, Optional,Dict,Callable,Union,List
from openai import OpenAI
from .base import BaseLLM


class OpenaiLLM(BaseLLM):
    def __init__(self,llm_config:Optional[Dict]=None):
        super().__init__(llm_config)
        llm_config = llm_config or {}
        self.client_cfg = llm_config.get('client_cfg', {})
        self.chat_cfg = llm_config.get('chat_cfg', {})
        self.completion_cfg = llm_config.get('completion_cfg', {})
        self.embedding_cfg = llm_config.get('embedding_cfg', {})
        self.rerank_cfg = llm_config.get('rerank_cfg', {})
        def _chat(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.chat.completions.create(*args,**{**self.chat_cfg,**kwargs})
        def _embed(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.embeddings.create(*args,**{**self.embedding_cfg,**kwargs})
        def _multi_embed(*args,**kwargs):
            raise NotImplemented
        def _completion(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.completions.create(*args,**{**self.completion_cfg,**kwargs})
        def _fn_chat(fn:Callable,model_fn:Callable,*args,**kwargs):
            return fn(model_fn(*args,**kwargs))
        def _img_gen(*args,**kwargs):
            client=OpenAI(**self.client_cfg)
            return client.images.generate(*args,**kwargs)
        def _rerank(*args,**kwargs):
            from ._request_llm import _base_requst
            data={
                **self.rerank_cfg,
                **kwargs,
            }
            return _base_requst(self.client_cfg,suffix='/rerank',request_data=data)
        self._chat = _chat
        self._embed=_embed
        self._mutil_embed=_multi_embed
        self._completion = _completion    
        self._fn_chat=_fn_chat  
        self._img_gen=_img_gen
        self._rerank=_rerank
    
    def chat(self,messages:Messages,**kwargs)-> Generator[Message, Any, None]:
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
                    yield Message.assistant(id,created,content=delta.content)
                if hasattr(delta,"reasoning_content") and delta.reasoning_content:
                    reasoning_content+=delta.reasoning_content
                    yield Message.assistant(id,created,reasoning_content=delta.reasoning_content)
            # 实现消息的追加
            messages.append(Message.assistant(id,created,content=content,reasoning_content=reasoning_content))
        def _no_stream_chat(resp):
            msg=resp.choices[0].message
            id=resp.id
            created=resp.created
            content=''
            reasoning_content=''
            if hasattr(msg, 'content') and msg.content:
                content=msg.content
            if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                reasoning_content=msg.reasoning_content
            yield Message.assistant(id,created,content, reasoning_content)
            # 实现消息的追加
            messages.append(Message.assistant(id,created,content, reasoning_content))
        fn=_stream_chat if kwargs.get("stream",False) else _no_stream_chat

        return self._fn_chat(fn,self._chat,**kwargs)
    
    def schat(self,messages:list[Message],parallel_tool_calls:bool=True,**kwargs):
        return self._base_chat(messages=messages,model=self._chat,parallel_tool_calls=parallel_tool_calls,**kwargs)
        
    def _base_chat(self,messages:list[Message],model:Callable,parallel_tool_calls:bool=True,**kwargs)-> Generator[Message, Any, None]:
        kwargs['messages']=[m.to_dict() for m in messages]
        def _stream_chat(resp):
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
                    yield Message.assistant(id,created,content=delta.content)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
                    yield Message.assistant(id,created,content="", reasoning_content=delta.reasoning_content)
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
                # 添加对于函数调用的需求
                msg=Message.tool_call_response(id,created,content,tool_calls)
                yield msg
                messages.append(msg)

                # 进行函数调用的执行
                from .func import func_call
                tool_results = func_call(tool_calls, parallel=parallel_tool_calls)
                for tool_result in tool_results:
                    yield tool_result
                    messages.append(tool_result)
            else:
                # 如果没有函数调用的需求 直接添加msg信息即可
                msg=Message.assistant(
                    id,
                    created,
                    content=content,
                    reasoning_content=reasoning_content,
                )
                messages.append(msg)

        def _no_stream_chat(resp):
            id=resp.id
            created=resp.created
            resp_msg =resp.choices[0].message
            content=resp_msg.content
            reasoning_content=getattr(resp_msg, 'reasoning_content', "") or ""
            func_call_flag=resp.choices[0].finish_reason =="tool_calls"
            if not func_call_flag:
                # 如果没有函数调用的需求 直接添加msg信息即可
                curr_msg=Message.assistant(
                    id,created,
                    content=content,
                    reasoning_content=reasoning_content,
                )
                yield curr_msg
                messages.append(curr_msg)
            else:
                # 存在函数调用的需求 直接添加函数调用需求 并且 返回函数调用的结果
                meta_data=resp.choices[0].message.model_dump()
                tools_calls = meta_data.get('tool_calls', None)
                msg = Message.assistant(
                    id,
                    created,
                    content=meta_data['content'],
                    reasoning_content=meta_data.get('reasoning_content', None),
                    tool_calls=tools_calls
                )
                yield msg
                messages.append(msg)
                
                # 进行函数调用的实现
                from .func import func_call
                tool_results= func_call(tools_calls, parallel=parallel_tool_calls)
                for tool_result in tool_results:
                    yield tool_result
                    messages.append(tool_result)
        fn = (lambda resp: _stream_chat(resp)) if kwargs.get("stream", False) else (lambda resp: _no_stream_chat(resp))
        return self._fn_chat(fn,model,**kwargs)

    def embed(self,text:Union[str,list[str]],**kwargs):
        text=text if isinstance(text,list) else [text]
        resp=self._embed(input=text)
        return np.array([data.embedding for data in resp.data])
    
    def completion(self,text:str,**kwargs):
        return self._completion(prompt=text,**kwargs)
    
    def fn_chat(self,fn:Callable,*args,**kwargs):
        return self._fn_chat(fn,self._chat,*args,**kwargs)

    def img_gen(self,*args,**kwargs):
        return self._img_gen(*args,**kwargs)

    def rerank(self, query: str, documents: List[str],top_k=3) -> List[Dict[str, Union[int, float, str]]]:
        results:List[Dict]=self._rerank(
            query=query,
            documents=documents,
        ).get('results')
        top_results=sorted(results,key=lambda x:x['relevance_score'],reverse=1)[:top_k]
        return [{"text":documents[result['index']],'score':result['relevance_score']} for result in top_results]
if __name__ == "__main__":
    from config import get_siliconflow_model
    import os
    llm_cfg=get_siliconflow_model()
    llm_cfg['rerank_cfg']['model']='BAAI/bge-reranker-v2-m3'
    openai_llm=OpenaiLLM(llm_cfg)

    
    query="Apple"
    documents= [
            "apple",
            "banana",
            "fruit",
            "vegetable"
        ]
    api_key=os.getenv("siliconflow_api_key")
    base_url='https://api.siliconflow.cn/v1'
    model="Qwen/Qwen3-32B"#'moonshotai/Kimi-K2-Instruct'
    embedding_model="Qwen/Qwen3-Embedding-8B"
    result=openai_llm.rerank(query=query,documents=documents)
    print(result)
    # msgs=[
    #     Message.system("你是一个助手"),
    #     # Message.user("查看一下天气？北京的上海的和西安(xian)的")
    # ]
    # msgs=Messages(system_prompt="你是一个助手")
    # from tools import get_weather,get_registered_tools
    # tools=get_registered_tools()
    # # for msg in openai_llm.chat(messages=msgs,stream=True):
    # #     if msg.reasoning_content:
    # #         print(msg.reasoning_content,end="",flush=True)
    # #     if msg.content:
    # #         print(msg.content,end="",flush=True)
    # while True:
    #     user_input = input("User: ")
    #     if user_input.lower() == 'q':
    #         break
    #     msgs.append(Message.user(user_input))
    #     print("Assistant: ", end="", flush=True)
    #     while True:
    #         for msg in openai_llm.schat(messages=msgs,stream=False,tools=tools,tool_choice='auto'):
    #             if msg.reasoning_content:
    #                 print(msg.reasoning_content,end="",flush=True)
    #             if msg.content:
    #                 print(msg.content,end="",flush=True)
    #         if not msgs.check_tool_result():
    #             break
    #     print("-------------------")
    # for msg in msgs:
    #     print(msg)
    # fn=lambda x:print(x)
    # fn(12)
    # openai_llm.fn_chat(
    #     fn=fn,
    #     messages=[i.to_dict() for i in msg]
    # )