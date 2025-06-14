import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import os

class SessionDatabase:
    """会话数据库管理类"""
    
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # 创建消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT,
                    reasoning_content TEXT,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    created_at TEXT NOT NULL,
                    message_order INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages (session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_order 
                ON messages (session_id, message_order)
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()
    
    def create_session(self, title: str = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if not title:
            title = f"会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, title, now, now))
            conn.commit()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions WHERE id = ? AND is_active = 1
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有活跃会话"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions 
                WHERE is_active = 1 
                ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET title = ?, updated_at = ?
                WHERE id = ? AND is_active = 1
            """, (title, datetime.now().isoformat(), session_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话（软删除）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def save_message(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """保存消息到数据库"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取当前会话的消息数量作为排序依据
            cursor.execute("""
                SELECT COALESCE(MAX(message_order), 0) + 1 
                FROM messages WHERE session_id = ?
            """, (session_id,))
            message_order = cursor.fetchone()[0]
            
            # 处理tool_calls（如果存在，转换为JSON字符串）
            tool_calls_json = None
            if message_data.get('tool_calls'):
                tool_calls_json = json.dumps(message_data['tool_calls'], ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO messages (
                    id, session_id, role, content, reasoning_content, 
                    tool_calls, tool_call_id, created_at, message_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_data.get('id', str(uuid.uuid4())),
                session_id,
                message_data.get('role'),
                message_data.get('content'),
                message_data.get('reasoning_content'),
                tool_calls_json,
                message_data.get('tool_call_id'),
                message_data.get('created', datetime.now().isoformat()),
                message_order
            ))
            
            # 更新会话的最后更新时间
            cursor.execute("""
                UPDATE sessions 
                SET updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            return True
    
    def get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有消息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY message_order ASC
            """, (session_id,))
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                message = dict(row)
                # 解析tool_calls JSON
                if message['tool_calls']:
                    try:
                        message['tool_calls'] = json.loads(message['tool_calls'])
                    except json.JSONDecodeError:
                        message['tool_calls'] = None
                messages.append(message)
            
            return messages
    
    def clear_session_messages(self, session_id: str) -> bool:
        """清空会话的所有消息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages WHERE session_id = ?
            """, (session_id,))
            
            # 更新会话的最后更新时间
            cursor.execute("""
                UPDATE sessions 
                SET updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            return cursor.rowcount > 0

# 全局数据库实例
db = SessionDatabase()