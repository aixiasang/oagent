from typing import List, Dict, Any, Optional, Callable, Union
from .base_rag import EmbeddingProvider
import asyncio
import logging

logger = logging.getLogger(__name__)


class LLMEmbeddingProvider(EmbeddingProvider):
    """直接使用LLM客户端的嵌入功能"""
    
    def __init__(
        self,
        llm_client,
        batch_size: int = 32,
        max_retries: int = 3
    ):
        self.llm_client = llm_client
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        # 验证LLM客户端有嵌入功能
        if not (hasattr(llm_client, 'embed') or hasattr(llm_client, '_embed')):
            raise ValueError("LLM客户端必须实现embed或_embed方法")
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档嵌入"""
        if not texts:
            return []
        
        all_embeddings = []
        
        # 分批处理
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            for attempt in range(self.max_retries):
                try:
                    # 尝试使用embed方法 - 使用OpenAI API标准格式
                    if hasattr(self.llm_client, 'embed'):
                        if asyncio.iscoroutinefunction(self.llm_client.embed):
                            response = await self.llm_client.embed(input=batch)
                        else:
                            response = self.llm_client.embed(input=batch)
                    elif hasattr(self.llm_client, '_embed'):
                        if asyncio.iscoroutinefunction(self.llm_client._embed):
                            response = await self.llm_client._embed(input=batch)
                        else:
                            response = self.llm_client._embed(input=batch)
                    else:
                        raise ValueError("LLM客户端没有embed或_embed方法")
                    
                    # 解析响应格式
                    embeddings = self._parse_embedding_response(response)
                    
                    all_embeddings.extend(embeddings)
                    break
                    
                except Exception as e:
                    logger.warning(f"嵌入生成失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # 指数退避
        
        return all_embeddings
    
    async def embed_query(self, text: str) -> List[float]:
        """生成查询嵌入"""
        embeddings = await self.embed_documents([text])
        return embeddings[0] if embeddings else []
    
    def _parse_embedding_response(self, response) -> List[List[float]]:
        """解析嵌入响应的不同格式"""
        # 直接是嵌入列表
        if isinstance(response, list) and all(isinstance(item, list) for item in response):
            return response
        
        # OpenAI API响应格式
        if hasattr(response, 'data'):
            return [item.embedding for item in response.data]
        
        # 字典格式
        if isinstance(response, dict):
            if 'data' in response:
                return [item['embedding'] for item in response['data']]
            elif 'embeddings' in response:
                return response['embeddings']
        
        # 尝试直接使用
        if isinstance(response, list):
            return response
        
        raise ValueError(f"无法解析嵌入响应格式: {type(response)}")


class FunctionEmbeddingProvider(EmbeddingProvider):
    """使用自定义函数的嵌入提供者"""
    
    def __init__(
        self,
        embed_function: Callable,
        batch_size: int = 32,
        max_retries: int = 3
    ):
        self.embed_function = embed_function
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        if not callable(embed_function):
            raise ValueError("embed_function必须是可调用的")
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档嵌入"""
        if not texts:
            return []
        
        for attempt in range(self.max_retries):
            try:
                if asyncio.iscoroutinefunction(self.embed_function):
                    return await self.embed_function(texts)
                else:
                    return self.embed_function(texts)
            except Exception as e:
                logger.warning(f"自定义嵌入函数失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    async def embed_query(self, text: str) -> List[float]:
        """生成查询嵌入"""
        embeddings = await self.embed_documents([text])
        return embeddings[0] if embeddings else []


def create_embedding_provider(
    llm_client=None,
    embed_function=None,
    provider: str = "llm",
    **kwargs
) -> EmbeddingProvider:
    """创建嵌入提供者工厂函数"""
    
    if provider == "llm":
        if not llm_client:
            raise ValueError("使用llm提供者时必须提供llm_client")
        return LLMEmbeddingProvider(llm_client, **kwargs)
    
    elif provider == "function":
        if not embed_function:
            raise ValueError("使用function提供者时必须提供embed_function")
        return FunctionEmbeddingProvider(embed_function, **kwargs)
    
    else:
        raise ValueError(f"不支持的提供者类型: {provider}")



