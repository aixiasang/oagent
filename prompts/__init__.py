from .openai_agent import AgentSquadPrompt
from .role_play import RolePlayPrompt
from .deep_research import DeepResearchPrompts
from .jina_agent import JinaAgentPrompts
from .ai_girlfriend import AIGirlfriendPrompts,AIGirlfriendMemory
from .programor import ProgramorPrompt
__all__ = [
    "AgentSquadPrompt",
    "RolePlayPrompt", 
    "DeepResearchPrompts",
    "JinaAgentPrompts",
    AIGirlfriendPrompts,
    AIGirlfriendMemory,
    ProgramorPrompt
]