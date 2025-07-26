from time import time

from model import Messages,OpenaiLLM
from ._base import BaseAgent
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from utils import parse_json_resp

@dataclass
class Share:
    """共享数据块
    id/task/
    """
    agent_id:int
    task:str
    call_in:Optional[Any]=None
    call_back:Optional[Any]=None
    _created:str=str(int(time()))

    def add_input(self,call_in:Any):
        self.call_in=call_in
    
    def add_back(self,call_back:Any):
        self.call_back=call_back
    
    def __str__(self):
        return str(self.__dict__)

class Context:
    def __init__(self):
        self.shares:List[Share]=[]
    
    def add_share(self,share:Share):
        self.shares.append(share)

    def use_call_back(self,idx:int):
        return self.shares[idx].call_back

    def __str__(self):
        return '\n'.join([f"share index:{idx}\nshare info:\n\t{share}" for idx,share in enumerate(self.shares)])



class Control(BaseAgent):
    def __init__(self, llm_cfg,agent_cfg,system_prompt = None,enhance_prompt = None):
        super().__init__(llm_cfg, system_prompt)
        self._context:Context=Context()
        self.agent_cfg = agent_cfg
        self.enhanced_prompt = enhance_prompt
        self.messages=Messages(system_prompt=self.system_prompt)
        self._user_prompts:List[str]=[]
    def chat(self, prompt: str) -> str:
        self._user_prompts.append(prompt)
        while True:
            self.messages.add_user_msg(self.enhanced_prompt.format(prompt=prompt,context=str(self._context)))
            resp=self.llm.chat(self.messages,stream=True)
            self._format_resp(resp)
            task=self._parser_resp(self.last_msg().content)
            if task.agent_id==-1:
                break
            self._exec_agent(task)
    def _parser_resp(self,resp:str):
        data=parse_json_resp(resp)
        print(type(data))
        print(data)
        _agent_id=data.get("agent_id")
        _prompt=data.get("prompt")
        _reasoning=data.get("reasoning")
        return Share(_agent_id,_prompt,)
    def _exec_agent(self,share:Share):
        
        user_prompt='\n'.join([f"user task:\nidx:{i}\ntask:{v}" for i,v in enumerate(self._user_prompts)])
        in_=f"{user_prompt}\n{share.task}\n{str(self._context)}"
        try:
            agent_id = share.agent_id
            fn_name = 'chat'            
            args={
                "prompt":in_,
            }
            share.add_input(in_)
            if agent_id not in self.agent_cfg:
                raise ValueError(f"Agent id {agent_id} not found.")

            agent_entry = self.agent_cfg[agent_id]
            agent_obj = agent_entry["agent"]

            if not hasattr(agent_obj, fn_name):
                raise AttributeError(f"Agent {agent_id} has no method {fn_name}.")

            fn = getattr(agent_obj, fn_name)
            result = fn(**args)
            share.add_back(result)
            self._context.add_share(share)

        except Exception as e:
            print(f"[Agent 调用错误]: {e}")
            result = f"[ERROR] {e}"


if __name__ == "__main__":
    from prompt import control_user_prompt,control_system_prompt
    from tools import get_registered_tools
    from config import get_siliconflow_model,get_ark_model
    from prompt import miziha_prompt,li_bai_prompt,get_tool_descs,fncall_prompt
    from ._roleplay import RolePlayAgent
    from ._fncall import FnCallAgent
    tools_schema=get_tool_descs(get_registered_tools())
    tools=get_registered_tools()
    llm_cfg=get_siliconflow_model()
    miziha_prompt=miziha_prompt(tools=tools_schema)
    libai_prompt=li_bai_prompt(tools=tools_schema)
    fncall_system_prompt=fncall_prompt.format(tools=tools_schema)

    miziha_agent=RolePlayAgent(llm_cfg,miziha_prompt)
    libai_agent=RolePlayAgent(llm_cfg,libai_prompt)
    fncall_agent=FnCallAgent(llm_cfg,fncall_system_prompt,tools)
    agent_cfg={
            1: {
                "agent":libai_agent,
                "desc":"角色扮演李白",
            },
            2: {
                "agent":miziha_agent,
                "desc":"角色扮演 宫水三叶",
            },
            3:{
                "agent":fncall_agent,
                "desc":"可以进行工具调用的智能体，可以调用工具",
            },
        }
    agent_desc= [f'agent_id:{agent_id}\nagent_desc:\n{agent_data['desc']}\n' for agent_id,agent_data in agent_cfg.items()]
    system_prompt=control_system_prompt.format(agents_desc=agent_desc,context="初始化阶段为空")
    control_agent=Control(
        llm_cfg=llm_cfg,
        agent_cfg=agent_cfg,
        system_prompt=system_prompt,
        enhance_prompt=control_user_prompt,
    )
    while True:
        prompt=input('请输入问题：')
        if prompt in ['exit','quit','q']:
            break
        control_agent.chat(prompt)

