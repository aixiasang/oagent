
# 🤖 OAgent 智能代理框架

OAgent 是一个基于大语言模型（LLM）的智能代理开发框架，支持函数调用、RAG 检索增强、角色扮演等多种智能交互模式，配备丰富的工具生态，适用于多场景 AI 应用开发。

---

## 🧩 项目亮点
- 🔧 **多模型兼容**：支持 OpenAI、智谱、Moonshot、Qwen 等主流 LLM。
- 🏗️ **模块化架构**：核心功能分为 agent、model、rag、tools 等模块，易于扩展和维护。
- 🧠 **RAG 检索增强**：集成向量数据库，支持文档切片、索引、语义检索。
- 🛠️ **工具系统**：支持 MCP 协议，工具可热插拔，便于自定义扩展。
- 🎭 **角色扮演模式**：支持多角色对话，沉浸式交互体验。
- 📈 **可视化监控**：可集成监控模块，实时追踪代理运行状态。

---

## 📦 目录结构
```
agent/         # 代理核心模块
    _base.py       # 基础代理类
    _fncall.py     # 函数调用代理
    _rag.py        # RAG 检索代理
    _roleplay.py   # 角色扮演代理
    _react.py      # ReAct 代理
model/         # LLM模型接口
    _openai.py     # OpenAI模型实现
    _zhipu.py      # 智谱模型实现
    _request_llm.py# 通用LLM请求封装
    base.py        # 通用模型基类
    func.py        # 工具函数
    msg.py         # 消息结构
rag/           # 检索增强生成模块
    _vector_db.py  # 向量数据库接口
    _chunk.py      # 文本切片处理
    _parser.py     # 文档解析
    _tokenizer.py  # 分词器
config/        # 配置模块
    llm.py         # LLM模型配置
prompt/        # 提示词模板
    _base.py       # 通用提示词
    _rag.py        # RAG相关提示词
    _other.py      # 其他场景提示词
    __init__.py    # 提示词注册
storage/       # 索引与缓存
    faiss.index    # Faiss向量索引
    index.npz      # Numpy索引
    _cache.json    # 缓存文件
    ...
tools/         # 工具集
    base_tools.py  # 基础工具
    register.py    # 工具注册
    with_os.py     # OS相关工具
    _mcp.py        # MCP协议工具
    ...
data/          # 示例数据
    libai1.txt     # 李白诗歌样例
    libai2.txt     # 李白诗歌样例
```

---

## ⚙️ LLM API 密钥配置
在 `config/llm.py` 或 `.env` 文件中设置你的 API 密钥：
```python
def get_siliconflow_model():
    api_key=os.getenv("siliconflow_api_key")
    base_url='https://api.siliconflow.cn/v1'
    model="Qwen/Qwen3-235B-A22B-Instruct-2507"
    embedding_model="Qwen/Qwen3-Embedding-8B"
    rerank_model="Qwen/Qwen3-Reranker-8B"
    return get_model(api_key,base_url,model,embedding_model,rerank_model)
```

## 🛠️ 开发规范
- ✅ 遵循PEP8编码规范
- 🧩 使用模块化设计原则
- 📌 关键代码添加类型注解
- 🧪 开发新功能需同步更新单元测试
- 📚 文档字符串采用Google风格

## 🧪 使用案例

### 函数调用支持
```python
from tools import get_registered_tools
from config import get_siliconflow_model,get_ark_model
tools=get_registered_tools()
tools_schema=get_tool_descs(tools)
system_prompt=fncall_prompt.format(tools=tools_schema)
llm_cfg=get_siliconflow_model()#get_ark_model()
react_agent=FnCallAgent(llm_cfg,system_prompt,tools)
while True:
    user_input=input("\nuser:")
    if user_input.lower() in ['q','quit','exit']:
        break
    react_agent.chat(user_input)
print(react_agent.messages)
```

### RAG检索【支持并不是很充分】
```python
from tools import get_registered_tools
from config import get_siliconflow_model,get_ark_model
from ._base import get_tool_descs
from prompt import li_bai_prompt
tools=get_registered_tools()
tools_schema=get_tool_descs(tools)
system_prompt=li_bai_prompt(tools=tools_schema)
print("system_prompt:",system_prompt)
llm_cfg=get_siliconflow_model()
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
```
## 🤝 参考
- [OpenAI](https://openai.com/)
- [LightRag](https://github.com/HKUDS/LightRAG)
- [TrustRag](https://github.com/gomate-community/TrustRAG)
- [QwenAgent](https://github.com/QwenLM/Qwen-Agent)
## 📄 许可证
MIT License
