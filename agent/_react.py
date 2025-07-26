from ._base import BaseAgent
from model import Message, OpenaiLLM, Messages,func_call
from prompt import react_prompt
from typing import Optional, Dict, List

class ReActAgent(BaseAgent):
    """
    React Agent
    """
    def __init__(self, llm_cfg: Optional[Dict], system_prompt: Optional[str] = None,):
        super().__init__(llm_cfg,system_prompt)

    def chat(self, prompt: str):
        content=f"<user_input>{prompt}</user_input>"
        self.messages.append(Message.user(content))
        while True:
            resp=self.llm.chat(self.messages,stream=True)
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
            _reasoning, _actions, _final= self._parser_msg(content)
            # print("_reasoning",_reasoning)
            # print("_actions",_actions)
            # print("_final",_final)
            if _final:
                break
            if _actions:
                tools_result=''
                for tool_result in self._exec_func(_actions):
                    tools_result += tool_result
                self.messages.append(Message.user(f"<tools_result>\n{tools_result}\n</tools_result>"))
            else:
                break
    def _exec_func(self,_actions):
        # {"id": "function_name", "function": {"name": "function_name", "arguments": {}}}
        import json
        import uuid
        # [{"fn":"get_weather","args":{"city":"beijing"}}]
        _curr_action = json.loads(_actions) 
        _id_map={}
        tool_calls = []
        for action in _curr_action:
            uix= uuid.uuid4().hex
            fn_name= action['fn']
            args=json.dumps(action['args'])
            curr_tools={
                'id':uix,
                'function': {
                    'name': fn_name,
                    'arguments': args
                }
            } 
            tool_calls.append(curr_tools)
            _id_map[uix]=(fn_name,args)
        for tool_result in func_call(tool_calls, parallel=True):
            _fn_id=tool_result.tool_call_id
            _content=tool_result.content
            fn_args=_id_map[_fn_id]
            yield f'<tool_result>\n{{"fn_args":{fn_args},"result":{_content}}}\n</tool_result>\n'


    def _parser_msg(self,content):
        import re
        _reasoning = re.search(r'<reasoning>(.*?)</reasoning>', content, re.DOTALL)
        _actions = re.search(r'<actions>(.*?)</actions>', content, re.DOTALL)
        _final = re.search(r'<final>(.*?)</final>', content, re.DOTALL)
        reasoning = _reasoning.group(1).strip() if _reasoning else ""
        actions = _actions.group(1).strip() if _actions else ""
        final = _final.group(1).strip() if _final else ""
        return reasoning, actions, final
    




if __name__=='__main__':
    from tools import get_registered_tools
    from config import get_siliconflow_model,get_ark_model
    from prompt import get_tool_descs
    tools_schema=get_tool_descs(get_registered_tools())
    system_prompt=react_prompt.format(tools=tools_schema)
    llm_cfg=get_siliconflow_model()#get_ark_model()
    react_agent=ReActAgent(llm_cfg,system_prompt)
    while True:
        user_input=input("\nuser:")
        if user_input.lower() in ['q','quit','exit']:
            break
        react_agent.chat(user_input)
    print(react_agent.messages)