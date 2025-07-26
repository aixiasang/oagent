"""
消息格式的定义和处理
定义了消息的结构，包括角色、内容、时间戳等字段
并提供了消息的创建、转换为字典和JSON格式的方法
"""
from dataclasses import dataclass
from time import time
import json
from typing import Union,Dict,List,Optional

@dataclass(frozen=False)
class Message:
    """字段含义"""
    role:str   
    id:str="-1"
    created:str=str(int(time())) 
    content:Optional[Union[str, Dict, List]]=None 
    reasoning_content:Optional[Union[str, Dict, List]]=None 
    tool_call_id: Optional[str] = None 
    tool_calls:Optional[List[Dict]]=None 
    
    """补充字段 候补 后续来进行优化"""
    # refusal: None
    # annotations: None
    # audio: None
    # function_call: None
    @staticmethod
    def system(content:str):
        return Message(role="system", content=content,)
    @staticmethod
    def user(content:Optional[Union[str, Dict, List]]):
        return Message(role="user", content=content)
    @staticmethod
    def assistant(id:str,created:str,content:Optional[Union[str, Dict, List]]=None,reasoning_content:Optional[Union[str, Dict, List]]=None,tool_calls:Optional[List[Dict]]=None):
        return Message(id=id,created=created,role="assistant", content=content, reasoning_content=reasoning_content, tool_calls=tool_calls)
    @staticmethod
    def tool_call_response(id:str,created:str,content,tool_calls:List[Dict]):
        return Message(id=id,created=created,role="assistant", content=content, tool_calls=[
            {
                'id': call['id'],
                'type': 'function',
                'function': {
                    'name': call['function']['name'],
                    'arguments': call['function']['arguments']
                }
            } for call in tool_calls
        ])
    @staticmethod
    def tool_result(tool_call_id:str,content:Optional[Union[str, Dict, List]]):
        return  Message(role="tool", tool_call_id=tool_call_id, content=content,)
    @staticmethod
    def check_tool_result(message:'Message'):
        return message.role=="tool" and message.tool_call_id and message.content
    def to_dict(self):
        required_fields=['role','content',"tool_call_id","tool_calls"]
        msg={}
        for field in required_fields:
            val=getattr(self,field,None)
            if val:
                msg[field]=val
        return msg
    
    def to_json(self):
        """将所有字段转为字典"""
        msg={}
        for field in self.__dataclass_fields__:
            val=getattr(self,field,None)
            if val is not None:
                msg[field]=val
        return msg
    
    def __repr__(self):
        data = self.to_json()
        return json.dumps(data, indent=2,ensure_ascii=False)
    @staticmethod
    def from_json(data: Dict) -> "Message":
        return Message(
            role=data.get("role"),
            id=data.get("id", "-1"),
            created=data.get("created", str(int(time()))),
            content=data.get("content"),
            reasoning_content=data.get("reasoning_content"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=data.get("tool_calls"),
        )
class Messages:
    def __init__(self,system_prompt:Optional[str]=None):
        self.messages:List[Message]=[]
        self.system_prompt_index=0
        if system_prompt:
            self.system_prompt_index+=1
            self.messages.append(Message.system(system_prompt))

    def _add_msg(self, msg:Message):
        if msg.role == 'system':
            self.messages.insert(self.system_prompt_index, msg)
            self.system_prompt_index +=1
        else:
            self.messages.append(msg)

    def _system_prompt(self, system_prompt: str,insert_flag:bool=True):
        if insert_flag: 
            self.messages.insert(self.system_prompt_index, Message.system(system_prompt))   
            self.system_prompt_index += 1   
        else:
            self.messages=[Message.system(system_prompt)]+self.messages[self.system_prompt_index:]
        self.system_prompt_index = 1 
    
    def insert_system_prompt(self, system_prompt: str):
        self._system_prompt(system_prompt, insert_flag=True)
    
    def update_system_prompt(self, system_prompt: str):
        self._system_prompt(system_prompt, insert_flag=False)
    
    def add_user_msg(self,msg):
        self._add_msg(Message.user(msg))
    
    def append(self, msg: Message):
        self._add_msg(msg)

    def rollback(self, n: int = 1):
        if n <= 0:
            return
        self.messages = self.messages[:-n]
        self.system_prompt_index = min(self.system_prompt_index, len(self.messages))
    
    def clear(self, keep_system: bool = True):
        if keep_system:
            self.messages = self.messages[:self.system_prompt_index]
        else:
            self.messages = []
            self.system_prompt_index = 0

    def save_to_json(self, file_path: str):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([msg.to_json() for msg in self.messages], f, ensure_ascii=False, indent=2)
    
    def load_from_json(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.messages = [Message(**msg) for msg in data]
    
    def check_tool_result(self):
        return Message.check_tool_result(self.messages[-1]) if self.messages else False
    
    def __iter__(self):
        return iter(self.messages)

    def __repr__(self) -> str:
        msgs='\n'.join([msg.__repr__() for msg in self.messages])
        return f"Messages(\n{msgs}\n)"
    
    def __str__(self) -> str:
        msgs='\n'.join([msg.__str__() for msg in self.messages])
        return f"Messages(\n{msgs}\n)"
    
    def __len__(self) -> int:
        return len(self.messages)

    def __getitem__(self, index):
        return self.messages[index]
    
    @staticmethod
    def from_json_list(data: List[Dict], system_prompt: Optional[str] = None) -> "Messages":
        msgs = Messages(system_prompt=system_prompt)
        msgs.messages = [Message.from_json(item) for item in data]
        return msgs
if __name__ == "__main__":
    msg=Message.system("hello")
    print(msg.to_dict())

    msg=Message.assistant("hello","world")
    print(msg.to_dict())

    """
    ChatCompletionMessage(content='',ations=None, audio=None, functiaaatiatiatioationsations=None, aaaations=None, audio=None, function_call=None, tool_calls=[ChatCompletionMessageToolCall(id='019754973564d5bf282e6aa62ef9f54e', function=Function(arguments='{"city":"Beijing"}', name='get_weather'), type='function')])
    """
    msg=Message.assistant(content="hello",reasoning_content="world",)
    print(msg.to_dict())
    msg=Message.assistant()
    print(msg.created)
    import time
    time.sleep(1)
    print(msg.to_dict())
    print(msg)
    print(msg.created)