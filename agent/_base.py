"""
agent_cfg:
"""
import json
import os
from typing import Generator, Optional, Dict, List, Callable, Any
from model import Message, OpenaiLLM,Messages
import uuid
default_save_path="/agent_save"
class BaseAgent:
    def __init__(self,llm_cfg:Optional[Dict],system_prompt:Optional[str]=None,save_path:Optional[str]=default_save_path):
        self.llm = OpenaiLLM(llm_cfg)
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.messages = Messages(system_prompt=self.system_prompt)
        self._session_id = str(uuid.uuid4().hex)
        self._save_path = save_path
        os.makedirs(self._save_path, exist_ok=True)
    def chat(self, prompt: str):
        self.messages.add_user_msg(prompt)
        resp=self.llm.chat(self.messages,stream=False)
        self._format_resp(resp)

    def _to_json(self) -> str:
        return json.dumps({
            "_session_id": self._session_id,
            "system_prompt": self.system_prompt,
            "messages": [msg.to_json() for msg in self.messages]
        }, indent=2, ensure_ascii=False)

    def _format_resp(self,resp:Generator[Message, Any, None]):
        for msg in resp:
            if msg.role == 'assistant':
                if msg.reasoning_content:
                    print(msg.reasoning_content,end="",flush=True)
                if msg.content:
                    print(msg.content,end="",flush=True)
            else:
                print(msg,end="",flush=True)
    @classmethod
    def _from_json(cls, js_data: str, llm_cfg: Optional[Dict] = None, save_path: Optional[str] = default_save_path) -> "BaseAgent":
        data = json.loads(js_data)
        agent = cls(llm_cfg, system_prompt=data.get("system_prompt"), save_path=save_path)
        agent._session_id = data.get("_session_id")
        agent.messages = Messages.from_json_list(data.get("messages", []))
        return agent

    def save_agent(self, agent_id: Optional[str] = None):
        file_name = agent_id if agent_id else self._session_id
        full_path = os.path.join(self._save_path, f"{file_name}.json")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(self._to_json())

    @classmethod
    def load_agent(cls, agent_id: str, llm_cfg: Optional[Dict] = None, save_path: Optional[str] = default_save_path) -> "BaseAgent":
        full_path = os.path.join(save_path, f"{agent_id}.json")
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Agent with id '{agent_id}' not found at {full_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            return cls._from_json(f.read(), llm_cfg=llm_cfg, save_path=save_path)

    def last_msg(self) -> str:
        return self.messages[-1]
    
       
    
if __name__ == "__main__":
    from config import get_siliconflow_model
    llm_config = get_siliconflow_model()
    agent = BaseAgent(llm_config, system_prompt="You are a helpful assistant.")
    while True:
        try:
            prompt = input("\nYou: ")
            if prompt.lower() in ['exit', 'quit','q']:
                break
            agent.chat(prompt)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")