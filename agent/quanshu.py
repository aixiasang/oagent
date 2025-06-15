from .daru import MiniAgent
from model import Message
from typing import Optional,Dict
from prompts import QuanShuPrompt   
class QuanShuAgent(MiniAgent):
    def __init__(self,llm_config:Optional[Dict]=None):
        super().__init__(llm_config)
        self.system_prompt=QuanShuPrompt.quanshu_system_prompt(extra_info=self.func_prompt).text()
        self.user_enhanced_prompt_func=QuanShuPrompt.quanshu_user_prompt
        self.messages=[Message.system(self.system_prompt)]  
        print(self.messages)
    
    def chat_stream(self, prompt):
        return super().chat_stream(prompt)
if __name__=="__main__":
    from config import get_siliconflow_model,get_ark_model
    llm_config=get_siliconflow_model()
    programor=QuanShuAgent(llm_config)
    while True:
        prompt=input("\nUser>>")
        if prompt=="q":
            break
        programor.chat_stream(prompt=prompt)
    print("*"*50)