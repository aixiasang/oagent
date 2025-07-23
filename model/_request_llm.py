import os
import requests
from typing import List, Dict

def _base_requst(client_cfg:Dict,request_data:Dict,suffix:str='/rerank'):
    api_key,base_url=client_cfg['api_key'],client_cfg['base_url']
    url = f"{base_url}{suffix}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        }
    response = requests.post(url, headers=headers, json=request_data)
    response.raise_for_status()

    return response.json()

if __name__ == "__main__":
    data = {
        "model": "BAAI/bge-reranker-v2-m3",
        "query": "Apple",
        "documents": [
            "apple",
            "banana",
            "fruit",
            "vegetable"
        ]
    }
    api_key=os.getenv("siliconflow_api_key")
    base_url='https://api.siliconflow.cn/v1'
    model="Qwen/Qwen3-32B"#'moonshotai/Kimi-K2-Instruct'
    embedding_model="Qwen/Qwen3-Embedding-8B"
    client_cfg={
        "api_key": api_key,
        "base_url": base_url,
    }
    result=_base_requst(client_cfg,data)
    print(result)