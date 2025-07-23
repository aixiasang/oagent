from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from ._tokenizer import Tokenizer, TiktokenTokenizer
from ._parser import Document


@dataclass
class ChunkInfo:
    tokens: int
    content: str
    chunk_order_index: int
    doc_id: str
    file_path: str
    _meta: Dict[str, Any] = field(default_factory=dict)
    _llm_cache: List[Any] = field(default_factory=list)

    @staticmethod
    def from_doc(tokens: int, content: str, chunk_order_index: int, doc: Document):
        return ChunkInfo(
            tokens=tokens,
            content=content,
            chunk_order_index=chunk_order_index,
            doc_id=doc.doc_id,
            file_path=doc.file_path,
            _meta=doc._meta,
            _llm_cache=doc._llm_cache
        )

    @property
    def to_json(self):
        return {
            "tokens": self.tokens,
            "content": self.content,
            "chunk_order_index": self.chunk_order_index,
            "content": self.content,
            "doc_id": self.doc_id,
            "file_path": self.file_path,
            "_meta": self._meta,
            "_llm_cache": self._llm_cache
        }

def get_chunks(
    doc: Document,
    tokenizer: Optional[Tokenizer] = None,
    chunk_size: int = 1024,
    leap_size: int = 128,
    split_char: Optional[str] = None,
    only_char: bool = False,
):
    def _tokenizer_chunk():
        tokens = tokenizer.encode(doc.content)
        
        def _split_tokens(split_char: str, only_char: bool = True):
            raw_chunks = doc.content.split(split_char)
            new_chunks = []
            if only_char:
                for chunk in raw_chunks:
                    _tokens = tokenizer.encode(chunk)
                    new_chunks.append((len(_tokens), chunk))
            else:
                for chunk in raw_chunks:
                    _tokens = tokenizer.encode(chunk)
                    step = chunk_size - leap_size
                    if len(_tokens) > chunk_size:
                        for idx in range(0, len(_tokens), step if step > 0 else chunk_size):
                            _chunk_content = tokenizer.decode(_tokens[idx:idx + chunk_size])
                            new_chunks.append((min(chunk_size, len(_tokens) - idx), _chunk_content))
                    else:
                        new_chunks.append((len(_tokens), chunk))
            results: List[ChunkInfo] = []
            for i, (_len, _chunk) in enumerate(new_chunks):
                results.append(ChunkInfo.from_doc(_len, _chunk, i, doc))
            return results
        
        def _simple_chunk():
            results: List[ChunkInfo] = []
            step = chunk_size - leap_size
            for i, idx in enumerate(range(0, len(tokens), step if step > 0 else chunk_size)):
                _chunk_content = tokenizer.decode(tokens[idx:idx + chunk_size])
                results.append(ChunkInfo.from_doc(min(chunk_size, len(tokens) - idx), _chunk_content.strip(), i, doc))
            return results
        
        return _simple_chunk() if not split_char else _split_tokens(split_char, only_char)
    
    def _no_tokenizer_chunk():
        data = doc.content
        step = chunk_size - leap_size
        results: List[ChunkInfo] = []
        for i, idx in enumerate(range(0, len(data), step if step > 0 else chunk_size)):
            _chunk_content = data[idx:idx + chunk_size]
            results.append(ChunkInfo.from_doc(min(chunk_size, len(data) - idx), _chunk_content.strip(), i, doc))
        return results
    
    return _tokenizer_chunk() if tokenizer else _no_tokenizer_chunk()