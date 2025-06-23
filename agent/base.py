import os
from typing import Optional,Dict,List,Callable,Generator,Any
from model import Message, OpenaiLLM
import time
from colorama import Fore, Style
from prompt import ProgramorPrompt,get_tool_descs
from tools import *
class BaseAgent:
    """基础智能体类"""
    def __init__(self, llm_config: Optional[Dict] = None):
        self.llm = OpenaiLLM(llm_config)
        self.messages = []
        self.context = {
            "current_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "current_directory": os.getcwd(),
        }
    
    def _get_messages(self):
        """获取格式化的消息列表"""
        format_messages = []
        for msg in self.messages:
            if (msg.role == 'assistant' and not msg.tool_calls and msg.content) or \
               msg.role == 'user' or msg.role == 'system':
                format_messages.append(msg)
        return format_messages
    
    def updated_message(self, messages: List[Message]):
        """更新消息历史"""
        self.messages.extend(messages)
    
    def clear_messages(self):
        """清空消息历史（保留系统消息）"""
        self.messages = [msg for msg in self.messages if msg.role == 'system']
    
    def get_messages(self):
        return self.messages

    def load_messages(self,messages:List[Message]):
        self.messages=messages  
  
class Agent(BaseAgent):
    def __init__(self,llm_config:Optional[Dict]=None):
        super().__init__(llm_config)
        self.llm=OpenaiLLM(llm_config)
        self.tools=get_registered_tools()
        os_info=get_os_info()
        func_desc,_=get_tool_descs(self.tools)
        model=llm_config['generation_cfg']['model']
        self.system_prompt=ProgramorPrompt.programor_system_prompt(model,func_desc,os_info).text()
        self.messages=[Message.system(self.system_prompt)]
        self.not_toolas_messages=[]
        self.user_qustions=[]
        self.context={
            "current_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "current_directory":os.getcwd(),
            "previous_questions":self.user_qustions if self.user_qustions else "目前没有上下文",
        }
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

if __name__=="__main__":
    from config import get_siliconflow_model,get_ali_model
    llm_config=get_siliconflow_model()
    programor=Agent(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat_stream(prompt=prompt)
    print("*"*50)   
