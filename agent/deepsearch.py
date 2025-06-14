"""
并不是很成熟
"""
from typing import Optional, Dict, List, Any
from model import OpenaiLLM, Message
from prompts import DeepResearchPrompts, JinaAgentPrompts
from tools import *
import time
from datetime import datetime

from tools.register import get_registered_tool, get_tool_list

class DeepSearchAgent:
    """深度搜索代理，基于jina-ai/node-DeepResearch架构实现"""
    def __init__(self, llm_config: Optional[Dict] = None, name: str = "DeepSearchAgent", description: str = "深度搜索AI助手", max_iterations: int = 3):
        self.llm = OpenaiLLM(llm_config)
        self.name = name
        self.description = description
        self.max_iterations = max_iterations
        self.search_history = []
        self.gathered_info = []
        self.sources = []
        self.tools = get_registered_tools()
        self.search_tools=get_tool_list(['zhipu_web_search','search_baidu'])
        
    def _get_current_time_context(self) -> str:
        """获取当前时间上下文"""
        now = datetime.now()
        return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')} (北京时间)"
        
    def _print_content(self, content: str, color: str = "green", bold: bool = True):
        """打印带颜色和加粗的内容"""
        if bold and color == "green":
            print(f"\033[1;32m{content}\033[0m", flush=True, end="")
        elif color == "green":
            print(f"\033[32m{content}\033[0m", flush=True, end="")
        elif bold:
            print(f"\033[1m{content}\033[0m", flush=True, end="")
        else:
            print(content, flush=True, end="")
            
    def search_with_all_tools(self, question: str, context: str = "") -> str:
        """使用所有可用的搜索工具进行搜索"""
        # 生成搜索提示，包含时间上下文
        time_context = self._get_current_time_context()
        search_prompt = DeepResearchPrompts.get_search_prompt(
            question=question,
            context=f"{time_context}\n{context}",
            previous_searches="\n".join([s["query"] for s in self.search_history])
        )
        
        print("\n🔍 正在使用所有搜索工具进行深度搜索...\n")
        
        # 构建系统提示，强调使用所有搜索工具
        system_prompt = f"""{DeepResearchPrompts.get_system_prompt()}
        
重要指示：
1. 你必须使用所有可用的搜索工具来获取全面的信息
2. 对于每个搜索查询，尝试使用不同的搜索工具以获得更全面的结果
3. 包括但不限于：网页搜索、维基百科搜索、学术搜索等
4. 当前时间上下文：{time_context}
5. 搜索时考虑时效性，优先获取最新信息
"""
        
        # 让LLM使用所有搜索工具
        messages = [
            Message.system(system_prompt),
            Message.user(f"""{search_prompt}
请按照以下步骤执行深度搜索：
1. 使用所有可用的搜索工具（包括zhipu_web_search、search_wiki等）来查找相关信息
2. 对每个搜索结果进行分析和总结
3. 确保获取最新、最准确的信息
4. 如果某个工具没有找到结果，尝试其他工具
5. 综合所有搜索结果给出完整的信息

开始搜索并分析内容。""")
        ]
        # 使用所有工具进行搜索 - 启用流式输出
        full_response = ""
        resp = self.llm.chat(messages=messages, tools=self.search_tools, tool_choice="auto", stream=True)
        # while True:
        for msg in resp:
            if msg.reasoning_content:
                self._print_content(msg.reasoning_content)
            if msg.content:
                self._print_content(msg.content, color="green", bold=True)
                full_response += msg.content
        if msg.content:
            self.search_history.append({
                "query": question,
                "context": context,
                "response": msg.content,
                "timestamp": time.time(),
                "time_context": time_context
            })
            # if Message.check_tool_result(messages[-1]):
            #     continue
            # else:
            #     break
            
        return full_response or "搜索未返回结果"
    
    def analyze_and_reason(self, question: str, search_results: str) -> str:
        """分析搜索结果并进行推理"""
        time_context = self._get_current_time_context()
        read_prompt = DeepResearchPrompts.get_read_prompt(
            question=question,
            url="综合搜索结果",
            content=search_results
        )
        
        print("\n\n🧠 正在分析和推理...\n")
        
        system_prompt = f"""{DeepResearchPrompts.get_system_prompt()}
        
分析指导：
1. 仔细分析所有搜索结果
2. 识别关键信息和数据点
3. 注意信息的时效性和可靠性
4. 当前时间：{time_context}
5. 如果信息不足，明确指出需要进一步搜索的方向
"""
        
        messages = [
            Message.system(system_prompt),
            Message.user(read_prompt)
        ]
        
        # 流式分析
        analysis = ""
        resp = self.llm.chat(messages=messages, stream=True)
        
        for msg in resp:
            if msg.reasoning_content:
                self._print_content(msg.reasoning_content)
            if msg.content:
                self._print_content(msg.content, color="green", bold=True)
                analysis += msg.content
        
        if analysis:
            self.gathered_info.append({
                "search_results": search_results,
                "analysis": analysis,
                "timestamp": time.time(),
                "time_context": time_context
            })
        
        return analysis
    
    def reflect_and_plan_next(self, question: str) -> List[str]:
        """反思当前信息并规划下一步搜索"""
        if not self.gathered_info:
            return []
            
        time_context = self._get_current_time_context()
        gathered_info_text = "\n\n".join([info["analysis"] for info in self.gathered_info])
        
        reflect_prompt = DeepResearchPrompts.get_reflect_prompt(
            question=question,
            gathered_info=gathered_info_text,
            sources=f"已搜索 {len(self.search_history)} 次"
        )
        
        print("\n\n🤔 正在反思和规划下一步...\n")
        
        system_prompt = f"""{DeepResearchPrompts.get_system_prompt()}
        
反思指导：
1. 评估当前信息的完整性和准确性
2. 识别知识空白和需要验证的信息
3. 考虑时效性，是否需要更新的信息
4. 当前时间：{time_context}
5. 生成具体的后续搜索问题
"""
        
        messages = [
            Message.system(system_prompt),
            Message.user(reflect_prompt)
        ]
        
        # 流式反思
        reflection = ""
        resp = self.llm.chat(messages=messages, stream=True)
        
        for msg in resp:
            if msg.reasoning_content:
                self._print_content(msg.reasoning_content)
            if msg.content:
                self._print_content(msg.content, color="green", bold=True)
                reflection += msg.content
        
        # 提取子问题
        lines = reflection.split('\n')
        sub_questions = []
        for line in lines:
            line = line.strip()
            if line and ('?' in line or '？' in line or line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•'))):
                clean_line = line.lstrip('1234567890.-*• ').strip()
                if clean_line and len(clean_line) > 5:  # 过滤太短的问题
                    sub_questions.append(clean_line)
        
        return sub_questions[:3]  # 返回前3个子问题
    
    def generate_final_answer(self, question: str) -> str:
        """生成最终答案"""
        if not self.gathered_info:
            return "抱歉，经过深度搜索后仍未找到相关信息来回答您的问题。"
        
        time_context = self._get_current_time_context()
        research_summary = "\n\n".join([info["analysis"] for info in self.gathered_info])
        search_summary = "\n".join([f"搜索{i+1}: {s['query']}" for i, s in enumerate(self.search_history)])
        
        # 使用Beast Mode提示如果搜索次数较多
        if len(self.search_history) >= 5:
            answer_prompt = DeepResearchPrompts.get_beast_mode_prompt(
                question=question,
                available_info=research_summary
            )
        else:
            answer_prompt = DeepResearchPrompts.get_answer_prompt(
                question=question,
                research_summary=research_summary,
                sources=search_summary,
                key_findings=research_summary
            )
        
        print("\n\n✨ 正在生成最终答案...\n")
        
        system_prompt = f"""{DeepResearchPrompts.get_system_prompt()}
        
答案生成指导：
1. 基于所有搜索和分析结果提供准确答案
2. 包含具体的事实、数据和引用
3. 注明信息的时效性
4. 当前时间：{time_context}
5. 如有不确定性，明确说明
6. 使用清晰的结构和格式
"""
        
        messages = [
            Message.system(system_prompt),
            Message.user(answer_prompt)
        ]
        
        # 流式生成答案
        answer = ""
        resp = self.llm.chat(messages=messages, stream=True)
        
        for msg in resp:
            if msg.reasoning_content:
                self._print_content(msg.reasoning_content)
            if msg.content:
                self._print_content(msg.content, color="green", bold=True)
                answer += msg.content
        
        return answer or "无法生成答案"
    
    def deep_research(self, question: str) -> str:
        """执行深度研究的主要方法 - 基于jina-ai/node-DeepResearch架构"""
        print(f"\n🚀 开始深度研究: {question}")
        print(f"⏰ {self._get_current_time_context()}")
        print("="*80)
        
        # 重置状态
        self.search_history = []
        self.gathered_info = []
        self.sources = []
        
        current_context = ""
        
        # 主要的搜索-阅读-推理循环
        for iteration in range(self.max_iterations):
            print(f"\n\n📍 === 迭代 {iteration + 1}/{self.max_iterations} ===")
            print(f"🔄 Search → Read → Reason 循环")
            
            # 1. Search阶段：使用所有搜索工具
            search_results = self.search_with_all_tools(question, current_context)
            
            # 2. Read阶段：分析和推理搜索结果
            if search_results and search_results != "搜索未返回结果":
                analysis = self.analyze_and_reason(question, search_results)
            else:
                print("\n⚠️ 本轮搜索未获得有效结果")
                continue
            
            # 3. Reason阶段：反思并规划下一步
            if len(self.gathered_info) >= 1:
                sub_questions = self.reflect_and_plan_next(question)
                
                if sub_questions:
                    print(f"\n\n💡 生成了 {len(sub_questions)} 个后续搜索问题:")
                    for i, sq in enumerate(sub_questions, 1):
                        print(f"   {i}. {sq}")
                    current_context = "\n".join(sub_questions[:2])
                else:
                    print("\n✅ 当前信息已足够完整")
            
            # 检查是否有足够信息或达到预期深度
            if len(self.gathered_info) >= 3 or (len(self.gathered_info) >= 2 and not sub_questions):
                print("\n\n✅ 收集到足够信息，准备生成最终答案")
                break
                
            # 如果没有新的搜索方向，提前结束
            if not current_context and iteration > 0:
                print("\n\n🔚 没有新的搜索方向，结束研究")
                break
        
        # 4. Answer阶段：生成最终答案
        print("\n\n" + "="*80)
        final_answer = self.generate_final_answer(question)
        
        print(f"\n\n🎉 深度研究完成!")
        print(f"📊 总迭代次数: {iteration + 1}")
        print(f"🔍 总搜索次数: {len(self.search_history)}")
        print(f"📚 收集信息数量: {len(self.gathered_info)}")
        print(f"⏱️ 研究时长: 约 {(iteration + 1) * 30} 秒")
        print("="*80)
        
        return final_answer
    
    def chat(self, prompt: str, tools: Optional[List[Dict]] = None, tool_choice: str = "auto", stream=True) -> str:
        """聊天接口 - 所有问题都进行深度搜索"""
        # 根据用户要求，所有问题都进行深度搜索
        return self.deep_research(prompt)
    
    def quick_search(self, query: str) -> str:
        """快速搜索方法（保留用于特殊情况）"""
        print(f"\n🔍 快速搜索: {query}\n")
        
        time_context = self._get_current_time_context()
        messages = [
            Message.system(f"你是一个搜索助手。当前时间：{time_context}。请使用所有可用的搜索工具来查找用户需要的信息。"),
            Message.user(f"请使用所有搜索工具搜索: {query}")
        ]
        
        resp = self.llm.chat(messages=messages, tools=self.tools, tool_choice="auto", stream=True)
        
        result = ""
        for msg in resp:
            if msg.reasoning_content:
                self._print_content(msg.reasoning_content)
            if msg.content:
                self._print_content(msg.content, color="green", bold=True)
                result += msg.content
        
        return result


if __name__ == "__main__":
    from config import get_siliconflow_model
    
    # 创建深度搜索代理
    agent = DeepSearchAgent(
        llm_config=get_siliconflow_model(),
        max_iterations=1  # 增加迭代次数以支持更深度的搜索
    )
    
    print("\n🤖 深度搜索代理已启动!")
    print("🔍 基于 jina-ai/node-DeepResearch 架构")
    print("⚡ 所有问题都将进行深度搜索")
    print("💡 输入 'q' 退出")
    print("="*50)
    
    while True:
        question = input("\n❓ 请输入您的问题: ")
        if question.lower() == 'q':
            break
            
        try:
            answer = agent.chat(question)
            print("\n\n" + "="*80)
            print("📝 深度研究结果:")
            print("="*80)
            print(answer)
            print("="*80)
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()