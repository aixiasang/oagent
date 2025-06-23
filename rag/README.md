# OAgent RAG 系统

## 概述

OAgent RAG（Retrieval Augmented Generation）系统是一个现代化的检索增强生成框架，专门设计用于与LLM客户端直接集成。系统支持多种文档格式、智能文本分割和高效的向量检索。

## 主要特性

### 🚀 直接LLM集成
- **零配置嵌入**: 直接使用您的LLM客户端的embed方法
- **异步支持**: 全面的异步API设计
- **自定义函数**: 支持自定义嵌入函数

### 📄 丰富的文档支持
- **多格式支持**: PDF, Word, Markdown, HTML, 纯文本, JSON, CSV
- **智能分割**: 7种文本分割策略（递归、Token、Markdown、Python、JavaScript、HTML、LaTeX）
- **批量处理**: 支持文件夹批量导入

### 🔍 强大的检索能力
- **相似度搜索**: 基于向量相似度的精确检索
- **重排序**: 支持检索结果重排序
- **元数据过滤**: 基于元数据的条件筛选
- **上下文生成**: 自动生成RAG上下文

### 💾 可靠的存储
- **持久化**: 基于ChromaDB的向量存储
- **批量操作**: 高效的批量添加和查询
- **数据管理**: 文档增删改查完整支持

## 快速开始

### 基础使用

```python
import asyncio
from oagent.rag import RAGManager

# 假设您已经有一个LLM客户端
class MyLLMClient:
    async def embed(self, texts):
        # 您的嵌入实现
        return embeddings

async def main():
    # 创建RAG管理器
    rag_manager = RAGManager(
        llm_client=MyLLMClient(),
        provider="llm",
        collection_name="my_documents",
        persist_directory="./rag_db"
    )
    
    # 添加文档
    documents = [
        {
            "content": "这是一个示例文档内容...",
            "metadata": {"source": "example.txt", "category": "demo"}
        }
    ]
    
    result = await rag_manager.add_documents(documents)
    print(f"添加结果: {result}")
    
    # 查询
    results = await rag_manager.search_with_score("查询内容", top_k=5)
    for result in results:
        print(f"分数: {result['score']:.3f}")
        print(f"内容: {result['content']}")

asyncio.run(main())
```

### 文件处理

```python
# 添加单个文件
await rag_manager.add_file("./documents/readme.md")

# 批量添加文件
await rag_manager.add_files([
    "./docs/guide.pdf",
    "./docs/api.md"
])

# 添加整个目录
await rag_manager.add_directory(
    "./knowledge_base",
    glob_pattern="**/*.{md,txt,pdf}",
    exclude_patterns=["**/.*", "**/__pycache__/**"]
)
```

### 高级查询

```python
# 带分数的搜索
results = await rag_manager.search_with_score(
    query="机器学习算法",
    top_k=10,
    filter_metadata={"category": "AI"}
)

# 重排序搜索
results = await rag_manager.search_with_rerank(
    query="深度学习",
    k=20,          # 初始检索数量
    rerank_k=5     # 重排序后返回数量
)

# 生成RAG上下文
context = await rag_manager.generate_context(
    query="什么是RAG？",
    top_k=5,
    max_context_length=4000
)
```

## 配置选项

### RAGManager 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `llm_client` | Any | None | LLM客户端实例（必须有embed方法） |
| `embed_function` | Callable | None | 自定义嵌入函数 |
| `provider` | str | "llm" | 嵌入提供者类型 ("llm", "function") |
| `collection_name` | str | "documents" | 向量集合名称 |
| `persist_directory` | str | "./chroma_db" | 持久化目录 |
| `chunk_size` | int | 1000 | 文本分块大小 |
| `chunk_overlap` | int | 200 | 分块重叠大小 |
| `splitter_type` | str | "recursive" | 文本分割器类型 |

### 支持的分割器类型

- `recursive`: 递归字符分割（通用）
- `token`: 基于Token的分割
- `markdown`: Markdown文档分割
- `python`: Python代码分割
- `javascript`: JavaScript代码分割
- `html`: HTML文档分割
- `latex`: LaTeX文档分割

## 自定义嵌入函数

```python
async def my_custom_embed(texts):
    """自定义嵌入函数示例"""
    # 您的嵌入逻辑
    embeddings = []
    for text in texts:
        # 调用您的嵌入服务
        embedding = your_embedding_service(text)
        embeddings.append(embedding)
    return embeddings

rag_manager = RAGManager(
    embed_function=my_custom_embed,
    provider="function"
)
```

## 文档管理

```python
# 获取文档信息
doc = await rag_manager.get_document_by_id("doc_id")

# 更新文档
await rag_manager.update_document(
    "doc_id",
    "新的文档内容",
    {"updated": True}
)

# 删除文档
await rag_manager.delete_documents(["doc_id_1", "doc_id_2"])

# 清空集合
await rag_manager.clear_collection()

# 获取集合信息
info = await rag_manager.get_collection_info()
```

## 数据导出

```python
# 导出数据到JSON文件
result = await rag_manager.export_data("./backup.json")
```

## 错误处理

```python
try:
    result = await rag_manager.add_documents(documents)
    if result["status"] == "error":
        print(f"添加失败: {result['message']}")
except Exception as e:
    print(f"发生异常: {str(e)}")
```

## 性能优化建议

1. **批量操作**: 尽量使用批量API而不是单个操作
2. **合适的分块大小**: 根据文档类型调整`chunk_size`
3. **异步操作**: 充分利用异步API提高并发性能
4. **索引策略**: 合理设置ChromaDB的索引参数

## 系统要求

- Python 3.8+
- ChromaDB
- 您的LLM客户端必须实现`embed`或`_embed`方法

## 安装依赖

```bash
pip install chromadb
# 根据需要安装其他依赖
pip install PyPDF2 python-docx beautifulsoup4 tiktoken
```

## 示例运行

查看 `examples/rag_usage_example.py` 获取完整的使用示例。

```bash
python examples/rag_usage_example.py
```

## 常见问题

### Q: 如何切换不同的嵌入提供者？

A: 使用 `update_embedding_provider` 方法：

```python
await rag_manager.update_embedding_provider(
    llm_client=new_llm_client,
    provider="llm"
)
```

### Q: 支持哪些文档格式？

A: 当前支持：PDF、Word（.docx）、Markdown、HTML、纯文本、JSON、CSV等。

### Q: 如何自定义文本分割策略？

A: 可以通过继承 `TextSplitter` 基类来实现自定义分割器。

### Q: 向量数据持久化在哪里？

A: 数据持久化在 `persist_directory` 指定的目录中，默认为 `./chroma_db`。

## 贡献

欢迎提交Issue和Pull Request来改进这个系统！ 