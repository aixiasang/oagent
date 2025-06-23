import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError:
    raise ImportError("请安装chromadb: pip install chromadb")

from .base_rag import BaseRAG, Document, SearchResult, EmbeddingProvider
from .document_loader import DocumentLoader

logger = logging.getLogger(__name__)


class ChromaRAG(BaseRAG):
    """基于ChromaDB的RAG实现"""
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        collection_name: str = "documents",
        persist_directory: str = "./chroma_db",
        **kwargs
    ):
        super().__init__(embedding_provider, collection_name, **kwargs)
        self.persist_directory = persist_directory
        self.max_batch_size = kwargs.get("max_batch_size", 100)
        self.distance_threshold = kwargs.get("distance_threshold", 0.7)
        
        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化ChromaDB客户端
        self._client = None
        self._collection = None
        self._initialize_client()
        
        # 文档加载器
        chunk_size = kwargs.get('chunk_size', 1000)
        chunk_overlap = kwargs.get('chunk_overlap', 200)
        splitter_type = kwargs.get('splitter_type', 'recursive')
        
        self.document_loader = DocumentLoader(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_type=splitter_type
        )
    
    def _initialize_client(self):
        """初始化ChromaDB客户端和集合"""
        try:
            # 创建ChromaDB客户端
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # 获取或创建集合
            try:
                self._collection = self._client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"已连接到现有集合: {self.collection_name}")
            except Exception:
                # 集合不存在，创建新集合
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"已创建新集合: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"初始化ChromaDB失败: {str(e)}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """添加文档到向量数据库"""
        if not documents:
            return {"status": "success", "message": "没有要添加的文档", "added_count": 0}
        
        try:
            # 准备数据
            ids = []
            texts = []
            metadatas = []
            
            for doc in documents:
                if not doc.page_content.strip():
                    continue
                    
                ids.append(doc.doc_id)
                texts.append(doc.page_content)
                
                # 准备元数据（ChromaDB要求所有值都是基本类型）
                metadata = self._prepare_metadata(doc.metadata)
                metadatas.append(metadata)
            
            if not texts:
                return {"status": "success", "message": "没有有效内容的文档", "added_count": 0}
            
            # 分批生成嵌入
            all_embeddings = []
            for i in range(0, len(texts), self.max_batch_size):
                batch_texts = texts[i:i + self.max_batch_size]
                try:
                    batch_embeddings = await self.embedding_provider.embed_documents(batch_texts)
                    all_embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(f"生成嵌入失败: {str(e)}")
                    return {"status": "error", "message": f"嵌入生成失败: {str(e)}"}
            
            if len(all_embeddings) != len(texts):
                return {"status": "error", "message": "嵌入数量与文档数量不匹配"}
            
            # 分批添加到ChromaDB
            added_count = 0
            for i in range(0, len(ids), self.max_batch_size):
                batch_end = min(i + self.max_batch_size, len(ids))
                
                try:
                    self._collection.upsert(
                        ids=ids[i:batch_end],
                        documents=texts[i:batch_end],
                        embeddings=all_embeddings[i:batch_end],
                        metadatas=metadatas[i:batch_end]
                    )
                    added_count += (batch_end - i)
                except Exception as e:
                    logger.error(f"批量添加失败: {str(e)}")
                    return {"status": "error", "message": f"添加文档失败: {str(e)}"}
            
            logger.info(f"成功添加 {added_count} 个文档到集合 {self.collection_name}")
            return {
                "status": "success",
                "message": f"成功添加 {added_count} 个文档",
                "added_count": added_count
            }
            
        except Exception as e:
            logger.error(f"添加文档时发生错误: {str(e)}")
            return {"status": "error", "message": f"添加文档失败: {str(e)}"}
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """相似度搜索"""
        try:
            # 生成查询嵌入
            query_embedding = await self.embedding_provider.embed_query(query)
            
            # 构建查询参数
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            # 添加过滤条件
            if filter_metadata:
                query_params["where"] = filter_metadata
            
            # 执行查询
            results = self._collection.query(**query_params)
            
            # 转换结果
            documents = []
            if results and results['documents'] and results['documents'][0]:
                docs_data = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs_data)
                distances = results['distances'][0] if results['distances'] else [0] * len(docs_data)
                ids = results['ids'][0] if results['ids'] else [f"doc_{i}" for i in range(len(docs_data))]
                
                for i, (doc_content, metadata, distance, doc_id) in enumerate(
                    zip(docs_data, metadatas, distances, ids)
                ):
                    # 过滤距离阈值
                    if distance > self.distance_threshold:
                        continue
                    
                    # 添加搜索相关信息到元数据
                    search_metadata = metadata.copy() if metadata else {}
                    search_metadata.update({
                        "search_score": 1 - distance,  # 转换为相似度分数
                        "search_distance": distance,
                        "search_rank": i + 1
                    })
                    
                    documents.append(Document(
                        page_content=doc_content,
                        metadata=search_metadata,
                        doc_id=doc_id
                    ))
            
            return documents
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            return []
    
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[Document, float]]:
        """带分数的相似度搜索"""
        try:
            # 生成查询嵌入
            query_embedding = await self.embedding_provider.embed_query(query)
            
            # 构建查询参数
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if filter_metadata:
                query_params["where"] = filter_metadata
            
            # 执行查询
            results = self._collection.query(**query_params)
            
            # 转换结果
            scored_documents = []
            if results and results['documents'] and results['documents'][0]:
                docs_data = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs_data)
                distances = results['distances'][0] if results['distances'] else [0] * len(docs_data)
                ids = results['ids'][0] if results['ids'] else [f"doc_{i}" for i in range(len(docs_data))]
                
                for doc_content, metadata, distance, doc_id in zip(docs_data, metadatas, distances, ids):
                    if distance > self.distance_threshold:
                        continue
                    
                    score = 1 - distance  # 转换为相似度分数
                    
                    document = Document(
                        page_content=doc_content,
                        metadata=metadata or {},
                        doc_id=doc_id
                    )
                    
                    scored_documents.append((document, score))
            
            return scored_documents
            
        except Exception as e:
            logger.error(f"带分数搜索失败: {str(e)}")
            return []
    
    async def delete_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """删除文档"""
        if not doc_ids:
            return {"status": "success", "message": "没有要删除的文档", "deleted_count": 0}
        
        try:
            # 检查文档是否存在
            existing_results = self._collection.get(ids=doc_ids, include=[])
            existing_ids = existing_results['ids'] if existing_results else []
            
            if not existing_ids:
                return {"status": "success", "message": "没有找到要删除的文档", "deleted_count": 0}
            
            # 删除文档
            self._collection.delete(ids=existing_ids)
            
            logger.info(f"成功删除 {len(existing_ids)} 个文档")
            return {
                "status": "success",
                "message": f"成功删除 {len(existing_ids)} 个文档",
                "deleted_count": len(existing_ids)
            }
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {"status": "error", "message": f"删除文档失败: {str(e)}"}
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            # 获取集合统计信息
            count = self._collection.count()
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory,
                "distance_threshold": self.distance_threshold,
                "max_batch_size": self.max_batch_size,
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "status": "error",
                "error": str(e)
            }
    
    async def clear_collection(self) -> Dict[str, Any]:
        """清空集合"""
        try:
            # 删除现有集合
            self._client.delete_collection(name=self.collection_name)
            
            # 重新创建集合
            self._collection = self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            return {
                "status": "success",
                "message": f"已清空集合 {self.collection_name}"
            }
            
        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return {"status": "error", "message": f"清空集合失败: {str(e)}"}
    
    async def export_data(self, file_path: str) -> Dict[str, Any]:
        """导出数据"""
        try:
            # 获取所有数据
            results = self._collection.get(include=["documents", "metadatas", "embeddings"])
            
            export_data = {
                "collection_name": self.collection_name,
                "export_time": datetime.now().isoformat(),
                "document_count": len(results['ids']) if results['ids'] else 0,
                "documents": []
            }
            
            if results['ids']:
                for i, doc_id in enumerate(results['ids']):
                    doc_data = {
                        "id": doc_id,
                        "content": results['documents'][i] if i < len(results['documents']) else "",
                        "metadata": results['metadatas'][i] if i < len(results['metadatas']) else {},
                        "embedding": results['embeddings'][i] if results['embeddings'] and i < len(results['embeddings']) else None
                    }
                    export_data["documents"].append(doc_data)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return {
                "status": "success",
                "message": f"数据已导出到 {file_path}",
                "exported_count": export_data["document_count"]
            }
            
        except Exception as e:
            logger.error(f"导出数据失败: {str(e)}")
            return {"status": "error", "message": f"导出数据失败: {str(e)}"}
    
    def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """准备元数据，确保兼容ChromaDB"""
        clean_metadata = {}
        
        for key, value in metadata.items():
            # ChromaDB支持的类型: str, int, float, bool
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif value is None:
                clean_metadata[key] = ""
            else:
                # 转换复杂类型为字符串
                clean_metadata[key] = str(value)
        
        return clean_metadata
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        try:
            results = self._collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results['ids'] and len(results['ids']) > 0:
                return Document(
                    page_content=results['documents'][0],
                    metadata=results['metadatas'][0] if results['metadatas'] else {},
                    doc_id=results['ids'][0]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"获取文档失败: {str(e)}")
            return None
    
    async def update_document(self, doc_id: str, document: Document) -> Dict[str, Any]:
        """更新文档"""
        try:
            # 生成新的嵌入
            embedding = await self.embedding_provider.embed_query(document.page_content)
            
            # 更新文档
            self._collection.upsert(
                ids=[doc_id],
                documents=[document.page_content],
                embeddings=[embedding],
                metadatas=[self._prepare_metadata(document.metadata)]
            )
            
            return {
                "status": "success",
                "message": f"文档 {doc_id} 更新成功"
            }
            
        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            return {"status": "error", "message": f"更新文档失败: {str(e)}"}
    
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """添加文本列表"""
        documents = []
        metadatas = metadatas or [{}] * len(texts)
        
        for i, text in enumerate(texts):
            doc = Document(
                page_content=text,
                metadata=metadatas[i]
            )
            documents.append(doc)
        
        return await self.add_documents(documents)
    
    def add_files(
        self,
        file_paths: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """批量添加文件"""
        try:
            all_documents = []
            
            for file_path in file_paths:
                docs = self.document_loader.load_file_documents(file_path, metadata)
                all_documents.extend(docs)
            
            return self.add_documents(all_documents)
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"添加文件失败: {str(e)}"
            }
    
    def add_urls(
        self,
        urls: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """批量添加网页"""
        try:
            all_documents = []
            
            for url in urls:
                docs = self.document_loader.load_url_documents(url, metadata)
                all_documents.extend(docs)
            
            return self.add_documents(all_documents)
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"添加网页失败: {str(e)}"
            }
    
    async def search_with_rerank(
        self,
        query: str,
        k: int = 10,
        rerank_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        rerank_threshold: float = 0.5
    ) -> List[SearchResult]:
        """带重排序的搜索"""
        # 先获取更多候选结果
        candidates = await self.similarity_search_with_score(
            query, k=k, filter_metadata=filter_metadata
        )
        
        if not candidates:
            return []
        
        # 简单的重排序策略：基于分数和文本长度
        def rerank_score(doc_score_pair):
            doc, score = doc_score_pair
            # 考虑原始分数和文本长度
            length_penalty = min(len(doc.page_content) / 1000, 1.0)  # 适中长度的文档更好
            return score * 0.7 + length_penalty * 0.3
        
        # 重新排序
        reranked = sorted(candidates, key=rerank_score, reverse=True)
        
        # 过滤低分结果并返回top-k
        results = []
        for i, (doc, score) in enumerate(reranked[:rerank_k]):
            if score >= rerank_threshold:
                results.append(SearchResult(
                    doc_id=doc.doc_id,
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=score,
                    rank=i + 1
                ))
        
        return results
    
    async def generate_context(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None,
        max_context_length: int = 4000
    ) -> str:
        """生成RAG上下文"""
        results = await self.search_with_rerank(
            query, k=k, filter_metadata=filter_metadata
        )
        
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        
        for result in results:
            content = result.content
            
            # 检查是否会超出最大长度
            if total_length + len(content) > max_context_length:
                # 截断最后一个文档
                remaining_length = max_context_length - total_length
                if remaining_length > 100:  # 至少保留100字符
                    content = content[:remaining_length] + "..."
                else:
                    break
            
            context_parts.append(f"[文档{result.rank}] {content}")
            total_length += len(content)
            
            if total_length >= max_context_length:
                break
        
        return "\n\n".join(context_parts) 