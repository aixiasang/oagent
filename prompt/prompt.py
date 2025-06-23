import re
from functools import wraps

_PROMPT_REGISTRY = {}

def register_prompt(name: str = None, rewrite: bool = True):
    """
    注册提示模板的装饰器
    
    :param name: 模板在注册表中的名称（默认使用函数名）
    :param rewrite: 是否允许重写已存在的模板（默认True）
    """
    def decorator(func):
        prompt_name = name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            template = func(*args, **kwargs)
            
            if not rewrite and prompt_name in _PROMPT_REGISTRY:
                raise ValueError(f"提示模板 '{prompt_name}' 已存在且不允许重写")
            
            prompt = Prompt(template)
            _PROMPT_REGISTRY[prompt_name] = prompt
            return prompt
        
        return wrapper()
    
    if callable(name):
        func = name
        prompt_name = func.__name__
        template = func()
        prompt = Prompt(template)
        _PROMPT_REGISTRY[prompt_name] = prompt
        return prompt
    
    return decorator

def get_prompt(name: str) -> 'Prompt':
    """
    从注册表获取提示模板
    
    :param name: 模板名称
    :return: Prompt实例
    """
    return _PROMPT_REGISTRY.get(name)

def list_prompts() -> list:
    """
    获取所有注册的模板名称
    
    :return: 模板名称列表
    """
    return list(_PROMPT_REGISTRY.keys())

class Prompt:
    """
    提示模板类，支持链式格式化和原始内容访问
    """
    def __init__(self, template: str):
        """
        初始化提示模板
        
        :param template: 提示模板字符串
        """
        self._template = template
        self.placeholders = self._extract_placeholders(template)
    
    def text(self) -> str:
        """获取模板的原始文本内容"""
        return self._template
    
    def txt(self, default: str = "") -> str:
        """
        获取模板内容，未格式化的占位符替换为默认值
        
        :param default: 未格式化占位符的默认值
        :return: 处理后的模板字符串
        """
        result = self._template
        for placeholder in self.placeholders:
            result = result.replace(
                f"{{{placeholder}}}", 
                default)
        return result
    
    def _extract_placeholders(self, template: str) -> set:
        """提取模板中的占位符"""
        return set(re.findall(r'\{(\w+)\}', template))
    
    def format(self, **kwargs) -> 'Prompt':
        """预处理一下 如果value是空的话，则移除 格式化模板，将占位符替换为对应的值"""
        params = {k: v for k, v in kwargs.items() if v}
        return self.formated(**params)
       
    
    def formated(self, **kwargs) -> 'Prompt':
        """格式化模板，将占位符替换为对应的值"""
        formatted = self._template
        for placeholder in self.placeholders:
            if placeholder not in kwargs:
                continue
            formatted = formatted.replace(
                f"{{{placeholder}}}", 
                str(kwargs[placeholder]))
        return Prompt(formatted)
    
    
    @classmethod
    def from_config(cls, config: dict):
        """
        从配置字典创建实例
        
        :param config: 包含template的字典
        :return: Prompt实例
        """
        return cls(template=config.get("template", ""))
    
    def to_config(self) -> dict:
        """
        将当前配置导出为字典
        
        :return: 包含模板的字典
        """
        return {"template": self._template}
    
    def merge(self, other: 'Prompt') -> 'Prompt':
        """
        合并两个提示模板
        
        :param other: 另一个Prompt实例
        :return: 合并后的新实例
        """
        return Prompt(
            template=self._template + "\n" + other._template
        )
    
    def get_placeholders(self) -> set:
        """
        获取模板中的所有占位符
        
        :return: 占位符集合
        """
        return self.placeholders



if __name__ == "__main__":
    @register_prompt
    def coding_assistant():
        return r"""
    你是一个{role}助手，请根据用户请求提供帮助。
    当前时间: {current_time}
    操作系统: {os_info}
    用户请求: {user_query}
    上下文信息: {context}
        """

    @register_prompt("debug_helper")
    def debugging_template():
        return r"""
    你是一个{language}调试专家，请帮助解决以下问题：
    问题描述: {problem}
    错误信息: {error}
    代码片段: {code_snippet}
    附加说明: {notes}
        """

    @register_prompt(name="data_analysis", rewrite=False)
    def analysis_template():
        return r"""
    你是一个数据分析专家，请处理以下数据：
    数据集: {dataset}
    分析目标: {goal}
    时间范围: {time_range}
    附加要求: {requirements}
        """

    try:
        @register_prompt(name="data_analysis", rewrite=False)
        def duplicate_analysis():
            return "重复模板"
    except ValueError as e:
        print(f"捕获异常: {e}")
    print("注册的模板:", list_prompts())
    
    coding_prompt = get_prompt("coding_assistant")
    print("\n编程助手模板占位符:", coding_prompt.get_placeholders())
    
    formatted = coding_prompt.format(
        role="Python编程",
        current_time="2023-10-15",
        os_info="Linux",
        user_query="实现快速排序",
    )
    print("*"*50)
    print(formatted.text())
    print("*"*50)
    print(formatted.txt())
    print("*"*50)
    data=formatted.format(context="项目使用Python 3.10")
    print(data.text())