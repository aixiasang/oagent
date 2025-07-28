from ._base import react_prompt,fncall_prompt,miziha_prompt,roleplay_prompt,li_bai_prompt,get_tool_descs
from ._other import cursor_agent_prompt as programor_prompt
from ._rag import rag_prompt
from ._agents import control_user_prompt,control_system_prompt
all=[
    get_tool_descs,
    miziha_prompt,
    roleplay_prompt,
    li_bai_prompt,
    react_prompt,
    fncall_prompt,
    programor_prompt,
    rag_prompt,
    control_system_prompt,
    control_user_prompt
]