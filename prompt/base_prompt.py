from .prompt import register_prompt
from .base.zhuzi import base_prompt,enhanced_user_prompt


@register_prompt
def base_prompt():
    return base_prompt
@register_prompt
def enhanced_user_prompt():
    return enhanced_user_prompt