from openai import OpenAI
from typing import Optional, Dict,List,Callable, Generator
import os
api_key =os.getenv("SILICONFLOW_API_KEY")
base_url = "https://api.siliconflow.cn/v1"
model ="Qwen/Qwen3-32B"

def parse_response(response) -> dict:
    """Parse LLM response into fixed format"""
    return {
        "id": response.id,
        "model": response.model,
        "created": response.created,
        "content": response.choices[0].message.content if hasattr(response.choices[0], 'message') else "",
        "finish_reason": response.choices[0].finish_reason,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        } if response.usage else None
    }

def call_llm(messages: List[Dict]) -> dict:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(model=model, messages=messages)
    return parse_response(response)

def call_llm_stream(messages: List[Dict]) -> Generator[dict, None, None]:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(model=model, messages=messages, stream=True)
    
    for chunk in response:
        yield parse_response(chunk)

if __name__=="__main__":
    messages=[{"role":"user","content":"你好"}]
    
    # Non-streaming call
    non_stream_response = call_llm(messages)
    print("Non-streaming response:")
    print(non_stream_response)
    
    # Streaming call
    print("\nStreaming response:")
    for chunk in call_llm_stream(messages):
        print(chunk)
