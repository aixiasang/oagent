from rag import(
    TiktokenTokenizer,
    Parser,
    VectorStore
)
from model import OpenaiLLM
from config import get_siliconflow_model
from ._base import BaseAgent
from typing import Optional,List,Dict

def get_vb():
    dim=1024*4
    chunk_size=512*4
    leap_size=128
    tokenizer=TiktokenTokenizer(encoding_name='cl100k_base')
    llm_cfg=get_siliconflow_model()
    # llm_cfg['embedding_cfg']['model']='BAAI/bge-m3'
    llm=OpenaiLLM(llm_config=llm_cfg)
    vb=VectorStore(dim=dim,llm=llm,tokenizer=tokenizer,chunk_size=chunk_size,leap_size=leap_size)
    return vb

def vb_insert(vb:VectorStore,file_path:str):
    vb.add_doc(Parser.parser(file_path))


class RagAgent(BaseAgent):
    def __init__(self, llm_cfg, system_prompt = None,tools:Optional[List[Dict]]=None,vb:VectorStore=None):
        super().__init__(llm_cfg, system_prompt)
        self.tools=tools
        self.vb=vb

    def _vb_query_rerank_prompt(self,query:str,top_k=6):
        results=self.vb.rereank(query=query,top_k=top_k)
        return self.vb._formated_result(results)
    def _no_func_chat(self,prompt):
        query_info=self._vb_query_rerank_prompt(prompt)
        print("query_info")
        print(query_info)
        enhanced_prompt=f"<user_input>\n{prompt}\n<user_input>\n<rag_query>{query_info}</rag_query>"
        self.messages.add_user_msg(enhanced_prompt)
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
        query_info=self._vb_query_rerank_prompt(prompt)
        enhanced_prompt=f"<user_input>\n{prompt}\n<user_input>\n<rag_query>{query_info}</rag_query>"
        self.messages.add_user_msg(enhanced_prompt)
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
    

    def close(self):
        self.vb.save_index()
if __name__=='__main__':
    from tools import get_registered_tools
    from config import get_siliconflow_model,get_ark_model
    from ._base import get_tool_descs
    from prompt import li_bai_prompt
    tools=get_registered_tools()
    tools_schema=get_tool_descs(tools)
    system_prompt=li_bai_prompt(tools=tools_schema)
    print("system_prompt:",system_prompt)
    llm_cfg=get_siliconflow_model()#get_ark_model()
    vb=get_vb()
    vb_insert(vb,file_path='data/libai1.txt')
    vb.save_index()
    rag_agent=RagAgent(llm_cfg,system_prompt,tools,vb)
    while True:
        user_input=input("\nuser:")
        if user_input.lower() in ['q','quit','exit']:
            break
        rag_agent.chat(user_input)
    print(rag_agent.messages)