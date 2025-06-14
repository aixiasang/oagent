from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from database import SessionDatabase
import json
import sys
import os
from datetime import datetime

# 添加父目录到路径以便导入agent模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent import Agent
from config import get_siliconflow_model
from model.msg import Message
from database import db

app = Flask(__name__)
CORS(app)  # 启用CORS支持

# 初始化数据库
db = SessionDatabase()

# 全局agent实例字典，按会话ID存储
agent_instances = {}
current_session_id = None

def get_or_create_agent(session_id: str):
    """获取或创建指定会话的agent实例"""
    global agent_instances
    
    if session_id not in agent_instances:
        try:
            llm_config = get_siliconflow_model()
            agent = Agent(llm_config)
            
            # 从数据库加载历史消息
            messages_data = db.get_session_messages(session_id)
            if messages_data:
                # 转换数据库消息为Message对象
                messages = []
                for msg_data in messages_data:
                    if msg_data['role'] == 'system':
                        msg = Message.system(msg_data['content'])
                    elif msg_data['role'] == 'user':
                        msg = Message.user(msg_data['content'])
                    elif msg_data['role'] == 'assistant':
                        msg = Message.bot(
                            content=msg_data['content'],
                            reasoning_content=msg_data['reasoning_content'],
                            tool_calls=msg_data['tool_calls']
                        )
                    elif msg_data['role'] == 'tool':
                        msg = Message.tool_result(
                            tool_call_id=msg_data['tool_call_id'],
                            content=msg_data['content']
                        )
                    else:
                        continue
                    
                    # 设置消息的ID和创建时间
                    msg.id = msg_data['id']
                    msg.created = msg_data['created_at']
                    messages.append(msg)
                
                # 加载消息到agent
                agent.load_messages(messages)
            
            agent_instances[session_id] = agent
        except Exception as e:
            print(f"初始化Agent失败: {e}")
            # 如果配置失败，使用默认配置
            agent_instances[session_id] = Agent()
    
    return agent_instances[session_id]

def init_agent():
    """向后兼容的初始化函数"""
    global current_session_id
    if not current_session_id:
        current_session_id = db.create_session("默认会话")
    return get_or_create_agent(current_session_id)

@app.route('/')
def index():
    """主页面"""
    return render_template('chat.html')

@app.route('/favicon.ico')
def favicon():
    """处理favicon请求"""
    return '', 204

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    """处理聊天请求，支持流式输出"""
    if request.method == 'GET':
        return jsonify({'message': '请使用POST方法发送聊天消息'}), 200
    
    try:
        data = request.get_json()
        global current_session_id
        
        user_message = data.get('message', '')
        session_id = data.get('session_id', current_session_id)
        
        if not user_message.strip():
            return jsonify({'error': '消息不能为空'}), 400
        
        # 如果指定了session_id，切换到该会话
        if session_id and session_id != current_session_id:
            current_session_id = session_id
        
        agent = get_or_create_agent(current_session_id)
        
        def generate_response():
            """生成流式响应"""
            import queue
            import threading
            
            # 创建队列来收集消息
            message_queue = queue.Queue()
            
            try:
                # 定义处理函数来收集消息
                def message_handler(msg):
                    message_queue.put(msg)
                
                # 在单独线程中运行fn_chat
                def run_chat():
                    try:
                        agent.fn_chat(message_handler, user_message)
                        message_queue.put(None)  # 结束信号
                    except Exception as e:
                        message_queue.put(('error', str(e)))
                
                chat_thread = threading.Thread(target=run_chat)
                chat_thread.start()
                
                # 从队列中读取消息并yield
                while True:
                    try:
                        msg = message_queue.get(timeout=30)  # 30秒超时
                        
                        if msg is None:  # 结束信号
                            # 保存消息到数据库
                            try:
                                # 保存用户消息和助手回复到数据库
                                for message in agent.messages[-10:]:  # 保存最近的消息
                                    if message.role in ['user', 'assistant', 'tool']:
                                        db.save_message(
                                            session_id=current_session_id,
                                            role=message.role,
                                            content=message.content,
                                            tool_call_id=getattr(message, 'tool_call_id', None),
                                            tool_calls=getattr(message, 'tool_calls', None),
                                            reasoning_content=getattr(message, 'reasoning_content', None)
                                        )
                            except Exception as e:
                                print(f"保存消息到数据库失败: {e}")
                            break
                        elif isinstance(msg, tuple) and msg[0] == 'error':  # 错误信号
                            error_msg = f"处理消息时出错: {msg[1]}"
                            yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
                            break
                        else:
                            # 使用msg.to_json()获取完整的消息数据
                            msg_data = msg.to_json()
                            
                            # 参考base.py中的消息处理逻辑
                            if msg_data.get('role') == 'assistant':
                                # 处理assistant角色的消息
                                
                                # 1. 处理推理内容 (reasoning_content)
                                if msg_data.get('reasoning_content'):
                                    response_data = {
                                        'id': msg_data.get('id'),
                                        'type': 'reasoning',
                                        'role': 'assistant',
                                        'content': msg_data.get('reasoning_content'),
                                        'created': msg_data.get('created')
                                    }
                                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                                
                                # 2. 处理正常内容 (content)
                                if msg_data.get('content'):
                                    response_data = {
                                        'id': msg_data.get('id'),
                                        'type': 'content',
                                        'role': 'assistant', 
                                        'content': msg_data.get('content'),
                                        'created': msg_data.get('created')
                                    }
                                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                                
                                # 3. 处理工具调用响应 (tool_calls)
                                if msg_data.get('tool_calls'):
                                    for tool_call in msg_data.get('tool_calls', []):
                                        tool_name = tool_call.get('function', {}).get('name', '未知工具')
                                        tool_args = tool_call.get('function', {}).get('arguments', '{}')
                                        
                                        try:
                                            tool_input = json.loads(tool_args)
                                        except:
                                            tool_input = tool_args
                                        
                                        tool_content = f"🔧 工具调用: {tool_name}\n"
                                        tool_content += f"输入: {json.dumps(tool_input, ensure_ascii=False, indent=2)}"
                                        
                                        response_data = {
                                            'id': msg_data.get('id'),
                                            'type': 'tool_call',
                                            'role': 'assistant',
                                            'content': tool_content,
                                            'tool_call_id': tool_call.get('id'),
                                            'tool_name': tool_name,
                                            'tool_input': tool_input,
                                            'created': msg_data.get('created')
                                        }
                                        yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                            
                            elif msg_data.get('role') == 'tool':
                                # 处理工具结果消息
                                tool_call_id = msg_data.get('tool_call_id')
                                tool_result = msg_data.get('content', '')
                                
                                tool_content = f"📋 工具结果:\n{tool_result}"
                                
                                response_data = {
                                    'id': msg_data.get('id', tool_call_id),
                                    'type': 'tool_result',
                                    'role': 'tool',
                                    'content': tool_content,
                                    'tool_call_id': tool_call_id,
                                    'created': msg_data.get('created')
                                }
                                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    
                    except queue.Empty:
                        # 超时，可能是长时间没有响应
                        yield f"data: {json.dumps({'type': 'error', 'content': '响应超时'}, ensure_ascii=False)}\n\n"
                        break
                
                # 等待线程结束
                chat_thread.join(timeout=5)
                
                # 发送结束信号
                yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error_msg = f"处理消息时出错: {str(e)}"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
        
        return Response(
            generate_response(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

@app.route('/clear', methods=['POST'])
def clear_chat():
    """清空当前会话的聊天记录"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', current_session_id)
        
        global agent_instances
        
        # 清空数据库中的消息
        if session_id:
            db.clear_session_messages(session_id)
        
        # 重新初始化该会话的agent
        if session_id in agent_instances:
            del agent_instances[session_id]
        
        # 如果是当前会话，重新创建agent
        if session_id == current_session_id:
            get_or_create_agent(session_id)
        
        return jsonify({
            'success': True,
            'message': '聊天记录已清空'
        })
    except Exception as e:
        return jsonify({'error': f'清空聊天记录失败: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'active_sessions': len(agent_instances),
        'current_session': current_session_id
    })

@app.route('/current-session', methods=['GET'])
def get_current_session():
    """获取当前会话状态"""
    return jsonify({
        'current_session_id': current_session_id,
        'has_sessions': len(db.get_all_sessions()) > 0
    })

# 会话管理API
@app.route('/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话列表"""
    try:
        sessions = db.get_all_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions,
            'current_session_id': current_session_id
        })
    except Exception as e:
        return jsonify({'error': f'获取会话列表失败: {str(e)}'}), 500

@app.route('/sessions', methods=['POST'])
def create_session():
    """创建新会话"""
    try:
        data = request.get_json() or {}
        title = data.get('title', f"新会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        session_id = db.create_session(title)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'title': title
        })
    except Exception as e:
        return jsonify({'error': f'创建会话失败: {str(e)}'}), 500

@app.route('/sessions/<session_id>', methods=['GET'])
def get_session_info(session_id):
    """获取指定会话信息"""
    try:
        session = db.get_session(session_id)
        if not session:
            return jsonify({'error': '会话不存在'}), 404
        
        messages = db.get_session_messages(session_id)
        
        return jsonify({
            'success': True,
            'session': session,
            'messages': messages
        })
    except Exception as e:
        return jsonify({'error': f'获取会话信息失败: {str(e)}'}), 500

@app.route('/sessions/<session_id>/switch', methods=['POST'])
def switch_session(session_id):
    """切换到指定会话"""
    try:
        global current_session_id
        
        # 检查会话是否存在
        session = db.get_session(session_id)
        if not session:
            return jsonify({'error': '会话不存在'}), 404
        
        current_session_id = session_id
        
        # 获取或创建该会话的agent实例
        agent = get_or_create_agent(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'已切换到会话: {session["title"]}'
        })
    except Exception as e:
        return jsonify({'error': f'切换会话失败: {str(e)}'}), 500

@app.route('/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """更新会话信息"""
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({'error': '缺少标题参数'}), 400
        
        success = db.update_session_title(session_id, data['title'])
        if not success:
            return jsonify({'error': '会话不存在或更新失败'}), 404
        
        return jsonify({
            'success': True,
            'message': '会话标题已更新'
        })
    except Exception as e:
        return jsonify({'error': f'更新会话失败: {str(e)}'}), 500

@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    try:
        global current_session_id, agent_instances
        
        success = db.delete_session(session_id)
        if not success:
            return jsonify({'error': '会话不存在或删除失败'}), 404
        
        # 从内存中移除agent实例
        if session_id in agent_instances:
            del agent_instances[session_id]
        
        # 检查是否还有其他活跃会话
        remaining_sessions = db.get_all_sessions()
        
        # 如果删除的是当前会话，需要更新当前会话ID
        if current_session_id == session_id:
            if remaining_sessions:
                # 如果还有其他会话，切换到最新的会话
                current_session_id = remaining_sessions[0]['id']
            else:
                # 如果没有其他会话了，清空当前会话ID
                current_session_id = None
        
        return jsonify({
            'success': True,
            'message': '会话已删除',
            'current_session_id': current_session_id,
            'has_sessions': len(remaining_sessions) > 0
        })
    except Exception as e:
        return jsonify({'error': f'删除会话失败: {str(e)}'}), 500

@app.route('/sessions/<session_id>/clear', methods=['POST'])
def clear_session_messages(session_id):
    """清空指定会话的消息"""
    try:
        global agent_instances
        
        success = db.clear_session_messages(session_id)
        if not success:
            return jsonify({'error': '会话不存在或清空失败'}), 404
        
        # 重新初始化该会话的agent
        if session_id in agent_instances:
            del agent_instances[session_id]
        
        return jsonify({
            'success': True,
            'message': '会话消息已清空'
        })
    except Exception as e:
        return jsonify({'error': f'清空会话失败: {str(e)}'}), 500

if __name__ == '__main__':
    print("正在启动Flask聊天机器人服务...")
    init_agent()
    print("Agent初始化完成")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)