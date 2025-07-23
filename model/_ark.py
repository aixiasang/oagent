"""
Ark LLM 模型的实现
实现了Ark的聊天、嵌入、多模态嵌入、机器人聊天、图像生成等功能
"""
from typing import Callable, Dict, List, Union
from .base import OpenaiLLM,execute_func
from .msg import Message
from volcenginesdkarkruntime import Ark
class ArkLLM(OpenaiLLM):
    def __init__(self, llm_config: Dict | None = None):
        super().__init__(llm_config)
        def _chat(*args,**kwargs):
            client=Ark(**self.client_cfg)
            return client.chat.completions.create(*args,**{**self.generation_cfg,**kwargs})
        def _embed(*args,**kwargs):
            client=Ark(**self.client_cfg)
            return client.embeddings.create(*args,**{**self.embedding_cfg,**kwargs})
        def _multi_embed(*args,**kwargs):
            client=Ark(**self.client_cfg)
            return client.multimodal_embeddings.create(*args,**kwargs)
        def _bot_chat(*args,**kwargs):
            client=Ark(**self.client_cfg)
            return client.bot_chat.completions.create(*args,**kwargs)
        def _img_gen(*args,**kwargs):
            client=Ark(**self.client_cfg)
            return client.images.generate(*args,**kwargs)
        self._chat = _chat
        self._embed=_embed
        self._multi_embed=_multi_embed
        self._bot_chat=_bot_chat
        self._img_gen=_img_gen
        
    def embed(self, *args,**kwargs):
        """
        https://www.volcengine.com/docs/82379/1521766
        """
        return self._embed(*args,**kwargs)
    
    def multi_embed(self,*args,**kwargs):
        """
        https://www.volcengine.com/docs/82379/1523520
        """
        return self._multi_embed(*args,**kwargs)
    
    def bot_chat(self,messages:list[Message],func_call:Callable=execute_func,**kwargs   ):
        """
        这部分存在瑕疵需要来进行优化
        https://www.volcengine.com/docs/82379/1526787
        """
        return self._chat(messages=messages,model=self._bot_chat,func_call=func_call,**kwargs)

    def img_gen(self,*args,**kwargs):
        """
        https://www.volcengine.com/docs/82379/1541523
        """
        return self._img_gen(*args,**kwargs)
    

if __name__ == "__main__":
    import os
    from .msg import Message
    api_key =os.getenv("ARK_API_KEY")
    model ="doubao-1-5-thinking-pro-m-250428"
    embedding_model="doubao-embedding-large-text-250515"

    llm_config={
        "client_cfg": {
            "api_key": api_key,
            # "base_url": base_url,
        },
        "generation_cfg": {
            "model": model,
            "max_tokens": 4096,
            "top_p": 0.3,
            "temperature": 0.2,
        },
    }
    llm=ArkLLM(llm_config)
    msgs=[
        Message.system("你是一个助手"),
        Message.user("查看一下天气？北京的上海的和西安(xian)的")
    ]
    from tools import get_weather,get_registered_tools
    tools=get_registered_tools()
    for msg in llm.chat(messages=msgs,tools=tools,tool_choice='auto',stream=True):
        if msg.reasoning_content:
            print(msg.reasoning_content,end="",flush=True)
        if msg.content:
            print(msg.content,end="",flush=True)