import stat
from sympy import im
from zhipuai import ZhipuAI
from .register import register_tool
from typing import Dict, Any, List, cast
import os
@register_tool
def zhipu_web_search(
        search_query: str, 
        search_engine: str = "search_std",
        count: int = 10, 
        search_domain_filter: str = "", 
        search_recency_filter: str = "noLimit", 
        content_size: str = "medium"
        ) -> Dict[str, Any]:
    """
    {
        "func": "ZhipuAi Web Search",
        "params": {
            "search_query": "需要进行搜索的内容, 建议搜索 query 不超过 78 个字符",
            "search_egine":"要调用的搜索引擎编码，可以是其中的一个参数search_std/search_pro_sogou/search_pro_jina/search_pro_bing,默认是search_std",
            "count": "返回结果的条数，范围1-50，默认10",
            "search_domain_filter": "只访问指定域名的内容，默认是空白",
            "search_recency_filter": "搜索指定日期范围内的内容，默认是无限制",
            "content_size":"控制网页摘要的字数，默认medium"
        }
    }
    """
    api_key=os.getenv('zhipuai')
    client = ZhipuAI(api_key=api_key)  # 填写您自己的APIKey
    
    return client.web_search.web_search(
        search_engine=search_engine,
        search_query=search_query,
        count=count,
        search_domain_filter=search_domain_filter,
        search_recency_filter=search_recency_filter,
        content_size=content_size
    )
@register_tool
def search_wiki(entity: str,sentences=10, auto_suggest=False) -> str:
    """
    {
        "func": "Search the entity in WikiPedia and return the summary of the required page, containing factual information about the given entity.",
        "params": {
            "entity": "The entity to search for.",
            "sentences": "if set, return the first `sentences` sentences (can be no greater than 10)",
            "auto_suggest":"let Wikipedia find a valid page title for the query"
        }
    }
    """
    import wikipedia
    result: str

    try:
        result = wikipedia.summary(entity, sentences=sentences, auto_suggest=auto_suggest)
    except wikipedia.exceptions.DisambiguationError as e:
        result = wikipedia.summary(
            e.options[0], sentences=5, auto_suggest=False
        )
    except wikipedia.exceptions.PageError:
        result = (
            "There is no page in Wikipedia corresponding to entity "
            f"{entity}, please specify another word to describe the"
            " entity to be searched."
        )
    except wikipedia.exceptions.WikipediaException as e:
        result = f"An exception occurred during the search: {e}"

    return result
@register_tool
def search_duckduckgo(query: str, source: str = "text", max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        {
            "func": "Use DuckDuckGo search engine to search information for the given query. This function queries the DuckDuckGo API for related topics to the given search term. The results are formatted into a list of  dictionaries, each representing a search result.",
            "params": {
                "query": "The query to search for",
                "source": "The type of information to query (e.g., 'text','images', 'videos'). Defaults to 'text'.",
                "max_results": "Max number of results, defaults to `5`"
            }
        }
        """
        from duckduckgo_search import DDGS
        from requests.exceptions import RequestException

        ddgs = DDGS()
        responses: List[Dict[str, Any]] = []

        if source == "text":
            try:
                results = ddgs.text(keywords=query, max_results=max_results)
            except RequestException as e:
                responses.append({"error": f"duckduckgo search failed.{e}"})

            for i, result in enumerate(results, start=1):
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "description": result["body"],
                    "url": result["href"],
                }
                responses.append(response)

        elif source == "images":
            try:
                results = ddgs.images(keywords=query, max_results=max_results)
            except RequestException as e:
                responses.append({"error": f"duckduckgo search failed.{e}"})

            for i, result in enumerate(results, start=1):
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "image": result["image"],
                    "url": result["url"],
                    "source": result["source"],
                }
                responses.append(response)

        elif source == "videos":
            try:
                results = ddgs.videos(keywords=query, max_results=max_results)
            except RequestException as e:
                responses.append({"error": f"duckduckgo search failed.{e}"})

            for i, result in enumerate(results, start=1):
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "description": result["description"],
                    "embed_url": result["embed_url"],
                    "publisher": result["publisher"],
                    "duration": result["duration"],
                    "published": result["published"],
                }
                responses.append(response)
        return responses
@register_tool
def search_baidu( query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    {
        "func":"earch Baidu using web scraping to retrieve relevant search results. This method queries Baidu's search engine and extracts search results including titles, descriptions, and URLs",
        "params":{
            "query": "Search query string to submit to Baidu.",
            "max_results": "Maximum number of results to return."
        }
    }
    """
    from bs4 import BeautifulSoup
    import requests
    try:
        url = "https://www.baidu.com/s"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.baidu.com",
        }
        params = {"wd": query, "rn": str(max_results)}
        response = requests.get(url, headers=headers, params=params)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for idx, item in enumerate(soup.select(".result"), 1):
            title_element = item.select_one("h3 > a")
            title = (
                title_element.get_text(strip=True) if title_element else ""
            )
            link = title_element["href"] if title_element else ""
            desc_element = item.select_one(".c-abstract, .c-span-last")
            desc = (
                desc_element.get_text(strip=True) if desc_element else ""
            )
            results.append(
                {
                    "result_id": idx,
                    "title": title,
                    "description": desc,
                    "url": link,
                }
            )
            if len(results) >= max_results:
                break
        if not results:
            print(
                "Warning: No results found. Check "
                "if Baidu HTML structure has changed."
            )
        return {"results": results}
    except Exception as e:
        return {"error": f"Baidu scraping error: {e!s}"}

def get_search_web_tools_name():
    return ['zhipu_web_search', 'search_baidu','search_duckduckgo','search_wiki']

if __name__ == "__main__":
    from .register import get_registered_tools,get_tool_list
    # print(get_tool_list(["search_baidu"]))
    # query="三星手机的最新款"
    # print(zhipu_web_search(query))
    # print(search_baidu(query))
