import os
from model import OpenaiLLM,Messages
from typing import Dict, List, Optional,Callable
from agent import BaseAgent
class Tace(BaseAgent):
    def __init__(self,llm_cfg:Dict,system_prompt:str,tools_schema:List[Dict],user_enhance_prompt:Callable):
        self._llm=OpenaiLLM(llm_cfg)
        self._task:List[str]=[]
        self._system_prompt=system_prompt
        self.messages:Messages=Messages(system_prompt=self._system_prompt)
        self.tools=tools_schema
        self.user_enhance_prompt=user_enhance_prompt
        self.history_log: List[str] = []  
    
    def chat(self,task:str,):
        self._task.append(task)
        history_summary = "\n".join(self.history_log[-5:]) 
        user_message=self.user_enhance_prompt(task,history_summary)
        self.messages.add_user_msg(user_message)
        while True:
            resp=self._llm.schat(self.messages,stream=True,tools=self.tools,tool_choice='auto')
            content=''
            for msg in resp:
                if msg.role == 'assistant':
                    if msg.reasoning_content:
                        print(msg.reasoning_content,end="",flush=True)
                    if msg.content:
                        print(msg.content,end="",flush=True)
                        content += msg.content
                else:
                    print(msg,end="",flush=True)
            if not self.messages.check_tool_result():
                break
        self.history_log.append(f"Task: {task}\nAnswer: {self.last_msg().content}...")
   
if __name__ == "__main__":
    from config import get_siliconflow_model,get_ark_model
    from tools import get_tools_list,init_mcp_tools,get_os_info,get_registered_tools
    from .prompt import system_prompt,user_prompt
    from .use_tools import (
        bash,
        edit_file,
        json_edit
    )

    mcp_cfg={
                "mcpServers": {
                    "sequential-thinking": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-sequential-thinking"
                        ]
                    }
                }
            }
    init_mcp_tools(mcp_cfg)
    tools_schema=get_registered_tools()
    llm_cfg=get_ark_model()
    model=llm_cfg['chat_cfg']['model']
    def get_tool_descs(tools:List[Dict]):
        tool_descs=[]
        for tool in tools:
            content=f'<function>\n{tool}\n</function>\n'
            tool_descs.append(content)
        return "<functions>\n"+"".join(tool_descs)+"</functions>"   
    user_info=get_os_info()

    system_prompt=system_prompt(model=model,functions=get_tool_descs(tools_schema),user_info=user_info)
    print(tools_schema)
    trae=Tace(llm_cfg,system_prompt,tools_schema,user_prompt)
    while True:
        user_input=input("\nuser:")
        if user_input in ['q','quit','exit']:
            break
        trae.chat(user_input)
    print(trae.messages)