from typing import Optional,Dict,List,Callable
from model import OpenaiLLM,Message
from prompts import AgentSquadPrompt
from tools import *
name="Agent"
description="是一个全面的智能助手"
class Agent:
    def __init__(self,llm_config:Optional[Dict]=None,name:Optional[str]=name,description:Optional[str]=description):
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        os_info=get_os_info()
        functions='\n'.join(f"<function>{func}</function>" for func in self.tools)
        self.system_prompt=AgentSquadPrompt.get_openai_prompt(name,description)
        self.messages=[Message.system(self.system_prompt)]
        self.not_tools_messages=[]
        self.user_qustions=[]
        # self.context={
        #     "current_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        #     "current_directory":os.getcwd(),
        #     "previous_question":self.user_qustions[-1] if self.user_qustions else "目前没有上下文",
        # }
    
    def _get_messages(self):
        format_messages=[]
        for msg in self.messages:
            if (msg.role=='assistant' and not msg.tool_calls and msg.content) or msg.role=='user' or msg.role=='system':
                format_messages.append(msg)          
        format_messages=format_messages
        return format_messages
    
    def updated_message(self,messages:List[Message]):
        self.messages.extend(messages)

    # def _context_str(self):
    #     return f"\n 当前时间：{self.context['current_time']}\n 当前目录：{self.context['current_directory']}\n 上一个问题：{self.context['previous_quesion']}"
    def chat(self, prompt: str) -> str:
        updated_prompt = prompt
        self.messages.append(Message.user(updated_prompt))
        self.user_qustions.append(prompt)
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        
        format_messages = self._get_messages()
        index = len(format_messages)
        while True:
            resp = self.llm.chat(messages=format_messages, **kwargs)
            for msg in resp:
                if msg.reasoning_content:
                    print(msg.reasoning_content, flush=True, end="")
                if msg.content:
                    print(msg.content, flush=True, end="")
            if Message.check_tool_result(format_messages[-1]):
                continue
            else:
                break
        self.updated_message(format_messages[index:])
    def fn_chat(self, fn: Callable, prompt, **kwargs):
        updated_prompt = prompt
        self.messages.append(Message.user(updated_prompt))
        self.user_qustions.append(prompt)
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        
        format_messages = self._get_messages()
        index = len(format_messages)
        while True:
            resp = self.llm.chat(messages=format_messages, **kwargs)
            for msg in resp:
                fn(msg) 
                if msg.reasoning_content:
                    print(msg.reasoning_content, flush=True, end="")
                if msg.content:
                    print(msg.content, flush=True, end="")
            if Message.check_tool_result(format_messages[-1]):
                continue
            else:
                break
        self.updated_message(format_messages[index:])
    def web_chat(self, prompt: str):
        """专门为web应用设计的聊天方法，返回带有正确id和created字段的消息流"""
        import uuid
        from datetime import datetime
        
        updated_prompt = prompt
        self.messages.append(Message.user(updated_prompt))
        self.user_qustions.append(prompt)
        
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        
        format_messages = self._get_messages()
        index = len(format_messages)
        
        # 为这次对话生成唯一的消息ID和时间戳
        message_id = str(uuid.uuid4())
        created_time = datetime.now().isoformat()
        
        while True:
            resp = self.llm.chat(messages=format_messages, **kwargs)
            for msg in resp:
                # 创建带有正确id和created字段的消息
                web_msg = Message.bot(
                    id=message_id,
                    created=created_time,
                    content=msg.content,
                    reasoning_content=msg.reasoning_content
                )
                yield web_msg
                
            if Message.check_tool_result(format_messages[-1]):
                continue
            else:
                break
                
        self.updated_message(format_messages[index:])
    
    def get_messages(self):
        return self.messages
    def load_messages(self,messages:List[Message]):
        self.messages=messages
if __name__=="__main__":
    from config import get_siliconflow_model,get_ark_model
    llm_config=get_siliconflow_model()
    programor=Agent(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat(prompt=prompt)
    print("*"*50)
