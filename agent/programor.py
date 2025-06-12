from typing import List, Optional, Dict
from prompts import ProgramorPrompt
from model import Message,OpenaiLLM
import platform
import os
import sys
import time
from tools import *

class Programor:
    def __init__(self,llm_config:Optional[Dict]=None):
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        os_info=get_os_info()
        functions='\n'.join(f"<function>{func}</function>" for func in self.tools)
        self.system_prompt=ProgramorPrompt.get_system_prompt_zh(functions,os_info)
        self.messages=[Message.system(self.system_prompt)]
        self.not_tools_messages=[]
        self.user_qustions=[]
        self.context={
            "current_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "current_directory":os.getcwd(),
            "previous_question":self.user_qustions[-1] if self.user_qustions else "目前没有上下文",
        }
    
    def _get_messages(self):
        format_messages=[]
        for msg in self.messages:
            if (msg.role=='assistant' and not msg.tool_calls and msg.content) or msg.role=='user' or msg.role=='system':
                format_messages.append(msg)          
        format_messages=format_messages
        return format_messages
    
    def updated_message(self,messages:List[Message]):
        self.messages.extend(messages)

    def _context_str(self):
        return f"\n 当前时间：{self.context['current_time']}\n 当前目录：{self.context['current_directory']}\n 上一个问题：{self.context['previous_quesion']}"
    def chat(self, prompt: str) -> str:
        updated_prompt=ProgramorPrompt.get_user_prompt_zh(prompt,self._context_str)
        self.messages.append(Message.user(updated_prompt))
        self.user_qustions.append(prompt)
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        
        format_messages=self._get_messages()
        index=len(format_messages)
        print("format_messages",format_messages)
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
if __name__=="__main__":
    from config import get_siliconflow_model,get_ark_model
    llm_config=get_ark_model()
    programor=Programor(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat(prompt=prompt)
    print("*"*50)   
