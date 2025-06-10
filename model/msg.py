from dataclasses import dataclass
from datetime import datetime
import json
from typing import Union,Dict,List,Optional,Any

@dataclass
class Message:
    role:str
    time:datetime=datetime.now()
    content:Optional[Union[str, Dict, List]]=None
    reasoning_content:Optional[Union[str, Dict, List]]=None
    tool_call_id: Optional[str] = None
    tool_calls:Optional[List[Dict]]=None
    refusal:str=None
    annotations:str=None
    audio:str=None
    function_call:Any=None
    @staticmethod
    def system(content:str):
        msg={
            "role":"system",
            "content":content
        }
        return  Message(**msg)
    @staticmethod
    def user(content:Optional[Union[str, Dict, List]]):
        msg={
            "role":"user",
            "content":content
        }
        return  Message(**msg)
    
    @staticmethod
    def bot(content:Optional[Union[str, Dict, List]]=None,reasoning_content:Optional[Union[str, Dict, List]]=None,**kwargs):
        msg={
            "role":"assistant",
        }
        if content:
            msg["content"]=content
        if reasoning_content:
            msg["reasoning_content"]=reasoning_content
        return  Message(**{**msg,**kwargs})
    
    @staticmethod
    def tool_call_response(content,tool_calls:List[Dict]):
        msg={
            "role":"assistant",
            "content":content,
            'tool_calls':[
                    {
                        'id': call['id'],
                        'type': 'function',
                        'function': {
                            'name': call['function']['name'],
                            'arguments': call['function']['arguments']
                        }
                    } for call in tool_calls
            ]
        }
        return  Message(**msg)
    @staticmethod
    def tool(content:Optional[Union[str, Dict, List]]=None,tool_call_id:Optional[str]=None):
        msg={
            "role":"tool",
            "content":content,
            "tool_call_id":tool_call_id
        }
        return  Message(**msg)
    @staticmethod
    def tool_result(tool_call_id:str,content:Optional[Union[str, Dict, List]]):
        msg={
            "role":"tool",
            "tool_call_id":tool_call_id,
            "content":content
        }
        return  Message(**msg)
    @staticmethod
    def check_tool_result(message:'Message'):
        return message.role=="tool" and message.tool_call_id and message.content
    def to_dict(self):
        required_fields=['role','content',"tool_call_id","tool_calls","refusal","annotations","audio","function_call"]
        msg={}
        for field in required_fields:
            val=getattr(self,field,None)
            if val:
                msg[field]=val
        return msg
    
    def __repr__(self):
        data = self.to_dict()
        return json.dumps(data, indent=2,ensure_ascii=False)


if __name__ == "__main__":
    msg=Message.system("hello")
    print(msg.to_dict())

    msg=Message.bot("hello","world")
    print(msg.to_dict())

    msg=Message.tool("hello","12")
    print(msg.to_dict())

    """
    ChatCompletionMessage(content='',ations=None, audio=None, functiaaatiatiatioationsations=None, aaaations=None, audio=None, function_call=None, tool_calls=[ChatCompletionMessageToolCall(id='019754973564d5bf282e6aa62ef9f54e', function=Function(arguments='{"city":"Beijing"}', name='get_weather'), type='function')])
    """
    msg=Message.bot(content="hello",reasoning_content="world",**{
        "tool_calls":[
            {
                "id":"019754973564d5bf282e6aa62ef9f54e",
                "function":{
                    "arguments":"{\"city\":\"Beijing\"}",
                    "name":"get_weather"
                },
                "type":"function"
            }
        ]
    })
    print(msg.to_dict())

    kw= {'content': '', 'refusal': None, 'role': 'assistant', 'annotations': None, 'audio': None, 'function_call': None, 'tool_calls': [{'id': '019754b3bb51354c6e38c835f738bc26', 'function': {'arguments': '{"city":"Beijing"}', 'name': 'get_weather'}, 'type': 'function'}, {'id': '019754b3bb51f924890e0e119b50568e', 'function': {'arguments': '{"city":"Xi\'an"}', 'name': 'get_weather'}, 'type': 'function'}, {'id': '019754b3bb512ac4e34ca5b370c9c400', 'function': {'arguments': '{"city":"Shanghai"}', 'name': 'get_weather'}, 'type': 'function'}]}
    msg=Message.bot(**kw)
    print(msg.time)
    import time
    time.sleep(1)
    print(msg.to_dict())
    print(msg)
    print(msg.time)