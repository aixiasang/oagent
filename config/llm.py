import os

def get_model(api_key,base_url,model,embedding_model=None,rerank_model=None):
    llm_config={
        "client_cfg": {
            "api_key": api_key,
            "base_url": base_url,
        },
        "chat_cfg": {
                "model": model,
                "max_tokens": 4096,
                "top_p": 0.7,
                "temperature": 0.9,
            },
        'embedding_cfg':{
            "model": embedding_model,
            "encoding_format":"float",
        },
        "rerank_cfg":{
            'model':rerank_model
        }
    }
    return llm_config
def get_ali_model():
    api_key =os.getenv("DASHSCOPE_API_KEY") 
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model ="qwen-plus-latest" 
    return get_model(api_key,base_url,model)
   
def get_siliconflow_model():
    api_key=os.getenv("siliconflow_api_key")
    base_url='https://api.siliconflow.cn/v1'
    model="Qwen/Qwen3-235B-A22B-Instruct-2507"#"Qwen/Qwen3-32B"#'moonshotai/Kimi-K2-Instruct' 工具调用模型kimi有点偷工减料
    embedding_model="Qwen/Qwen3-Embedding-8B"
    rerank_model="Qwen/Qwen3-Reranker-8B"
    return get_model(api_key,base_url,model,embedding_model,rerank_model)

def get_ark_model():
    api_key=os.getenv("ark_api_key")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model ="doubao-seed-1-6-thinking-250615"
    embedding_model="doubao-embedding-large-text-250515"
    return get_model(api_key,base_url,model,embedding_model)


def get_zhipuai_model():
    api_key =os.getenv("zhipuai")
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    model = "GLM-4-Air-250414"#"GLM-4-Flash-250414"
    return get_model(api_key,base_url,model)
