from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class Retriever:
    """文档检索器"""
    
    def __init__(self, collection, embedding_model: SentenceTransformer):
        self.collection = collection
        self.embedding_model = embedding_model
    
    def retrieve(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query_text: 查询文本
            top_k: 返回的文档数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            相关文档列表，包含内容、元数据和相关度分数
        """
        # 生成查询向量
        query_embedding = self.embedding_model.encode([query_text])[0].tolist()
        
        # 构建查询参数
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k
        }
        
        # 添加元数据过滤
        if filter_metadata:
            query_kwargs["where"] = filter_metadata
        
        # 执行查询
        results = self.collection.query(**query_kwargs)
        
        # 格式化结果
        formatted_results = []
        if results and results['documents']:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
            distances = results['distances'][0] if results['distances'] else [0] * len(documents)
            ids = results['ids'][0] if results['ids'] else [''] * len(documents)
            
            for i in range(len(documents)):
                # 将距离转换为相似度分数 (1 - normalized_distance)
                # ChromaDB使用的是余弦距离，范围是[0, 2]
                score = 1 - (distances[i] / 2)
                
                formatted_results.append({
                    'id': ids[i],
                    'content': documents[i],
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'score': score,
                    'distance': distances[i]
                })
        
        # 按相关度排序
        formatted_results.sort(key=lambda x: x['score'], reverse=True)
        
        return formatted_results
    
    def retrieve_with_rerank(
        self,
        query_text: str,
        top_k: int = 10,
        rerank_top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        检索并重排序文档
        
        Args:
            query_text: 查询文本
            top_k: 初始检索的文档数量
            rerank_top_k: 重排序后返回的文档数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            重排序后的文档列表
        """
        # 初始检索
        initial_results = self.retrieve(query_text, top_k, filter_metadata)
        
        if not initial_results:
            return []
        
        # 使用更精细的相似度计算进行重排序
        # 这里使用简单的关键词匹配增强，实际可以使用更复杂的重排序模型
        query_words = set(query_text.lower().split())
        
        for result in initial_results:
            content_words = set(result['content'].lower().split())
            keyword_overlap = len(query_words & content_words) / len(query_words) if query_words else 0
            
            # 组合原始分数和关键词重叠度
            result['rerank_score'] = result['score'] * 0.7 + keyword_overlap * 0.3
        
        # 按重排序分数排序
        initial_results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        # 返回前N个结果
        return initial_results[:rerank_top_k] 