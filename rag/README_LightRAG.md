# LightRAG 集成使用指南

本文档介绍如何在 oagent 框架中使用 LightRAG 进行图增强检索生成。

## 什么是 LightRAG？

LightRAG 是一个基于图的检索增强生成（RAG）框架，它通过构建知识图谱来理解文档中的实体关系，从而提供更精确和上下文相关的查询结果。与传统的向量RAG相比，LightRAG特别擅长处理需要理解实体间关系的复杂查询。

### 主要特点

- **图增强检索**: 通过知识图谱捕获实体间的复杂关系
- **多种查询模式**: 支持 naive、local、global 和 hybrid 模式
- **增量更新**: 支持动态添加新文档而无需重建整个图
- **双层检索**: 同时支持实体级和关系级检索

## 安装

```bash
pip install lightrag-hku
```

## 基础使用

### 1. 创建 LightRAG 管理器

```python
from oagent.rag import RAGManager
from oagent.config.llm import get_zhipuai_model

# 配置LLM
llm_config = get_zhipuai_model()

# 创建RAG管理器
rag_manager = RAGManager(
    rag_type="lightrag",  # 指定使用LightRAG
    collection_name="my_lightrag",
    persist_directory="./lightrag_storage",
    llm_config=llm_config,
    chunk_size=1000,
    chunk_overlap=200
)
```

### 2. 添加文档

```python
# 添加文本文档
documents = [
    {
        "content": "人工智能是计算机科学的一个分支...",
        "metadata": {"source": "ai_intro", "topic": "AI"}
    }
]

result = await rag_manager.add_documents(documents)
print(result)

# 添加文件
result = await rag_manager.add_file("document.pdf")

# 批量添加文件
result = await rag_manager.add_files(["doc1.txt", "doc2.pdf"])
```

### 3. 查询文档

#### 传统RAG查询（返回相关文档片段）

```python
# 获取相关文档片段
results = await rag_manager.query(
    "什么是机器学习？",
    top_k=5
)

for doc in results:
    print(f"内容: {doc['content']}")
    print(f"分数: {doc['score']}")
    print(f"元数据: {doc['metadata']}")
```

#### LightRAG生成式查询（返回完整答案）

```python
# 获取生成的完整答案
answer = await rag_manager.lightrag_query(
    "请解释人工智能、机器学习和深度学习之间的关系",
    mode="naive"
)

print(answer)
```

## LightRAG 查询模式

LightRAG 支持四种不同的查询模式：

### 1. Naive 模式
- 最基础的查询模式
- 适合简单的事实性问题
- 查询速度最快

```python
answer = await rag_manager.lightrag_query(
    "什么是机器学习？",
    mode="naive"
)
```

### 2. Local 模式
- 专注于局部实体和关系
- 适合查询特定实体的属性和直接关系
- 查询精度较高

```python
answer = await rag_manager.lightrag_query(
    "深度学习有哪些应用？",
    mode="local"
)
```

### 3. Global 模式
- 考虑全局知识图谱结构
- 适合需要理解多个实体间复杂关系的查询
- 查询最全面但速度较慢

```python
answer = await rag_manager.lightrag_query(
    "人工智能技术如何影响不同行业的发展？",
    mode="global"
)
```

### 4. Hybrid 模式
- 结合 local 和 global 模式的优势
- 平衡查询精度和覆盖范围
- 适合大多数复杂查询场景

```python
answer = await rag_manager.lightrag_query(
    "分析机器学习在医疗、金融和教育领域的具体应用",
    mode="hybrid"
)
```

## 高级功能

### 1. 获取底层 LightRAG 实例

```python
# 获取原始LightRAG实例进行高级操作
lightrag_instance = rag_manager.get_lightrag_instance()

if lightrag_instance:
    # 直接使用LightRAG的原生方法
    from lightrag import QueryParam
    
    result = lightrag_instance.query(
        "custom query",
        param=QueryParam(mode="local", top_k=10)
    )
```

### 2. 流式查询

```python
# 启用流式输出（如果LLM支持）
answer = await rag_manager.lightrag_query(
    "详细介绍深度学习的发展历程",
    mode="global",
    stream=True
)
```

### 3. 集合管理

```python
# 获取集合信息
info = await rag_manager.get_collection_info()
print(f"工作目录: {info['working_directory']}")
print(f"存储文件: {info['storage_files']}")

# 清空集合
result = await rag_manager.clear_collection()

# 导出数据
result = await rag_manager.export_data("./backup_dir")
```

## 配置不同的 LLM 后端

### 1. 智谱AI

```python
from oagent.config.llm import get_zhipuai_model

llm_config = get_zhipuai_model()
# 需要设置环境变量: zhipuai
```

### 2. SiliconFlow

```python
from oagent.config.llm import get_siliconflow_model

llm_config = get_siliconflow_model()
# 需要设置环境变量: SILICONFLOW_API_KEY
```

### 3. 字节跳动 ARK

```python
from oagent.config.llm import get_ark_model

llm_config = get_ark_model()
# 需要设置环境变量: ARK_API_KEY
```

### 4. 阿里云

```python
from oagent.config.llm import get_ali_model

llm_config = get_ali_model()
# 需要设置环境变量: DASHSCOPE_API_KEY
```

## 最佳实践

### 1. 文档准备
- 确保文档内容结构清晰，包含明确的实体和关系
- 适当分割长文档，但保持语义完整性
- 为文档添加有意义的元数据

### 2. 查询优化
- 使用具体、明确的查询问题
- 根据查询复杂度选择合适的模式
- 对于关系型查询优先使用 global 或 hybrid 模式

### 3. 性能考虑
- LightRAG 的知识图谱构建需要时间，添加文档后要等待处理完成
- Global 模式查询耗时较长，在实时应用中需要考虑超时设置
- 定期导出数据作为备份

### 4. 错误处理

```python
try:
    answer = await rag_manager.lightrag_query(query, mode="global")
except Exception as e:
    print(f"查询失败: {e}")
    # 降级到更简单的模式
    answer = await rag_manager.lightrag_query(query, mode="naive")
```

## 与 ChromaRAG 的对比

| 特性 | ChromaRAG | LightRAG |
|------|-----------|----------|
| 索引类型 | 向量索引 | 知识图谱 + 向量索引 |
| 查询类型 | 相似性检索 | 关系查询 + 生成式回答 |
| 适用场景 | 简单事实查询 | 复杂关系查询 |
| 处理速度 | 快 | 中等（图构建较慢） |
| 存储需求 | 低 | 中等 |
| 实体关系理解 | 弱 | 强 |

## 故障排除

### 1. 安装问题

```bash
# 如果安装失败，尝试指定源
pip install lightrag-hku -i https://pypi.org/simple/
```

### 2. LLM 配置问题

```python
# 检查 LightRAG 是否可用
from oagent.rag import LIGHTRAG_AVAILABLE

if not LIGHTRAG_AVAILABLE:
    print("LightRAG 不可用，请检查安装")
```

### 3. 内存不足

- 减少 `chunk_size` 参数
- 使用更少的 `top_k` 值
- 分批处理大量文档

### 4. 查询超时

```python
# 设置较短的超时时间或使用更简单的查询模式
answer = await rag_manager.lightrag_query(
    query,
    mode="naive"  # 使用更快的模式
)
```

## 示例代码

完整的使用示例请参考 `examples/lightrag_example.py` 文件。

## 支持的功能列表

✅ 支持的功能：
- 文档添加和处理
- 多种查询模式
- 增量更新
- 文件处理（txt, pdf, md等）
- 集合管理
- 数据导出

❌ 暂不支持的功能：
- 文档删除（LightRAG限制）
- 实时流式处理
- 分布式部署

## 更多资源

- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [LightRAG 论文](https://arxiv.org/abs/2410.05779)
- [oagent 文档](../README.md) 