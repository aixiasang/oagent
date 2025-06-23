from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union, Protocol
import uuid
from datetime import datetime
from dataclasses import dataclass, field


class EmbeddingProvider(Protocol):
    """嵌入提供者协议"""
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档嵌入"""
        ...
    
    async def embed_query(self, text: str) -> List[float]:
        """生成查询嵌入"""
        ...


@dataclass
class Document:
    """文档类"""
    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        # 确保基础元数据存在
        if not self.metadata:
            self.metadata = {}
        
        # 添加创建时间
        if "created_at" not in self.metadata:
            self.metadata["created_at"] = datetime.now().isoformat()
        
        # 添加内容长度
        self.metadata["content_length"] = len(self.page_content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.doc_id,
            "content": self.page_content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """从字典创建Document实例"""
        return cls(
            page_content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            doc_id=data.get("id", str(uuid.uuid4()))
        )


@dataclass 
class SearchResult:
    """搜索结果类"""
    doc_id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
            "rank": self.rank
        }


class BaseRAG(ABC):
    """RAG基础抽象类"""
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        collection_name: str = "documents",
        **kwargs
    ):
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.config = kwargs
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """添加文档到向量数据库"""
        pass
    
    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """相似度搜索"""
        pass
    
    @abstractmethod
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """带分数的相似度搜索"""
        pass
    
    @abstractmethod
    async def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """删除文档"""
        pass
    
    @abstractmethod
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        pass
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """添加文本列表"""
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if i < len(metadatas) else {}
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
        
        return await self.add_documents(documents)
    
    async def search_with_rerank(
        self,
        query: str,
        k: int = 10,
        rerank_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[SearchResult]:
        """带重排序的搜索"""
        # 先获取更多候选结果
        results = await self.similarity_search_with_score(
            query, k=k, filter_metadata=filter_metadata, **kwargs
        )
        
        # 简单的重排序（可以在子类中实现更复杂的逻辑）
        search_results = []
        for i, (doc, score) in enumerate(results[:rerank_k]):
            search_results.append(SearchResult(
                doc_id=doc.doc_id,
                content=doc.page_content,
                metadata=doc.metadata,
                score=score,
                rank=i + 1
            ))
        
        return search_results
    
    async def generate_context(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        max_context_length: int = 4000,
        separator: str = "\n\n"
    ) -> str:
        """生成RAG上下文"""
        documents = await self.similarity_search(
            query, k=k, filter_metadata=filter_metadata
        )
        
        context_parts = []
        current_length = 0
        
        for doc in documents:
            content = doc.page_content.strip()
            if not content:
                continue
            
            # 检查添加这段内容是否会超过限制
            part_length = len(content) + len(separator)
            if current_length + part_length > max_context_length and context_parts:
                break
            
            context_parts.append(content)
            current_length += part_length
        
        return separator.join(context_parts)
    
    async def clear_collection(self) -> Dict[str, Any]:
        """清空集合（默认实现）"""
        return {
            "status": "error",
            "message": "clear_collection 方法未在子类中实现"
        }
    
    async def export_data(self, file_path: str) -> Dict[str, Any]:
        """导出数据（默认实现）"""
        return {
            "status": "error", 
            "message": "export_data 方法未在子类中实现"
        } 