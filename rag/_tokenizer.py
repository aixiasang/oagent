from typing import List,Optional
import tiktoken

class Tokenizer:
    def __init__(self):
        pass
    def encode(self, content: str) -> List[int]:
        raise NotImplementedError
    
    def decode(self, tokens: List[int]) -> str:
        raise NotImplementedError
    

class TiktokenTokenizer(Tokenizer):
    def __init__(self,model_name:Optional[str]=None,encoding_name:Optional[str]=None):
        super().__init__()
        _tokenizer=None
        if model_name:
            _tokenizer=tiktoken.encoding_for_model(model_name=model_name)
        if encoding_name:
            _tokenizer=tiktoken.get_encoding(encoding_name=encoding_name)
        self.tokenizer = _tokenizer
        self.name="tiktoken"
    def encode(self, content: str) -> List[int]:
        return self.tokenizer.encode(content)
    def decode(self, tokens: List[int]) -> str:
        return self.tokenizer.decode(tokens)
    

