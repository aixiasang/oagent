import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from colorama import Fore, Style, init

from agent import Agent
from prompts import AIGirlfriendPrompts, AIGirlfriendMemory
from model import Message
from tools import *

# 初始化colorama
init(autoreset=True)

class AIGirlfriendAgent(Agent):
    """AI女友智能体
    
    基于情感交互、记忆管理和个性化对话的AI女友系统
    支持上下文记忆、情感分析、个性化适应等功能
    """
    
    def __init__(self, girlfriend_name: str = "美月", personality_traits: str = "", 
                 memory_file: str = "girlfriend_memory.json"):
        super().__init__()
        self.girlfriend_name = girlfriend_name
        self.personality_traits = personality_traits
        self.memory_file = memory_file
        self.memory = AIGirlfriendMemory()
        self.prompts = AIGirlfriendPrompts()
        
        # 加载记忆数据
        self._load_memory()
        
        # 设置系统提示词
        self.system_prompt = self.prompts.get_system_prompt(
            girlfriend_name, personality_traits
        )
    
    def _print_content(self, content: str, color: str = Fore.GREEN, bold: bool = True):
        """打印彩色粗体内容"""
        style = Style.BRIGHT if bold else Style.NORMAL
        print(f"{style}{color}{content}{Style.RESET_ALL}")
    
    def _load_memory(self):
        """加载记忆数据"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory.user_info = data.get('user_info', {})
                    self.memory.conversation_history = data.get('conversation_history', [])
                    self.memory.important_dates = data.get('important_dates', {})
                    self.memory.emotional_states = data.get('emotional_states', [])
                    self.memory.preferences = data.get('preferences', {})
                self._print_content(f"💾 已加载{self.girlfriend_name}的记忆数据")
            except Exception as e:
                self._print_content(f"⚠️ 记忆数据加载失败: {e}", Fore.YELLOW)
    
    def _save_memory(self):
        """保存记忆数据"""
        try:
            data = {
                'user_info': self.memory.user_info,
                'conversation_history': self.memory.conversation_history,
                'important_dates': self.memory.important_dates,
                'emotional_states': self.memory.emotional_states,
                'preferences': self.memory.preferences
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._print_content(f"⚠️ 记忆数据保存失败: {e}", Fore.YELLOW)
    
    def _analyze_emotion(self, user_input: str) -> str:
        """分析用户情感状态"""
        emotion_prompt = self.prompts.get_emotion_analysis_prompt()
        
        messages = [
            Message.system(emotion_prompt),
            Message.user(f"请分析以下文本的情感状态：\n{user_input}\n\n请简洁地返回主要情感（如：开心、难过、焦虑、愤怒、平静等）")
        ]
        
        try:
            response = self.llm.chat(messages, stream=False)
            emotion = response.content.strip()
            self.memory.update_emotional_state(emotion, user_input)
            return emotion
        except Exception as e:
            self._print_content(f"⚠️ 情感分析失败: {e}", Fore.YELLOW)
            return "平静"
    
    def _extract_important_info(self, user_input: str, ai_response: str):
        """提取重要信息并更新记忆"""
        memory_prompt = self.prompts.get_memory_prompt()
        
        messages = [
            Message.system(memory_prompt),
            Message.user(f"""
请从以下对话中提取重要信息：

用户：{user_input}
AI：{ai_response}

请以JSON格式返回提取的信息，包括：
- user_info: 用户的个人信息
- important_dates: 重要日期
- preferences: 偏好信息
- 如果没有相关信息，返回空对象
""")
        ]
        
        try:
            response = self.llm.chat(messages, stream=False)
            info = json.loads(response.content)
            
            # 更新记忆
            if 'user_info' in info:
                for key, value in info['user_info'].items():
                    self.memory.update_user_info(key, value)
            
            if 'important_dates' in info:
                for key, value in info['important_dates'].items():
                    self.memory.add_important_date(key, value)
            
            if 'preferences' in info:
                for key, value in info['preferences'].items():
                    self.memory.update_preference(key, value)
                    
        except Exception as e:
            # 静默处理，不影响主要对话流程
            pass
    
    def _get_contextual_prompt(self, user_input: str) -> str:
        """获取包含上下文的提示词"""
        # 分析情感
        emotion = self._analyze_emotion(user_input)
        
        # 获取对话上下文
        recent_context = self.memory.get_recent_context()
        context_prompt = self.prompts.get_conversation_context_prompt(recent_context)
        
        # 获取记忆摘要
        memory_summary = self.memory.get_memory_summary()
        
        # 个性化适应
        adaptation_prompt = self.prompts.get_personality_adaptation_prompt(self.memory.preferences)
        
        # 检查是否是特殊场合
        current_time = datetime.now()
        time_prompt = ""
        
        # 检查重要日期
        today = current_time.strftime("%m-%d")
        for date_type, date_value in self.memory.important_dates.items():
            if today in date_value:
                time_prompt = self.prompts.get_special_occasion_prompt(date_type, date_value)
                break
        
        if not time_prompt:
            time_prompt = self.prompts.get_daily_check_in_prompt()
        
        return f"""
{self.system_prompt}

{memory_summary}

{context_prompt}

{adaptation_prompt}

{time_prompt}

当前用户情感状态：{emotion}

请基于以上所有信息，用最贴心、最个性化的方式回应用户。
"""
    
    def chat(self, user_input: str) -> str:
        """与AI女友聊天"""
        self._print_content(f"💕 {self.girlfriend_name}正在思考中...")
        
        # 记录用户输入
        self.memory.add_conversation("user", user_input)
        
        # 获取上下文提示词
        contextual_prompt = self._get_contextual_prompt(user_input)
        
        # 构建消息
        messages = [
            Message.system(contextual_prompt),
            Message.user(user_input)
        ]
        
        try:
            # 流式响应
            self._print_content(f"\n💖 {self.girlfriend_name}: ", Fore.MAGENTA, bold=True)
            
            response_content = ""
            for chunk in self.llm.chat(messages, stream=True):
                if hasattr(chunk, 'content') and chunk.content:
                    print(chunk.content, end='', flush=True)
                    response_content += chunk.content
            
            print()  # 换行
            
            # 记录AI回应
            self.memory.add_conversation("assistant", response_content)
            
            # 提取重要信息（异步处理，不阻塞对话）
            try:
                self._extract_important_info(user_input, response_content)
            except:
                pass
            
            # 保存记忆
            self._save_memory()
            
            return response_content
            
        except Exception as e:
            error_msg = f"😔 抱歉，{self.girlfriend_name}现在有点不舒服，请稍后再试..."
            self._print_content(f"❌ 错误: {e}", Fore.RED)
            return error_msg
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        return self.memory.get_memory_summary()
    
    def reset_memory(self):
        """重置记忆"""
        self.memory = AIGirlfriendMemory()
        if os.path.exists(self.memory_file):
            os.remove(self.memory_file)
        self._print_content(f"🔄 {self.girlfriend_name}的记忆已重置")
    
    def set_personality(self, new_personality: str):
        """设置新的性格特征"""
        self.personality_traits = new_personality
        self.system_prompt = self.prompts.get_system_prompt(
            self.girlfriend_name, new_personality
        )
        self._print_content(f"✨ {self.girlfriend_name}的性格已更新")

# 使用示例
if __name__ == '__main__':
    # 创建AI女友实例
    girlfriend = AIGirlfriendAgent(
        girlfriend_name="小美",
        personality_traits="温柔体贴，喜欢音乐和绘画，偶尔会撒娇，很关心用户的生活"
    )
    
    print("💕 AI女友聊天系统启动！")
    print(f"💖 你好！我是{girlfriend.girlfriend_name}，很高兴见到你～")
    print("💡 输入 'exit' 退出，'memory' 查看记忆，'reset' 重置记忆")
    print("="*50)
    
    while True:
        try:
            user_input = input("\n🗣️ 你: ").strip()
            
            if user_input.lower() == 'exit':
                print(f"💕 {girlfriend.girlfriend_name}: 再见啦，记得想我哦～")
                break
            elif user_input.lower() == 'memory':
                print(girlfriend.get_memory_summary())
                continue
            elif user_input.lower() == 'reset':
                girlfriend.reset_memory()
                continue
            elif not user_input:
                continue
            
            # 开始聊天
            girlfriend.chat(user_input)
            
        except KeyboardInterrupt:
            print(f"\n💕 {girlfriend.girlfriend_name}: 再见啦～")
            break
        except Exception as e:
            print(f"❌ 系统错误: {e}")