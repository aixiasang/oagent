from typing import Any, Generator, List, Optional, Dict,Callable

from colorama import Fore, Style
from prompts import ProgramorPrompt
from model import Message,OpenaiLLM
import os
import time
from tools import *

class Programor:
    def __init__(self,llm_config:Optional[Dict]=None):
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        os_info=get_os_info()
        functions='\n'.join(f"<function>{func}</function>" for func in self.tools)
        self.system_prompt=ProgramorPrompt.programor_system_prompt(functions,os_info).text()
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
        return '\n'.join([f"{k}:{v}" for k,v in self.context.items()])
    def chat(self, prompt: str) -> str:
        updated_prompt=ProgramorPrompt.programor_user_prompt(prompt,self._context_str()).txt()
        self.messages.append(Message.user(updated_prompt))
        self.user_qustions.append(prompt)
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        
        format_messages=self._get_messages()
        index=len(format_messages)
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
        updated_prompt = ProgramorPrompt.programor_user_prompt(prompt,self._context_str()).txt()
        self.messages.append(Message.user(updated_prompt))
        kwargs = {}
        kwargs['tools'] = self.tools
        kwargs['tool_choice'] = 'auto'
        kwargs['stream'] = True
        format_messages = self._get_messages()
        index = len(format_messages)
        while True:
            resp=self.llm.chat(messages=format_messages, **kwargs)
            fn(resp)
            if Message.check_tool_result(format_messages[-1]):
                continue
            else:
                break
        self.updated_message(format_messages[index:])
    def chat_stream(self,prompt:str):
        def fn(resp:Generator[Message, Any, None]):
            for msg in resp:
                if msg.role=='tool':
                    print(msg)
                else:
                    if msg.reasoning_content:
                        print(Fore.BLUE + Style.BRIGHT + msg.reasoning_content, flush=True, end="")
                        print(Style.RESET_ALL, flush=True, end="")
                    if msg.content:
                        if msg.tool_calls:
                            print(msg)
                            continue
                        print(Fore.GREEN + Style.BRIGHT + msg.content, flush=True, end="")
                        print(Style.RESET_ALL, flush=True, end="")
        self.fn_chat(fn,prompt)
    
    def get_messages(self):
        return self.messages
    def load_messages(self,messages:List[Message]):
        self.messages=messages      
if __name__=="__main__":
    from config import get_siliconflow_model
    llm_config=get_siliconflow_model()
    programor=Programor(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat_stream(prompt=prompt)
    print("*"*50)   
