from .rag_manager import RAGManager
from .document_loader import DocumentLoader
from .base_rag import BaseRAG, Document, SearchResult, EmbeddingProvider
from .chroma_rag import ChromaRAG
from .embedding_adapters import (
    create_embedding_provider,
    LLMEmbeddingProvider,
    FunctionEmbeddingProvider,
    get_embedding_dimension
)
from .text_splitters import get_text_splitter, TextSplitter

# LightRAG组件（可选导入）
try:
    from .lightrag_adapter import LightRAGAdapter, create_lightrag_adapter, LIGHTRAG_AVAILABLE
    _LIGHTRAG_EXPORTS = [LightRAGAdapter, create_lightrag_adapter]
except ImportError:
    LIGHTRAG_AVAILABLE = False
    _LIGHTRAG_EXPORTS = []

__all__ = [
    "RAGManager",
    "DocumentLoader",
    "BaseRAG",
    "Document", 
    "SearchResult",
    "EmbeddingProvider",
    "ChromaRAG",
    "create_embedding_provider",
    "LLMEmbeddingProvider",
    "FunctionEmbeddingProvider",
    "get_embedding_dimension",
    "get_text_splitter",
    "TextSplitter",
    "LIGHTRAG_AVAILABLE"
] + [item.__name__ for item in _LIGHTRAG_EXPORTS]