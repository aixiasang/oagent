import gc
import os
from typing import List, Optional, Union
import numpy as np
import faiss
from ._chunk import get_chunks
from ._tokenizer import Tokenizer,TiktokenTokenizer
from ._parser import Parser,Document
from model import OpenaiLLM
from config import get_siliconflow_model
from typing import List,Dict,Optional,Callable
from ._chunk import ChunkInfo
from ._cache import _Cache

default_index_path="storage"
faiss_index='faiss.index'
index_npz='index.npz'
cache_path="_cache.json"
def cosine_similarity(vector1: List[float], vector2: List[float]) -> float:
    dot_product = np.dot(vector1, vector2)
    magnitude = np.linalg.norm(vector1) * np.linalg.norm(vector2)
    if not magnitude:
        return 0
    return dot_product / magnitude

class VectorStore:
    def __init__(self,dim:int,
                 tokenizer:Optional[Tokenizer]=None,
                 index_path:str=default_index_path,
                 llm:OpenaiLLM=None,
                 chunk_size:int=1024,
                 leap_size:int=128,
                 split_char:Optional[str]= None,
                 only_char:bool=False):
        self._tokenizer=tokenizer
        self._index_path=index_path
        self._llm=llm
        self._chunk_size=chunk_size
        self._leap_size=leap_size
        self._split_char=split_char
        self._only_char=only_char
        self._docs:List[ChunkInfo]=[]
        self._vectors=[]
        self._vectors_idx=0
        self._dim=dim
        self.num_docs = 0

        self._embed_func=self._llm.embed
        self._rerank_func=self._llm.rerank
        self._llm_chat=self._llm.chat

        self._index_npz_path=os.path.join(self._index_path,index_npz)
        self._faiss_index_path=os.path.join(self._index_path,faiss_index)
        self._cache_path=os.path.join(self._index_path,cache_path)
        self._cache=_Cache(self._cache_path)
        self._pre_load()
    def _get_chunks(self,doc:Document):
        _chunks=get_chunks(doc,self._tokenizer,self._chunk_size,self._leap_size,self._split_char,self._only_char)
        embeddings=self._embed_func([chunk.content for chunk in _chunks])
        if len(embeddings) > 0:
            vectors = np.array(embeddings).astype('float32')
            self._index.add(vectors)
        self._docs.extend(_chunks)
        self._vectors.extend(embeddings)
        self.num_docs += 1
        print("add doc",self.num_docs)
    def add_doc(self, doc: Document) -> None:
        if self._cache.hit(doc):
            print("cache hit",doc)
        return self._get_chunks(doc)
    def retrieve(self, query:Union[str,List[str]], top_k: int = 5) -> List[Dict[str, Union[str, float]]]:
        query=[query] if isinstance(query,str) else query
        query_embedding = self._embed_func(query)
        query_vector = np.array(query_embedding).astype('float32').reshape(1, -1)
        scores, indices = self._index.search(query_vector, top_k)
        results = [
            {'text': self._docs[idx].content, 'score': float(score)}
            for idx, score in zip(indices[0], scores[0])
        ]
        return results
    def _rerank(self,query: str, documents: List[str],top_k=3)->List[Dict]:
        return self._rerank_func(query, documents,top_k)
    def rereank(self,query: str,top_k=3):
        retrieve_topk=max(10,min(5,2*top_k))
        results=self.retrieve(query=query,top_k=retrieve_topk)
        return self._rerank(query=query,documents=[result['text'] for result in results],top_k=top_k)
    def get(self,query: str,top_k=3,**kwargs):
        results=self.rereank(query=query,top_k=top_k)
        _formated_result=self._formated_result(results)
        return self._chat(_formated_result,**kwargs)
    def _chat(self,formated_result:str,**kwargs):
        from prompt import rag_prompt
        from model import Messages
        msg = Messages(system_prompt=rag_prompt.format(rag_result=formated_result))
        content=''
        for msg in self._llm_chat(msg,**kwargs):
            if msg.reasoning_content:
                print(msg.reasoning_content,flush=True,end='')
            if msg.content:
                print(msg.content,flush=True,end='')
                content+=msg.content
        return content
    def _formated_result(self,result:List[Dict]):
        rag_result = ''
        for i in result:
            rag_result += f"score:{i['score']}\ncontent:{i['text']}\n"
        return rag_result
    def load_index(self,):
        data=np.load(self._index_npz_path,allow_pickle=True)
        self._docs=data['_docs'].tolist()
        self._vectors=data['_vectors'].tolist()
        self._index=faiss.read_index(self._faiss_index_path)
        del data
        gc.collect()
    def save_index(self):
        np.savez(
            self._index_npz_path,
            _docs=self._docs,
            _vectors=self._vectors
        )
        faiss.write_index(self._index, self._faiss_index_path)
        self._cache.save_cache()

    def _pre_load(self):
        if not os.path.exists(self._index_path):
            os.makedirs(self._index_path, exist_ok=True)
        
        print(self._index_npz_path)
        print(self._faiss_index_path)
        if os.path.exists(os.path.abspath(self._index_npz_path)) and os.path.exists(os.path.abspath(self._faiss_index_path)):
            self.load_index()
        else:
            self._index = faiss.IndexFlatL2(self._dim)

if __name__ == '__main__':
    tokenizer=TiktokenTokenizer(encoding_name='cl100k_base')
    llm_cfg=get_siliconflow_model()
    llm_cfg['embedding_cfg']['model']='BAAI/bge-m3'
    llm=OpenaiLLM(llm_config=llm_cfg)
   
    # embeddings=embed_model.embed([chunk.content for chunk in _chunks])
    dim=1024
    chunk_size=512
    leap_size=128
    vb=VectorStore(dim=dim,llm=llm,tokenizer=tokenizer,chunk_size=chunk_size,leap_size=leap_size)
    vb.load_index()
    from ._parser import Parser
    doc1=Parser.parser("rag/data.txt")
    vb.add_doc(doc1)
    query="我的老师"
    vb.get(query=query)
    doc2=Parser.parser("rag/data2.txt")
    vb.add_doc(doc2)

    doc3=Parser.parser("rag/data3.txt")
    vb.add_doc(doc3)
    vb.save_index()


    # results=vb.retrieve(query=query)

    # for result in results:
    #     print(result['text'])
    #     print(result['score'])
    # results=vb.rerank(query=query,documents=[result['text'] for result in results])
    # for result in results:
    #     print(result['text'])
    #     print(result['score'])

    