"""
llm_config:
    api_key =os.getenv("ARK_API_KEY")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model ="doubao-1-5-thinking-pro-m-250428"
    embedding_model="doubao-embedding-large-text-250515"

    llm_config={
        "client_cfg": {
            "api_key": api_key,
            "base_url": base_url,
        },
        "generation_cfg": {
            "model": model,
            "max_tokens": 4096,
            "top_p": 0.7,
            "temperature": 0.9,
        },
        'embedding_cfg':{
            "model": embedding_model,
            # input=inputs,
            "encoding_format":"float",

        }
    }
"""
from typing import Optional,Dict,List,Callable
from .msg import Message
class BaseModel:
    def __init__(self,llm_config:Optional[Dict]=None):
        def get_config(cfg_name:str,default={}):
            return llm_config.get(cfg_name,default)
        llm_config = llm_config or {}
        client_cfg = get_config("client_cfg",{})
        generation_cfg = get_config("generation_cfg",{})
        embedding_cfg = get_config("embedding_cfg",{})

        def _chat(*args,**kwargs):
            pass
        def _embed(*args,**kwargs):
            pass
        def _completion(*args,**kwargs):
            pass

        self._chat = _chat
        self._embed=_embed
        self._completion = _completion

    def chat(self,fn:Callable,*args,**kwargs):
        return fn(self._chat,*args,**kwargs)
    
    def embed(self,fn:Callable,*args,**kwargs):
        return fn(self._embed,*args,**kwargs)
    
    def completion(self,fn:Callable,*args,**kwargs):
        return fn(self._completion,*args,**kwargs)

