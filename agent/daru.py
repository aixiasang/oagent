from colorama import Fore, Style, init
from typing import Optional,Dict,List,Callable
from model import OpenaiLLM,Message
from prompts import DaRuPrompt,DaoPrompt,MoPrompt,MouShuPrompt
from tools import *
functions_prompts=r"""
【你可以使用的函数】
为了更好的帮助了解当下世界 提供一下函数工具来进行使用
在需要用到函数的情况下必须使用函数 
{functions}
"""
class MiniAgent:
    def __init__(self,llm_config:Optional[Dict]=None):
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        functions='\n'.join(f"<function>{func}</function>" for func in self.tools)
        self.func_prompt=functions_prompts.format(functions=functions)
        self.system_prompt=MouShuPrompt.moushu_prompt(self.func_prompt)
        self.user_enhanced_prompt_func=MouShuPrompt.moushu_user_prompt
        # print("self.system_prompt",self.system_prompt.text())
        self.messages=[Message.system(self.system_prompt.text())]
    
    
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
        updated_prompt = self.user_enhanced_prompt_func(prompt,"").txt()
        self.messages.append(Message.user(updated_prompt))
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
        updated_prompt = self.user_enhanced_prompt_func(prompt).txt()
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
        def fn(resp):
            for msg in resp:
                if msg.reasoning_content:
                    # 蓝色斜体显示
                    print(Fore.BLUE + Style.DIM + msg.reasoning_content, flush=True, end="")
                    print(Style.RESET_ALL, flush=True, end="")
                if msg.content:
                    #绿色加粗显示
                    print(Fore.GREEN + Style.BRIGHT + msg.content, flush=True, end="")
                    print(Style.RESET_ALL, flush=True, end="")
        self.fn_chat(fn,prompt)
    
    def get_messages(self):
        return self.messages
    def load_messages(self,messages:List[Message]):
        self.messages=messages

if __name__=="__main__":
    from config import get_siliconflow_model,get_ark_model
    llm_config=get_siliconflow_model()
    programor=MiniAgent(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat_stream(prompt=prompt)
    print("*"*50)
