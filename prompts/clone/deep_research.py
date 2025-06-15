from prompt import register_prompt,Prompt

DEEP_RESEARCH_SYSTEM_PROMPT = r"""
You are a deep research agent that keeps searching, reading webpages, and reasoning until you find the answer or exceed the token budget.

Your goal is to provide accurate, well-researched answers by following this iterative process:
1. Search for relevant information
2. Read and analyze content from reliable sources  
3. Reason about the information gathered
4. Continue searching if more information is needed
5. Provide a final answer with proper citations

You have access to the following actions:
- search: Perform keyword-based searches
- read: Read and analyze webpage content
- reflect: Generate clarifying sub-questions to fill knowledge gaps
- answer: Provide final answer with supporting references

Always include exact quotes and URLs as supporting references in your final answer.
"""

DEEP_RESEARCH_SEARCH_PROMPT = r"""
Based on the current question and context, generate a focused search query.

Original Question: {question}
Current Context: {context}
Previous Searches: {previous_searches}

Generate a search query that will help find new, relevant information not already covered.
Focus on specific keywords and avoid overly broad terms.

Search Query:
"""

DEEP_RESEARCH_READ_PROMPT = r"""
Analyze the following webpage content and extract key information relevant to the research question.

Question: {question}
URL: {url}
Content: {content}

Extract:
1. Key facts and data points
2. Relevant quotes with exact text
3. Supporting evidence
4. Any contradictory information
5. Areas that need further investigation

Provide a structured summary of the most important findings.
"""

DEEP_RESEARCH_REFLECT_PROMPT = r"""
Based on the information gathered so far, identify knowledge gaps and generate clarifying questions.

Original Question: {question}
Information Gathered: {gathered_info}
Sources Consulted: {sources}

Analyze what information is still missing and generate 3-5 specific sub-questions that would help:
1. Fill important knowledge gaps
2. Verify conflicting information
3. Provide more comprehensive coverage
4. Add supporting evidence

Sub-questions:
"""

DEEP_RESEARCH_ANSWER_PROMPT = r"""
Provide a comprehensive final answer based on all the research conducted.

Original Question: {question}
Research Summary: {research_summary}
Sources: {sources}
Key Findings: {key_findings}

Requirements for your answer:
1. Directly address the original question
2. Include specific facts and data points
3. Provide exact quotes from sources
4. Include proper citations with URLs
5. Acknowledge any limitations or uncertainties
6. Use clear, well-structured formatting

Final Answer:
"""

DEEP_RESEARCH_BEAST_MODE_PROMPT = r"""
You are now in "Beast Mode" - the token budget is nearly exceeded, so you must provide the best possible answer with the information currently available.

Even if you feel uncertain, synthesize the available information and provide a comprehensive response.
Clearly indicate any areas of uncertainty or where additional research would be beneficial.

Question: {question}
Available Information: {available_info}

Provide your best answer now:
"""
class DeepResearchPrompt():
    @staticmethod
    def deep_research_beast_mode_prompt(question='', available_info=''):
        return Prompt(DEEP_RESEARCH_BEAST_MODE_PROMPT).format(question=question, available_info=available_info)

    @staticmethod
    def deep_research_answer_prompt(question='', research_summary='', sources='', key_findings=''):
        return Prompt(DEEP_RESEARCH_ANSWER_PROMPT).format(question=question, research_summary=research_summary, sources=sources, key_findings=key_findings)
    
    @staticmethod
    def deep_research_reflect_prompt(question='', gathered_info='', sources=''):
        return Prompt(DEEP_RESEARCH_REFLECT_PROMPT).format(question=question, gathered_info=gathered_info, sources=sources)
    
    @staticmethod
    def deep_research_read_prompt(question='', url='', content=''):
        return Prompt(DEEP_RESEARCH_READ_PROMPT).format(question=question, url=url, content=content)
    
    @staticmethod
    def deep_research_search_prompt(question='', previous_searches='', context=''):
        return Prompt(DEEP_RESEARCH_SEARCH_PROMPT).format(question=question, previous_searches=previous_searches, context=context)
    
    @staticmethod
    def deep_research_system_prompt():
        return Prompt(DEEP_RESEARCH_SYSTEM_PROMPT)
    
if __name__ == "__main__":
    print(DeepResearchPrompt.deep_research_beast_mode_prompt().text())
    print(DeepResearchPrompt.deep_research_answer_prompt().text())
    print(DeepResearchPrompt.deep_research_reflect_prompt().text())
    print(DeepResearchPrompt.deep_research_read_prompt().text())
    print(DeepResearchPrompt.deep_research_search_prompt().text())