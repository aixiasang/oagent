# Jina AI Agent Prompts
# Additional prompts inspired by Jina AI's approach

JINA_AGENT_SYSTEM_PROMPT = r"""
You are an intelligent research agent powered by Jina AI's technology stack.
You excel at:
- Semantic search and information retrieval
- Multi-modal understanding (text, images, documents)
- Iterative reasoning and research
- Providing accurate, well-cited responses

Your approach:
1. Break down complex questions into manageable parts
2. Use multiple search strategies to gather comprehensive information
3. Cross-reference sources for accuracy
4. Synthesize findings into clear, actionable insights
5. Always provide proper citations and source attribution

Maintain a balance between thoroughness and efficiency.
"""

JINA_QUERY_REWRITER_PROMPT = r"""
Rewrite the following query to improve search effectiveness.

Original Query: {original_query}
Context: {context}
Search Intent: {intent}

Optimize for:
- Specific keywords and terminology
- Better semantic matching
- Reduced ambiguity
- Improved recall of relevant documents

Rewritten Query:
"""

JINA_CONTENT_ANALYZER_PROMPT = r"""
Analyze the following content for relevance and extract key information.

Query: {query}
Source: {source_url}
Content Type: {content_type}
Content: {content}

Provide:
1. Relevance Score (1-10)
2. Key Information Extracted
3. Supporting Quotes
4. Confidence Level
5. Recommended Follow-up Actions

Analysis:
"""

JINA_CITATION_FORMATTER_PROMPT = r"""
Format the following information into proper citations.

Sources: {sources}
Quotes: {quotes}
Context: {context}

Format as:
- Numbered references [1], [2], etc.
- Include exact quotes
- Provide accessible URLs
- Follow academic citation standards

Formatted Citations:
"""

class JinaAgentPrompts:
    """Jina AI inspired agent prompts"""
    
    @staticmethod
    def get_system_prompt():
        return JINA_AGENT_SYSTEM_PROMPT
    
    @staticmethod
    def get_query_rewriter_prompt(original_query, context="", intent="general"):
        return JINA_QUERY_REWRITER_PROMPT.format(
            original_query=original_query,
            context=context,
            intent=intent
        )
    
    @staticmethod
    def get_content_analyzer_prompt(query, source_url, content_type, content):
        return JINA_CONTENT_ANALYZER_PROMPT.format(
            query=query,
            source_url=source_url,
            content_type=content_type,
            content=content
        )
    
    @staticmethod
    def get_citation_formatter_prompt(sources, quotes, context):
        return JINA_CITATION_FORMATTER_PROMPT.format(
            sources=sources,
            quotes=quotes,
            context=context
        )