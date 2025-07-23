
import base64
from io import BytesIO
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any, List, Dict, Optional
from hashlib import md5
def _get_doc_id(prefix:str="_doc",content:str=None):
    return prefix+md5(content.encode()).hexdigest()

@dataclass
class Document:
    doc_id: str
    content: str
    file_path: str
    _meta: Dict[str, Any] = field(default_factory=dict)
    _llm_cache: List[Any] = field(default_factory=list)
    
    def __str__(self):
        return f"Doc<_doc {self.doc_id}>"
    
    @property
    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            'file_path': self.file_path,
            "_meta": self._meta,
            "_llm_cache": self._llm_cache
        }
def _read_text(path:str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        from charset_normalizer import from_path
        return str(from_path(path).best())
    raise Exception("文件读取失败")

def _parser_text(path:str):
    content=_read_text(path)
    return Document(doc_id=_get_doc_id("_doc",content=content),content=content,file_path=path,_meta={'file_path': path})
class Parser:
    @staticmethod
    def parser(path:str):
        return _parser_text(path)
def write_text(path:str, content:str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def _resize_image(img, short_side_length: int = 1080):
    from PIL import Image
    assert isinstance(img, Image.Image)

    width, height = img.size

    if width <= height:
        new_width = short_side_length
        new_height = int((short_side_length / width) * height)
    else:
        new_height = short_side_length
        new_width = int((short_side_length / height) * width)

    resized_img = img.resize((new_width, new_height), resample=Image.Resampling.BILINEAR)
    return resized_img

class ToBase64:
    @staticmethod
    def audio(path:str):
        with open(path, "rb") as f: 
            return 'data:;base64,' + base64.b64encode(f.read()).decode('utf-8')
    
    @staticmethod
    def video(path:str):
        with open(path, "rb") as f: 
            return 'data:;base64,' + base64.b64encode(f.read()).decode('utf-8')
    
    @staticmethod
    def image(path:str,max_short_side_length: int = -1):
        from PIL import Image
        image = Image.open(path)

        if (max_short_side_length > 0) and (min(image.size) > max_short_side_length):
            ori_size = image.size
            image = _resize_image(image, short_side_length=max_short_side_length)
        image = image.convert(mode='RGB')
        buffered = BytesIO()
        image.save(buffered, format='JPEG')
        return 'data:image/jpeg;base64,' + base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    
if __name__ == '__main__':
    doc=Parser.parser("./_parser.py")
    print(doc)