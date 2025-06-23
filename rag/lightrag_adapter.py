import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from .base_rag import BaseRAG, Document, SearchResult, EmbeddingProvider
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)
from lightrag import LightRAG, QueryParam
from lightrag.base import BaseKVStorage
LIGHTRAG_AVAILABLE = True



class LightRAGAdapter(BaseRAG):
    """LightRAG适配器，集成LightRAG图RAG功能"""
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        collection_name: str = "lightrag",
        working_dir: str = "./lightrag_storage",
        llm_config: Optional[Dict] = None,
        **kwargs
    ):
        if not LIGHTRAG_AVAILABLE:
            raise ImportError("LightRAG is not available. Please install with: pip install lightrag-hku")
        
        super().__init__(embedding_provider, collection_name, **kwargs)
        
        self.working_dir = working_dir
        self.llm_config = llm_config or {}
        
        # 确保工作目录存在
        os.makedirs(working_dir, exist_ok=True)
        
        # 初始化LightRAG
        self._init_lightrag()
        
        # 文档加载器
        self.document_loader = DocumentLoader()
        
        logger.info(f"LightRAG adapter initialized with working_dir: {working_dir}")
    
    def _init_lightrag(self):
        """初始化LightRAG实例"""
        try:
            # 基础配置
            config = {
                "working_dir": self.working_dir,
                **self.llm_config
            }
            
            self.lightrag = LightRAG(**config)
            logger.info("LightRAG instance created successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """添加文档到LightRAG"""
        try:
            total_docs = len(documents)
            successful_docs = 0
            failed_docs = []
            
            for i, doc in enumerate(documents):
                try:
                    # LightRAG的insert方法
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.lightrag.insert, doc.page_content
                    )
                    successful_docs += 1
                    logger.debug(f"Successfully inserted document {i+1}/{total_docs}")
                    
                except Exception as e:
                    logger.warning(f"Failed to insert document {doc.doc_id}: {e}")
                    failed_docs.append({
                        "doc_id": doc.doc_id,
                        "error": str(e)
                    })
            
            return {
                "status": "completed",
                "total_documents": total_docs,
                "successful_documents": successful_docs,
                "failed_documents": len(failed_docs),
                "failed_details": failed_docs
            }
            
        except Exception as e:
            logger.error(f"Error adding documents to LightRAG: {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        mode: str = "naive",
        **kwargs
    ) -> List[Document]:
        """使用LightRAG进行相似性搜索"""
        try:
            # 创建查询参数
            query_param = QueryParam(
                mode=mode,
                only_need_context=True,  # 只返回上下文，不需要生成回答
                top_k=k
            )
            
            # 执行查询
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.lightrag.query, query, query_param
            )
            
            # 解析结果并转换为Document格式
            documents = []
            if isinstance(result, str):
                # 如果返回的是字符串，创建单个文档
                doc = Document(
                    page_content=result,
                    metadata={
                        "source": "lightrag",
                        "query": query,
                        "mode": mode
                    }
                )
                documents.append(doc)
            
            return documents[:k]
            
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []
    
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        mode: str = "naive",
        **kwargs
    ) -> List[tuple[Document, float]]:
        """带评分的相似性搜索"""
        try:
            documents = await self.similarity_search(
                query, k, filter_metadata, mode, **kwargs
            )
            
            # LightRAG不直接返回评分，我们给一个默认评分
            scored_documents = []
            for i, doc in enumerate(documents):
                # 评分从高到低递减
                score = 1.0 - (i * 0.1)
                scored_documents.append((doc, max(score, 0.1)))
            
            return scored_documents
            
        except Exception as e:
            logger.error(f"Error during scored similarity search: {e}")
            return []
    
    async def query_with_generation(
        self,
        query: str,
        mode: str = "naive",
        stream: bool = False,
        **kwargs
    ) -> str:
        """使用LightRAG进行查询并生成回答"""
        try:
            query_param = QueryParam(
                mode=mode,
                stream=stream,
                **kwargs
            )
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.lightrag.query, query, query_param
            )
            
            return result if isinstance(result, str) else str(result)
            
        except Exception as e:
            logger.error(f"Error during query with generation: {e}")
            return f"Error: {str(e)}"
    
    async def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """删除文档（LightRAG不直接支持删除，返回警告）"""
        logger.warning("LightRAG does not support direct document deletion")
        return {
            "status": "not_supported",
            "message": "LightRAG does not support direct document deletion",
            "requested_deletions": len(doc_ids)
        }
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            # 检查工作目录的文件
            files = os.listdir(self.working_dir) if os.path.exists(self.working_dir) else []
            
            return {
                "collection_name": self.collection_name,
                "working_directory": self.working_dir,
                "storage_files": files,
                "status": "active"
            }
            
        except Exception as e:
            return {
                "collection_name": self.collection_name,
                "error": str(e),
                "status": "error"
            }
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """添加文本列表"""
        documents = []
        
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
        
        return await self.add_documents(documents)
    
    async def add_files(
        self,
        file_paths: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """添加文件"""
        try:
            all_documents = []
            
            for file_path in file_paths:
                try:
                    documents = self.document_loader.load_file_documents(file_path, metadata)
                    all_documents.extend(documents)
                except Exception as e:
                    logger.warning(f"Failed to load file {file_path}: {e}")
            
            if all_documents:
                return await self.add_documents(all_documents)
            else:
                return {
                    "status": "no_documents",
                    "message": "No documents were successfully loaded"
                }
                
        except Exception as e:
            logger.error(f"Error adding files: {e}")
            raise
    
    async def clear_collection(self) -> Dict[str, Any]:
        """清空集合（重新初始化LightRAG）"""
        try:
            # 删除工作目录
            import shutil
            if os.path.exists(self.working_dir):
                shutil.rmtree(self.working_dir)
            
            # 重新创建目录并初始化
            os.makedirs(self.working_dir, exist_ok=True)
            self._init_lightrag()
            
            return {
                "status": "cleared",
                "message": f"Collection {self.collection_name} cleared successfully"
            }
            
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def export_data(self, file_path: str) -> Dict[str, Any]:
        """导出数据"""
        try:
            import shutil
            
            # 复制整个工作目录
            if os.path.exists(self.working_dir):
                shutil.copytree(self.working_dir, file_path, dirs_exist_ok=True)
                
                return {
                    "status": "exported",
                    "export_path": file_path,
                    "source_directory": self.working_dir
                }
            else:
                return {
                    "status": "no_data",
                    "message": "No data to export"
                }
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_lightrag_instance(self) -> Optional[LightRAG]:
        """获取底层LightRAG实例，用于高级操作"""
        return self.lightrag if hasattr(self, 'lightrag') else None


def create_lightrag_adapter(
    embedding_provider: EmbeddingProvider,
    collection_name: str = "lightrag",
    working_dir: str = "./lightrag_storage",
    llm_config: Optional[Dict] = None,
    **kwargs
) -> LightRAGAdapter:
    """创建LightRAG适配器的工厂函数"""
    return LightRAGAdapter(
        embedding_provider=embedding_provider,
        collection_name=collection_name,
        working_dir=working_dir,
        llm_config=llm_config,
        **kwargs
    ) 