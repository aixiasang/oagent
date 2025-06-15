from math import log
import stat
from token import OP
from venv import create
from click import Option
from openai import OpenAI
from typing import Optional, Dict, List, Callable, Generator, Union
import os
from dataclasses import dataclass



"""
{
  "id": "<string>",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "<string>",
        "reasoning_content": "<string>",
        "tool_calls": [
          {
            "id": "<string>",
            "type": "function",
            "function": {
              "name": "<string>",
              "arguments": "<string>"
            }
          }
        ]
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 123,
    "total_tokens": 123
  },
  "created": 123,
  "model": "<string>",
  "object": "chat.completion"
}
"""

@dataclass
class Message:
    """
    使用的字段 id created role 

    这四个字段不知道是什么意思
    logprobs:None
    annotations:None 
    audio:None
    function_call:None
    """
    
    role:str='user'
    finish_reason:str=""
    id:Optional[str]=''
    created:Optional[int]=0
    content:Optional[Union[str, Dict, List]]=None
    reasoning_content:Optional[Union[str, Dict, List]]=None
    tool_calls:Optional[List[Dict]]=None
    usage: Optional[Dict]=None

    @staticmethod
    def user(content:Optional[Union[str, Dict, List]]):
        return Message(role="user", content=content)
    @staticmethod
    def bot(id:Optional[str],   
            created:Optional[int],
            content:Optional[Union[str, Dict, List]],
            reasoning_content:Optional[Union[str, Dict, List]],
            tool_calls:List[Dict],
            finish_reason:str,
            usage: Optional[Dict]
            ):
        return Message(
            role='assistant',
            id=id,
            created=created,
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage
        )
    

api_key = os.getenv("SILICONFLOW_API_KEY")
base_url = "https://api.siliconflow.cn/v1"
model = "Qwen/Qwen3-32B"

def call_llm(messages: List[Dict]) -> dict:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(model=model, messages=messages)

    id=response.id
    created=response.created
    usage=response.usage
    finish_reason=response.choices[0].finish_reason 
    msg=response.choices[0].message
    content=msg.content
    reasoning_content=msg.reasoning_content
    if finish_reason=='tool_calls':
        tool_calls=msg.tool_calls
    else:
        tool_calls=None
    return Message.bot(id,created,content,reasoning_content,tool_calls,finish_reason,usage)
    

def call_llm_stream(messages: List[Dict]) -> Generator[dict, None, None]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(model=model, messages=messages, stream=True)
    return response
if __name__=="__main__":
    messages=[{"role":"user","content":"你好"}]
    
    # Non-streaming call
    non_stream_response = call_llm(messages)
    non_stream_response
    print("Non-streaming response:")
    print(non_stream_response)
    
    # # Streaming call
    # print("\nStreaming response:")
    # for chunk in call_llm_stream(messages):
    #     print(chunk)
