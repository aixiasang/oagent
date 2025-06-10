from email import message
from typing import Dict, Optional,List
from agent import Agent
from prompts import AgentSquadPrompt
from model import Message,OpenaiLLM

class Classifier:
    def __init__(self,llm_config:Optional[Dict]=None):   
        llm_config=llm_config or {}
        self.llm=OpenaiLLM(llm_config)
        self.tools=AgentSquadPrompt.get_analyze_prompt_tool()
        self.system_prompt=AgentSquadPrompt.get_classification_prompt("","")
        self.agents:Dict[str,Agent]=None
        self.agents_descriptions:Optional[str]=None
        self.messages:List[Message]=None
    def set_agent(self,agents:Dict[str,Agent]):
        self.agents=agents
        self.agents_descriptions="\n\n".join(f"{agent.id}:{agent.description}" for agent in agents.values())

    def set_messages(self,messages:List[Message]):
        self.messages=messages
    
    def set_system_prompt(self,prompt:str):
        self.system_prompt=prompt

    def classify(self,user_input:str):
        import json
        kwargs={
            'messages':[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input},    
            ],
            "tools": self.tools,
            "tool_choice": {"type": "function", "function": {"name": "analyzePrompt"}},
            'stream':False,
        }
        resp=self.llm._chat(**kwargs)
        print(resp)
        tool_call=resp.choices[0].message.tool_calls[0]
        if not tool_call or tool_call.function.name!="analyzePrompt":
             raise ValueError("No valid tool call found in the response")
        tool_input = json.loads(tool_call.function.arguments)

        if isinstance(tool_input, dict) or 'selected_agent' not in tool_call or 'confidence' not in tool_call:
            raise ValueError("Tool input does not match expected structure")
        selected_agent=tool_input['selected_agent']
        confidence=tool_call['confidence']
        return selected_agent,confidence
        
    
if __name__ == "__main__":
    from config import get_siliconflow_model
    classifier=Classifier(get_siliconflow_model())
    ans=classifier.classify("英语老师")
    print(ans)
