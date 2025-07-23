import json
import os
from ._parser import Document
from collections import defaultdict
class _Cache:
    def __init__(self,cache_path:str):
        """
        id -> file_path
        file_path -> id
        """
        self._cache_doc_id=defaultdict(None)
        self._cache_doc_file_path=defaultdict(None)
        self._cache_path=cache_path
        if os.path.exists(self._cache_path):
            self._load_cache()
    def _load_cache(self):
        with open(self._cache_path,"r") as f:
            _cache=json.load(f)
        self._cache_doc_id=_cache["_cache_doc_id"]
        self._cache_doc_file_path=_cache["_cache_doc_file_path"]

    def save_cache(self):
        _cache={
            "_cache_doc_id":self._cache_doc_id,
            "_cache_doc_file_path":self._cache_doc_file_path
        }
        with open(self._cache_path,"w") as f:
            json.dump(_cache,f)
    def _check(self,doc:Document):
        _doc_id=doc.doc_id
        _doc_file_path=doc._meta.get("file_path",None)
        _doc_target_file_path=self._cache_doc_id.get(_doc_id)
        _doc_target_id=self._cache_doc_file_path.get(_doc_file_path)

        if _doc_target_file_path:
            """表示文件id已经存在了"""
            if _doc_target_file_path!=_doc_file_path:
                self._cache_doc_id[_doc_id]=_doc_file_path
                del self._cache_doc_file_path[_doc_target_file_path]
                self._cache_doc_file_path[_doc_file_path]=_doc_id
            return True
        if _doc_target_id:
            """文件路径存在 但是id不存在了"""
            del self._cache_doc_id[_doc_id]
            self._cache_doc_file_path[_doc_file_path]=_doc_id
            return False
        self._cache_doc_id[_doc_id]=_doc_file_path
        self._cache_doc_file_path[_doc_file_path]=_doc_id
        return False
    def hit(self,doc:Document):
        return self._check(doc)
        
