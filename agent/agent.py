from typing import Optional,Dict,List,Callable
from model import OpenaiLLM,Message
from prompts import OpenaiAgentPrompt
from tools import *
name="Agent"
description="是一个全面的智能助手"
class Agent:
    def __init__(self,llm_config:Optional[Dict]=None,name:Optional[str]=name,description:Optional[str]=description):
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        self.system_prompt=OpenaiAgentPrompt.openai_agent_prompt(name,description).text()
        self.messages=[Message.system(self.system_prompt)]
        self.not_toolas_messages=[]
        self.user_qustions=[]

    
    def _get_messages(self):
        format_messages=[]
        for msg in self.messages:
            if (msg.role=='assistant' and not msg.tool_calls and msg.content) or msg.role=='user' or msg.role=='system':
                format_messages.append(msg)          
        format_messages=format_messages
        return format_messages
    
    def updated_message(self,messages:List[Message]):
        self.messages.extend(messages)

    def chat(self, prompt: str) -> str:
        self.messages.append(Message.user(prompt))
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
