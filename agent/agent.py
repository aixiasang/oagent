from typing import Optional,Dict,List
from model import OpenaiLLM,Message
from prompts import AgentSquadPrompt
class Agent:
    def __init__(self,llm_config:Optional[Dict]=None,name:str="Agent",description:str="A helpful assistant"):
        self.llm=OpenaiLLM(llm_config)
        self.prompt_template=AgentSquadPrompt.get_openai_prompt(name,description)
        self.messages=[Message.system(self.prompt_template)]
        
    def chat(self, prompt: str, tools: Optional[List[Dict]] = None, tool_choice: str = "auto", stream=True) -> str:
        self.messages.append(Message.user(prompt))
        kwargs = {}
        if tools:
            kwargs['tools'] = tools
            kwargs['tool_choice'] = tool_choice
        if stream:
            kwargs['stream'] = True
        while True:
            resp = self.llm.chat(messages=self.messages, **kwargs)
            for msg in resp:
                if msg.reasoning_content:
                    print(msg.reasoning_content, flush=True, end="")
                if msg.content:
                    print(msg.content, flush=True, end="")
            if Message.check_tool_result(self.messages[-1]):
                continue
            else:
                break

if __name__ == "__main__":
    from config import get_siliconflow_model
    from tools import *
    agent=Agent(get_siliconflow_model())
    tools=get_registered_tools()
    print("tools",tools)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        agent.chat(prompt=prompt,tools=tools)
    print("*"*50)