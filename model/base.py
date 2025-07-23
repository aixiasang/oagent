from .msg import Message,Messages
from typing import Any, Generator, Optional,Dict,Callable,Union,List
from abc import ABC, abstractmethod
class BaseLLM(ABC):
    def __init__(self,*args,**kwargs):
        pass
    @abstractmethod
    def chat(self,messages:Messages,**kwargs)-> Generator[Message, Any, None]:
        pass
    @abstractmethod
    def schat(self,messages:Messages,parallel_tool_calls:bool=True,**kwargs):
        pass
    @abstractmethod
    def embed(self,*args,**kwargs):
        pass
    @abstractmethod
    def completion(self,text:str,**kwargs):
        pass
    @abstractmethod
    def fn_chat(self,fn:Callable,*args,**kwargs):
        pass
    @abstractmethod
    def img_gen(self,*args,**kwargs):
        pass