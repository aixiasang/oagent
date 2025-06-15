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

from prompt import Prompt

class JinaAgentPrompt():
    @staticmethod
    def jina_agent_system_prompt(original_query='', context='', intent=''):
        return Prompt(JINA_AGENT_SYSTEM_PROMPT).format(original_query=original_query, context=context, intent=intent)

    @staticmethod
    def jina_query_rewriter_prompt(original_query='', context='', intent=''):
        return Prompt(JINA_QUERY_REWRITER_PROMPT).format(original_query=original_query, context=context, intent=intent)

    @staticmethod
    def jina_content_analyzer_prompt(query='', source_url='', content_type='', content=''):
        return Prompt(JINA_CONTENT_ANALYZER_PROMPT).format(query=query, source_url=source_url, content_type=content_type, content=content)

    @staticmethod
    def jina_citation_formatter_prompt(sources='', quotes='', context=''):
        return Prompt(JINA_CITATION_FORMATTER_PROMPT).format(sources=sources, quotes=quotes, context=context)

if __name__ == "__main__":
    print(JinaAgentPrompt.jina_agent_system_prompt().text())
    print(JinaAgentPrompt.jina_query_rewriter_prompt().text())
    print(JinaAgentPrompt.jina_content_analyzer_prompt().text())
    print(JinaAgentPrompt.jina_citation_formatter_prompt().text())