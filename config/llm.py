import os

def get_model(api_key,base_url,model):
    llm_config={
        "client_cfg": {
            "api_key": api_key,
            "base_url": base_url,
        },
        "generation_cfg": {
            "model": model,
            "max_tokens": 4096,
            "top_p": 0.7,
            "temperature": 0.9,
        },
    }
    return llm_config
def get_ali_model():
    api_key =os.getenv("DASHSCOPE_API_KEY") 
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model ="qwen-plus-latest" 
    return get_model(api_key,base_url,model)
   
def get_siliconflow_model():
    api_key =os.getenv("SILICONFLOW_API_KEY")
    base_url = "https://api.siliconflow.cn/v1"
    model = "Qwen/Qwen3-32B"#"THUDM/GLM-Z1-32B-0414"#"deepseek-ai/DeepSeek-R1" #"deepseek-ai/DeepSeek-V3"#
    return get_model(api_key,base_url,model)

def get_ark_model():
    """
    获取ARK语言模型配置。
    
    返回:
        dict: 包含ARK语言模型客户端配置、生成配置和嵌入配置的字典。
        结构为:
        {
            "client_cfg": {
                "api_key": str,  # 从环境变量获取的API密钥
                "base_url": str  # API基础URL
            },
            "generation_cfg": {
                "model": str,      # 使用的模型名称
                "max_tokens": int, # 最大token数
                "top_p": float,    # 核采样参数
                "temperature": float  # 温度参数
            },
            "embedding_cfg": {
                "model": str,        # 嵌入模型名称
                "encoding_format": str  # 编码格式
            }
        }
    """
    api_key =os.getenv("ARK_API_KEY")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model ="doubao-1-5-thinking-pro-m-250428"
    embedding_model="doubao-embedding-large-text-250515"

    llm_config={
        "client_cfg": {
            "api_key": api_key,
            "base_url": base_url,
        },
        "generation_cfg": {
            "model": model,
            "max_tokens": 4096,
            "top_p": 0.7,
            "temperature": 0.9,
        },
        'embedding_cfg':{
            "model": embedding_model,
            # input=inputs,
            "encoding_format":"float",

        }
    }
    return llm_config


def get_zhipuai_model():
    api_key =os.getenv("zhipuai")
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    model = "GLM-4-Air-250414"#"GLM-4-Flash-250414"
    return get_model(api_key,base_url,model)
