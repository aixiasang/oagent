from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import re
import tiktoken
from .base_rag import Document


class TextSplitter(ABC):
    """文本分割器基类"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function: callable = len,
        keep_separator: bool = False,
        add_start_index: bool = False,
        strip_whitespace: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.keep_separator = keep_separator
        self.add_start_index = add_start_index
        self.strip_whitespace = strip_whitespace
    
    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        pass
    
    def create_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> List[Document]:
        """创建文档对象"""
        documents = []
        metadatas = metadatas or [{}] * len(texts)
        
        for i, text in enumerate(texts):
            chunks = self.split_text(text)
            for j, chunk in enumerate(chunks):
                metadata = metadatas[i].copy()
                metadata.update({
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                    "source_index": i
                })
                
                if self.add_start_index:
                    metadata["start_index"] = text.find(chunk)
                
                documents.append(Document(
                    page_content=chunk,
                    metadata=metadata
                ))
        
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割文档"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.create_documents(texts, metadatas)


class RecursiveCharacterTextSplitter(TextSplitter):
    """递归字符文本分割器"""
    
    def __init__(
        self,
        separators: Optional[List[str]] = None,
        is_separator_regex: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.separators = separators or ["\n\n", "\n", " ", ""]
        self.is_separator_regex = is_separator_regex
    
    def split_text(self, text: str) -> List[str]:
        """递归分割文本"""
        return self._split_text(text, self.separators)
    
    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """递归分割实现"""
        final_chunks = []
        separator = separators[-1]
        new_separators = []
        
        for i, _s in enumerate(separators):
            _separator = _s if self.is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_separator, text):
                separator = _s
                new_separators = separators[i + 1:]
                break
        
        _separator = separator if self.is_separator_regex else re.escape(separator)
        splits = self._split_text_with_regex(text, _separator, self.keep_separator)
        
        _good_splits = []
        _separator = "" if self.keep_separator else separator
        
        for s in splits:
            if self.length_function(s) < self.chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                
                if not new_separators:
                    final_chunks.append(s)
                else:
                    other_info = self._split_text(s, new_separators)
                    final_chunks.extend(other_info)
        
        if _good_splits:
            merged_text = self._merge_splits(_good_splits, _separator)
            final_chunks.extend(merged_text)
        
        return final_chunks
    
    def _split_text_with_regex(
        self, 
        text: str, 
        separator: str, 
        keep_separator: bool
    ) -> List[str]:
        """使用正则表达式分割文本"""
        if separator:
            if keep_separator:
                _splits = re.split(f"({separator})", text)
                splits = [_splits[i] + _splits[i + 1] for i in range(1, len(_splits), 2)]
                if len(_splits) % 2 == 0:
                    splits += _splits[-1:]
                splits = [_splits[0]] + splits
            else:
                splits = re.split(separator, text)
        else:
            splits = list(text)
        
        return [s for s in splits if s != ""]
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """合并分割结果"""
        separator_len = self.length_function(separator)
        
        docs = []
        current_doc = []
        total = 0
        
        for d in splits:
            _len = self.length_function(d)
            if total + _len + (separator_len if len(current_doc) > 0 else 0) > self.chunk_size:
                if total > self.chunk_size:
                    print(f"警告: 创建了长度为 {total} 的块，超过了指定的 {self.chunk_size}")
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    
                    while total > self.chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0) > self.chunk_size
                        and total > 0
                    ):
                        total -= self.length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        current_doc = current_doc[1:]
            
            current_doc.append(d)
            total += _len + (separator_len if len(current_doc) > 1 else 0)
        
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        
        return docs
    
    def _join_docs(self, docs: List[str], separator: str) -> Optional[str]:
        """连接文档"""
        text = separator.join(docs)
        if self.strip_whitespace:
            text = text.strip()
        if text == "":
            return None
        return text


class TokenTextSplitter(TextSplitter):
    """基于Token的文本分割器"""
    
    def __init__(
        self,
        encoding_name: str = "cl100k_base",
        model_name: Optional[str] = None,
        allowed_special: Union[str, set] = set(),
        disallowed_special: Union[str, set] = "all",
        **kwargs
    ):
        super().__init__(**kwargs)
        
        try:
            if model_name:
                self.encoding = tiktoken.encoding_for_model(model_name)
            else:
                self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            # 如果tiktoken不可用，使用简单的长度计算
            self.encoding = None
        
        self.allowed_special = allowed_special
        self.disallowed_special = disallowed_special
    
    def split_text(self, text: str) -> List[str]:
        """基于Token分割文本"""
        def _encode(_text: str) -> int:
            if self.encoding:
                return len(
                    self.encoding.encode(
                        _text,
                        allowed_special=self.allowed_special,
                        disallowed_special=self.disallowed_special,
                    )
                )
            else:
                # 简单估算：1 token ≈ 4 字符
                return len(_text) // 4
        
        tokenizer = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=_encode,
            keep_separator=self.keep_separator,
            add_start_index=self.add_start_index,
            strip_whitespace=self.strip_whitespace,
        )
        
        return tokenizer.split_text(text)


class MarkdownTextSplitter(RecursiveCharacterTextSplitter):
    """Markdown文本分割器"""
    
    def __init__(self, **kwargs):
        separators = [
            "\n#{1,6} ",  # Headers
            "```\n",      # Code blocks
            "\n\\*\\*\\*+\n",  # Horizontal rules
            "\n---+\n",
            "\n___+\n",
            "\n\n",       # Paragraphs
            "\n",         # Lines
            " ",          # Words
            "",           # Characters
        ]
        super().__init__(separators=separators, is_separator_regex=True, **kwargs)


class PythonCodeTextSplitter(RecursiveCharacterTextSplitter):
    """Python代码文本分割器"""
    
    def __init__(self, **kwargs):
        separators = [
            "\nclass ",
            "\ndef ",
            "\n\ndef ",
            "\n\n",
            "\n",
            " ",
            "",
        ]
        super().__init__(separators=separators, **kwargs)


class JavaScriptTextSplitter(RecursiveCharacterTextSplitter):
    """JavaScript代码文本分割器"""
    
    def __init__(self, **kwargs):
        separators = [
            "\nfunction ",
            "\nconst ",
            "\nlet ",
            "\nvar ",
            "\nclass ",
            "\n\n",
            "\n",
            " ",
            "",
        ]
        super().__init__(separators=separators, **kwargs)


class HTMLTextSplitter(RecursiveCharacterTextSplitter):
    """HTML文本分割器"""
    
    def __init__(self, **kwargs):
        separators = [
            "<body",
            "<div",
            "<p",
            "<br",
            "<li",
            "<h1",
            "<h2",
            "<h3",
            "<h4",
            "<h5",
            "<h6",
            "<span",
            "<table",
            "<tr",
            "<td",
            "<th",
            "<ul",
            "<ol",
            "<header",
            "<footer",
            "<nav",
            # 标准分隔符
            "\n\n",
            "\n",
            " ",
            "",
        ]
        super().__init__(separators=separators, **kwargs)


class LatexTextSplitter(RecursiveCharacterTextSplitter):
    """LaTeX文本分割器"""
    
    def __init__(self, **kwargs):
        separators = [
            # 章节结构
            "\\chapter{",
            "\\section{",
            "\\subsection{",
            "\\subsubsection{",
            # 环境
            "\\begin{enumerate}",
            "\\begin{itemize}",
            "\\begin{description}",
            "\\begin{list}",
            "\\begin{quote}",
            "\\begin{quotation}",
            "\\begin{verse}",
            "\\begin{verbatim}",
            # 其他
            "\\item ",
            # 标准分隔符
            "\n\n",
            "\n",
            " ",
            "",
        ]
        super().__init__(separators=separators, **kwargs)


def get_text_splitter(
    splitter_type: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs
) -> TextSplitter:
    """获取文本分割器"""
    
    splitters = {
        "recursive": RecursiveCharacterTextSplitter,
        "token": TokenTextSplitter,
        "markdown": MarkdownTextSplitter,
        "python": PythonCodeTextSplitter,
        "javascript": JavaScriptTextSplitter,
        "html": HTMLTextSplitter,
        "latex": LatexTextSplitter,
    }
    
    if splitter_type not in splitters:
        raise ValueError(f"不支持的分割器类型: {splitter_type}")
    
    return splitters[splitter_type](
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    ) 