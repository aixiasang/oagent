from ._base import BaseAgent
from typing import Optional,List,Dict
class RolePlayAgent(BaseAgent):
    def __init__(self, llm_cfg, system_prompt = None,tools:Optional[List[Dict]]=None):
        super().__init__(llm_cfg, system_prompt)
        self.tools=tools
    
    def _no_func_chat(self,prompt):
        self.messages.add_user_msg(prompt)
        resp=self.llm.chat(self.messages,stream=False)
        for msg in resp:
            if msg.role == 'assistant':
                if msg.reasoning_content:
                    print(msg.reasoning_content,end="",flush=True)
                if msg.content:
                    print(msg.content,end="",flush=True)
            else:
                print(msg,end="",flush=True)
    
    def _func_chat(self,prompt):
        self.messages.add_user_msg(prompt)
        while True:
            resp=self.llm.schat(self.messages,stream=True,tools=self.tools,tool_choice='auto')
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
    
    def chat(self, prompt):
        return self._func_chat(prompt) if self.tools else self._no_func_chat(prompt)
    

if __name__=='__main__':
    from tools import get_registered_tools
    from config import get_siliconflow_model,get_ark_model
    from ._base import get_tool_descs
    from prompt import miziha_prompt
    tools=get_registered_tools()
    tools_schema=get_tool_descs(tools)
    system_prompt=miziha_prompt(tools=tools_schema)
    print("system_prompt:",system_prompt)
    llm_cfg=get_siliconflow_model()#get_ark_model()
    roleplay_agent=RolePlayAgent(llm_cfg,system_prompt,tools)
    while True:
        user_input=input("\nuser:")
        if user_input.lower() in ['q','quit','exit']:
            break
        roleplay_agent.chat(user_input)
    print(roleplay_agent.messages)