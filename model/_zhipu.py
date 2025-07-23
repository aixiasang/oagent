"""
智谱AI LLM 模型的实现
实现了智谱AI的聊天、嵌入、视频生成等功能
"""
from zhipuai import ZhipuAI
from typing import Any, Callable, Dict, List, Union
from ._openai import OpenaiLLM
from .msg import Message, Messages
class ZhiPuLLm(OpenaiLLM):
    def __init__(self, llm_config: Dict | None = None):
        super().__init__(llm_config)
        def _chat(*args,**kwargs):
            client=ZhipuAI(**self.client_cfg)
            return client.chat.completions.create(*args,**{**self.generation_cfg,**kwargs})
        def _embed(*args,**kwargs):
            client=ZhipuAI(**self.client_cfg)
            return client.embeddings.create(*args,**{**self.embedding_cfg,**kwargs})
        def _video_gen(*args,**kwargs):
            client=ZhipuAI(**self.client_cfg)
            return  client.videos.generations(*args,**kwargs)
        def _assistant(*args,**kwargs):
            client=ZhipuAI(**self.client_cfg)
            return client.assistant.conversation(*args,**kwargs)
        def _moderations(*args,**kwargs):
            """内容安全部分"""
            client=ZhipuAI(**self.client_cfg)
            return client.moderations.create(*args,**kwargs)
        self._chat=_chat
        self._embed=_embed
        self._video_gen=_video_gen
        self._assistant=_assistant
        self._moderations=_moderations

    def video_gen(self,*args,**kwargs):
        """
        https://www.bigmodel.cn/dev/api/videomodel/cogvideox
        """
        return self._video_gen(*args,**kwargs)

    def assistant(self,*args,**kwargs):
        """
        https://www.bigmodel.cn/dev/api/intelligent-agent-model/assistantapi
        """
        return self._assistant(*args,**kwargs)
    
if __name__ == "__main__":
    import os
    from .msg import Message
    api_key =os.getenv("zhipuai")
    model ="glm-4-plus"
    # embedding_model="doubao-embedding-large-text-250515"

    llm_config={
        "client_cfg": {
            "api_key": api_key,
            # "base_url": base_url,
        },
        "generation_cfg": {
            "model": model,
            "max_tokens": 4096,
            "top_p": 0.3,
            "temperature": 0.2,
        },
    }
    llm=ZhiPuLLm(llm_config)
    msgs=[
        Message.system("你是一个助手"),
        Message.user("查看一下天气？上海的和西安(xian)的")
    ]
    from tools import get_weather,get_registered_tools
    tools=get_registered_tools()
    while True:
        for msg in llm.chat(messages=msgs,tools=tools,tool_choice='auto',stream=True):
            if msg.reasoning_content:
                print(msg.reasoning_content,end="",flush=True)
            if msg.content:
                print(msg.content,end="",flush=True)
        if Message.check_tool_result(msgs[-1]):
            continue
        else:
            break