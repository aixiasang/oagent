import os
import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, Union, Callable
from .base_rag import BaseRAG, Document, SearchResult, EmbeddingProvider
from .chroma_rag import ChromaRAG
from .embedding_adapters import create_embedding_provider
from .document_loader import DocumentLoader

try:
    from .lightrag_adapter import LightRAGAdapter, create_lightrag_adapter, LIGHTRAG_AVAILABLE
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAGAdapter = None
    create_lightrag_adapter = None

logger = logging.getLogger(__name__)


class RAGManager:
    """RAG管理器 - 统一的RAG接口"""
    
    def __init__(
        self,
        llm_client=None,
        embed_function: Optional[Callable] = None,
        provider: str = "llm",
        rag_type: str = "chroma",  # 添加RAG类型选择
        collection_name: str = "documents",
        persist_directory: str = "./chroma_db",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        splitter_type: str = "recursive",
        llm_config: Optional[Dict] = None,  # LightRAG需要的LLM配置
        **kwargs
    ):
        """
        初始化RAG管理器
        
        Args:
            llm_client: LLM客户端实例（必须有embed方法）
            embed_function: 自定义嵌入函数
            provider: 嵌入提供者 ("llm", "function")
            rag_type: RAG类型 ("chroma", "lightrag")
            collection_name: 集合名称
            persist_directory: 持久化目录
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            splitter_type: 分割器类型
            llm_config: LightRAG需要的LLM配置
        """
        self.llm_client = llm_client
        self.embed_function = embed_function
        self.provider = provider
        self.rag_type = rag_type
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.llm_config = llm_config or {}
        
        # 根据rag_type创建不同的RAG实例
        if rag_type == "lightrag":
            if not LIGHTRAG_AVAILABLE:
                raise ImportError("LightRAG is not available. Please install with: pip install lightrag-hku")
            
            # 创建嵌入提供者（LightRAG可能不需要，但保持接口一致）
            if llm_client or embed_function:
                try:
                    self.embedding_provider = create_embedding_provider(
                        llm_client=llm_client,
                        embed_function=embed_function,
                        provider=provider,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"创建嵌入提供者失败，LightRAG将使用内置嵌入: {str(e)}")
                    self.embedding_provider = None
            else:
                self.embedding_provider = None
            
            # 创建LightRAG实例
            self.rag = LightRAGAdapter(
                embedding_provider=self.embedding_provider,
                collection_name=collection_name,
                working_dir=persist_directory,
                llm_config=self.llm_config,
                **kwargs
            )
        else:
            # 默认使用ChromaRAG
            # 创建嵌入提供者
            try:
                self.embedding_provider = create_embedding_provider(
                    llm_client=llm_client,
                    embed_function=embed_function,
                    provider=provider,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"创建嵌入提供者失败: {str(e)}")
                raise
            
            # 创建ChromaRAG实例
            self.rag = ChromaRAG(
                embedding_provider=self.embedding_provider,
                collection_name=collection_name,
                persist_directory=persist_directory,
                **kwargs
            )
        
        # 文档加载器
        self.document_loader = DocumentLoader(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_type=splitter_type
        )
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """添加文档"""
        try:
            # 转换为Document对象
            doc_objects = []
            for doc in documents:
                if isinstance(doc, dict):
                    content = doc.get('content', '')
                    metadata = doc.get('metadata', {})
                    doc_id = doc.get('id')
                    
                    if not content.strip():
                        continue
                        
                    doc_obj = Document(
                        page_content=content,
                        metadata=metadata,
                        doc_id=doc_id if doc_id else str(uuid.uuid4())
                    )
                    doc_objects.append(doc_obj)
                elif isinstance(doc, Document):
                    doc_objects.append(doc)
            
            if not doc_objects:
                return {"status": "success", "message": "没有有效的文档可添加", "added_count": 0}
            
            return await self.rag.add_documents(doc_objects)
            
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return {"status": "error", "message": f"添加文档失败: {str(e)}"}
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """添加文本列表"""
        try:
            return await self.rag.add_texts(texts, metadatas)
        except Exception as e:
            logger.error(f"添加文本失败: {str(e)}")
            return {"status": "error", "message": f"添加文本失败: {str(e)}"}
    
    async def add_file(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """添加单个文件"""
        return await self.add_files([file_path], metadata)
    
    async def add_files(self, file_paths: List[str], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """批量添加文件"""
        try:
            all_documents = []
            
            for file_path in file_paths:
                try:
                    documents = self.document_loader.load_file_documents(file_path, metadata)
                    all_documents.extend(documents)
                except Exception as e:
                    logger.warning(f"加载文件 {file_path} 失败: {str(e)}")
                    continue
            
            if not all_documents:
                return {"status": "error", "message": "没有成功加载任何文件"}
            
            return await self.rag.add_documents(all_documents)
            
        except Exception as e:
            logger.error(f"批量添加文件失败: {str(e)}")
            return {"status": "error", "message": f"批量添加文件失败: {str(e)}"}
    
    async def add_url(self, url: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """添加单个网页"""
        return await self.add_urls([url], metadata)
    
    async def add_urls(self, urls: List[str], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """批量添加网页"""
        try:
            all_documents = []
            
            for url in urls:
                try:
                    documents = self.document_loader.load_url_documents(url, metadata)
                    all_documents.extend(documents)
                except Exception as e:
                    logger.warning(f"加载URL {url} 失败: {str(e)}")
                    continue
            
            if not all_documents:
                return {"status": "error", "message": "没有成功加载任何URL"}
            
            return await self.rag.add_documents(all_documents)
            
        except Exception as e:
            logger.error(f"批量添加URL失败: {str(e)}")
            return {"status": "error", "message": f"批量添加URL失败: {str(e)}"}
    
    async def add_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*",
        exclude_patterns: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """批量添加目录中的文件"""
        try:
            documents = self.document_loader.load_directory(
                directory_path,
                glob_pattern,
                exclude_patterns,
                metadata
            )
            
            if not documents:
                return {"status": "error", "message": f"目录 {directory_path} 中没有找到有效文档"}
            
            return await self.rag.add_documents(documents)
            
        except Exception as e:
            logger.error(f"添加目录失败: {str(e)}")
            return {"status": "error", "message": f"添加目录失败: {str(e)}"}
    
    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """查询相关文档"""
        try:
            documents = await self.rag.similarity_search(
                query_text, k=top_k, filter_metadata=filter_metadata, **kwargs
            )
            
            # 转换为字典格式
            results = []
            for i, doc in enumerate(documents):
                results.append({
                    "id": doc.doc_id,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "rank": i + 1
                })
            
            return results
            
        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return []
    
    async def search_with_score(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """带分数的查询"""
        try:
            results = await self.rag.similarity_search_with_score(
                query_text, k=top_k, filter_metadata=filter_metadata, **kwargs
            )
            
            # 转换为字典格式
            formatted_results = []
            for i, (doc, score) in enumerate(results):
                formatted_results.append({
                    "id": doc.doc_id,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score,
                    "rank": i + 1
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"带分数查询失败: {str(e)}")
            return []
    
    async def search_with_rerank(
        self,
        query_text: str,
        k: int = 10,
        rerank_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """带重排序的搜索"""
        try:
            results = await self.rag.search_with_rerank(
                query_text, k, rerank_k, filter_metadata, **kwargs
            )
            
            # 转换为字典格式
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.doc_id,
                    "content": result.content,
                    "metadata": result.metadata,
                    "score": result.score,
                    "rank": result.rank
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"重排序搜索失败: {str(e)}")
            return []
    
    async def generate_context(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        max_context_length: int = 4000
    ) -> str:
        """生成RAG上下文"""
        try:
            return await self.rag.generate_context(
                query_text, top_k, filter_metadata, max_context_length
            )
        except Exception as e:
            logger.error(f"生成上下文失败: {str(e)}")
            return ""
    
    async def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """删除文档"""
        try:
            return await self.rag.delete_documents(doc_ids)
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {"status": "error", "message": f"删除文档失败: {str(e)}"}
    
    async def clear_collection(self) -> Dict[str, Any]:
        """清空集合"""
        try:
            return await self.rag.clear_collection()
        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return {"status": "error", "message": f"清空集合失败: {str(e)}"}
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            info = await self.rag.get_collection_info()
            info.update({
                "provider": self.provider,
                "has_llm_client": self.llm_client is not None,
                "has_embed_function": self.embed_function is not None,
                "chunk_size": self.document_loader.chunk_size,
                "chunk_overlap": self.document_loader.chunk_overlap,
                "splitter_type": self.document_loader.splitter_type
            })
            return info
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {"status": "error", "message": f"获取集合信息失败: {str(e)}"}
    
    async def export_data(self, file_path: str) -> Dict[str, Any]:
        """导出数据"""
        try:
            return await self.rag.export_data(file_path)
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            return {"status": "error", "message": f"导出数据失败: {str(e)}"}
    
    async def update_embedding_provider(
        self,
        llm_client=None,
        embed_function=None,
        provider: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """更新嵌入提供者"""
        try:
            if provider:
                self.provider = provider
            if embed_function:
                self.embed_function = embed_function
            if llm_client:
                self.llm_client = llm_client
            
            # 重新创建嵌入提供者
            self.embedding_provider = create_embedding_provider(
                llm_client=self.llm_client,
                embed_function=self.embed_function,
                provider=self.provider,
                **kwargs
            )
            
            # 更新RAG实例的嵌入提供者
            self.rag.embedding_provider = self.embedding_provider
            
            return {
                "status": "success",
                "message": f"嵌入提供者已更新为 {self.provider}"
            }
            
        except Exception as e:
            logger.error(f"更新嵌入提供者失败: {str(e)}")
            return {"status": "error", "message": f"更新嵌入提供者失败: {str(e)}"}
    
    def get_supported_providers(self) -> List[str]:
        """获取支持的嵌入提供者"""
        return ["llm", "function"]
    
    def get_supported_rag_types(self) -> List[str]:
        """获取支持的RAG类型"""
        types = ["chroma"]
        if LIGHTRAG_AVAILABLE:
            types.append("lightrag")
        return types
    
    def get_supported_splitters(self) -> List[str]:
        """获取支持的文本分割器"""
        return ["recursive", "token", "markdown", "python", "javascript", "html", "latex"]
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        try:
            if hasattr(self.rag, 'get_document_by_id'):
                doc = await self.rag.get_document_by_id(doc_id)
                if doc:
                    return {
                        "id": doc.doc_id,
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
            return None
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None
    
    async def update_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """更新文档"""
        try:
            if hasattr(self.rag, 'update_document'):
                doc = Document(
                    page_content=content,
                    metadata=metadata or {},
                    doc_id=doc_id
                )
                return await self.rag.update_document(doc_id, doc)
            else:
                return {"status": "error", "message": "当前RAG实现不支持文档更新"}
        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            return {"status": "error", "message": f"更新文档失败: {str(e)}"}
    
    async def lightrag_query(
        self,
        query: str,
        mode: str = "naive",
        stream: bool = False,
        **kwargs
    ) -> str:
        """LightRAG专用查询方法，返回生成的回答"""
        if self.rag_type != "lightrag":
            logger.warning("lightrag_query只能在rag_type='lightrag'时使用")
            return "Error: This method only works with LightRAG"
        
        try:
            if hasattr(self.rag, 'query_with_generation'):
                return await self.rag.query_with_generation(
                    query=query,
                    mode=mode,
                    stream=stream,
                    **kwargs
                )
            else:
                return "Error: LightRAG adapter does not support query_with_generation"
        except Exception as e:
            logger.error(f"LightRAG查询失败: {str(e)}")
            return f"Error: {str(e)}"
    
    def get_lightrag_instance(self):
        """获取底层LightRAG实例（仅在使用LightRAG时可用）"""
        if self.rag_type == "lightrag" and hasattr(self.rag, 'get_lightrag_instance'):
            return self.rag.get_lightrag_instance()
        return None
    
    # 同步包装方法，保持向后兼容
    def add_documents_sync(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """同步添加文档（向后兼容）"""
        return asyncio.run(self.add_documents(documents))
    
    def query_sync(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """同步查询（向后兼容）"""
        return asyncio.run(self.query(query_text, top_k, filter_metadata, **kwargs)) 