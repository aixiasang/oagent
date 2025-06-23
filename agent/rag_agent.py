from typing import Optional, Dict, List, Callable, Generator, Any
import asyncio
import sys
import os
import json

# 添加父目录到路径以支持相对导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.base import Agent
from rag import RAGManager
from model import Message
from prompt import Prompt


class RAGAgent(Agent):
    """集成RAG的增强Agent"""
    
    def __init__(
        self,
        llm_config: Optional[Dict] = None,
        rag_config: Optional[Dict] = None
    ):
        """
        初始化RAG Agent
        
        Args:
            llm_config: LLM配置
            rag_config: RAG配置
        """
        super().__init__(llm_config)
        
        # 初始化RAG
        rag_config = rag_config or {}
        self.rag_manager = RAGManager(
            llm_client=self.llm,
            provider="llm",
            collection_name=rag_config.get("collection_name", "rag_agent_docs"),
            persist_directory=rag_config.get("persist_directory", "./rag_db"),
            chunk_size=rag_config.get("chunk_size", 500),
            chunk_overlap=rag_config.get("chunk_overlap", 50)
        )
        
        # RAG增强配置
        self.use_rag = True
        self.rag_top_k = 5
        self.rag_threshold = 0.7
    
    def _enhance_prompt_with_context(self, prompt: str) -> str:
        """使用RAG增强提示"""
        enhanced_parts = []
        if self.use_rag:
            try:
                rag_context = asyncio.run(self.rag_manager.generate_context(
                    prompt,
                    top_k=self.rag_top_k
                ))
                if rag_context:
                    enhanced_parts.append(f"参考信息:\n{rag_context}")
            except Exception as e:
                print(f"RAG上下文生成失败: {str(e)}")
        if enhanced_parts:
            context_text = "\n\n---\n\n".join(enhanced_parts)
            return f"{context_text}\n\n---\n\n用户问题: {prompt}"
        else:
            return prompt
    
    def chat(self, prompt: str) -> str:
        """增强的聊天方法"""
        enhanced_prompt = self._enhance_prompt_with_context(prompt)
        response = super().chat(enhanced_prompt)
        return response
    
    def chat_stream(self, prompt: str):
        """增强的流式聊天方法"""
        enhanced_prompt = self._enhance_prompt_with_context(prompt)
        def enhanced_fn(resp: Generator[Message, Any, None]):
            for msg in resp:
                if msg.role == 'tool':
                    print(msg)
                else:
                    if msg.reasoning_content:
                        print(msg.reasoning_content, flush=True, end="")
                    if msg.content:
                        if msg.tool_calls:
                            print(msg)
                            continue
                        print(msg.content, flush=True, end="")
        self.fn_chat(enhanced_fn, enhanced_prompt)
        
    def chat_stream_with_callback(self, prompt: str, callback_fn):
        """支持自定义回调的流式聊天方法"""
        enhanced_prompt = self._enhance_prompt_with_context(prompt)
        
        def enhanced_fn(resp: Generator[Message, Any, None]):
            current_msg_id = None
            for msg in resp:
                # 检查消息ID变化，支持多气泡显示
                if hasattr(msg, 'id') and msg.id != current_msg_id:
                    if current_msg_id is not None:
                        # 通知前一个消息完成
                        callback_fn({"type": "message_complete", "id": current_msg_id})
                    current_msg_id = msg.id
                    callback_fn({"type": "message_start", "id": current_msg_id})
                
                if msg.role == 'tool':
                    callback_fn({"type": "tool", "message": msg})
                else:
                    if msg.reasoning_content:
                        callback_fn({
                            "type": "reasoning", 
                            "content": msg.reasoning_content,
                            "id": current_msg_id
                        })
                    if msg.content:
                        if msg.tool_calls:
                            callback_fn({"type": "tool_call", "message": msg})
                            continue
                        callback_fn({
                            "type": "content", 
                            "content": msg.content,
                            "id": current_msg_id
                        })
            
            # 通知最后一个消息完成
            if current_msg_id is not None:
                callback_fn({"type": "message_complete", "id": current_msg_id})
        
        self.fn_chat(enhanced_fn, enhanced_prompt)
    
    def add_document(self, content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """添加文档到RAG - 同步包装"""
        try:
            return asyncio.run(self.rag_manager.add_documents([{
                "content": content,
                "metadata": metadata or {}
            }]))
        except Exception as e:
            return {"status": "error", "message": f"添加文档失败: {str(e)}"}
    
    def add_file(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """添加文件到RAG - 同步包装"""
        try:
            return asyncio.run(self.rag_manager.add_file(file_path, metadata))
        except Exception as e:
            return {"status": "error", "message": f"添加文件失败: {str(e)}"}
    
    def add_url(self, url: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """添加URL到RAG - 同步包装"""
        try:
            return asyncio.run(self.rag_manager.add_url(url, metadata))
        except Exception as e:
            return {"status": "error", "message": f"添加URL失败: {str(e)}"}
    
    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库 - 同步包装"""
        try:
            return asyncio.run(self.rag_manager.query(query, top_k))
        except Exception as e:
            print(f"搜索知识库失败: {str(e)}")
            return []
    
    def get_rag_info(self) -> Dict[str, Any]:
        """获取RAG信息"""
        try:
            return asyncio.run(self.rag_manager.get_collection_info())
        except Exception as e:
            return {"status": "error", "message": f"获取RAG信息失败: {str(e)}"}
    
    def save_session(self):
        """保存会话"""
        # 创建会话目录
        session_dir = "./sessions"
        os.makedirs(session_dir, exist_ok=True)
        
        # 生成会话ID
        from datetime import datetime
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存Agent消息到文件
        session_file = f"{session_dir}/agent_messages_{session_id}.json"
        
        messages_data = []
        for msg in self.messages:
            messages_data.append(msg.to_json())
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(messages_data, f, ensure_ascii=False, indent=2)
        
        return session_id


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from config import get_siliconflow_model
    
    # 创建RAG Agent
    rag_agent = RAGAgent(
        llm_config=get_siliconflow_model(),
        rag_config={
            "collection_name": "test_rag",
            "chunk_size": 300
        }
    )
    
    # 添加一些文档
    print("添加文档...")
    result = rag_agent.add_document(
        "Python是一种高级编程语言，以其简洁易读的语法而闻名。",
        {"type": "definition", "topic": "programming"}
    )
    print(f"添加结果: {result}")
    
    # 测试对话
    print("RAG Agent 已准备就绪！")
    while True:
        user_input = input("\n用户> ")
        if user_input.lower() == 'quit':
            break
        
        print("\n助手> ", end="")
        rag_agent.chat_stream(user_input)
        print()
    
    # 保存会话
    session_id = rag_agent.save_session()
    print(f"\n会话已保存: {session_id}") 