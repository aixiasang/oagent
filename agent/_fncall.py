from ._base import BaseAgent
from model import Message, OpenaiLLM, Messages,func_call
from prompt import fncall_prompt,get_tool_descs
from typing import Optional, Dict, List

class FnCallAgent(BaseAgent):
    def __init__(self, llm_cfg: Optional[Dict], system_prompt: Optional[str] = None,tools:List[Dict]=None):
        super().__init__(llm_cfg,system_prompt)
        self.tools=tools
        
    def chat(self, prompt: str):
        content=f"<user_input>{prompt}</user_input>"
        self.messages.append(Message.user(content))
        content=''
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
        return content


if __name__=='__main__':
    from tools import get_registered_tools
    from config import get_siliconflow_model,get_ark_model
    tools=get_registered_tools()
    tools_schema=get_tool_descs(tools)
    system_prompt=fncall_prompt.format(tools=tools_schema)
    llm_cfg=get_siliconflow_model()#get_ark_model()
    react_agent=FnCallAgent(llm_cfg,system_prompt,tools)
    while True:
        user_input=input("\nuser:")
        if user_input.lower() in ['q','quit','exit']:
            break
        react_agent.chat(user_input)
    print(react_agent.messages)