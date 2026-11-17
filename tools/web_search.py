import requests
from langchain.tools import tool

from core.config import SERPAPI_API_KEY


@tool("web_search")
def web_search(query: str) -> str:
    """Search the public web for recent or external information.

    Use when the private knowledge base is insufficient or the user explicitly asks for public web information.
    """
    if not SERPAPI_API_KEY:
        return "Web Search 未配置 SERPAPI_API_KEY，请先在 .env 中配置。"

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": query, "api_key": SERPAPI_API_KEY, "hl": "zh-cn"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        organic = data.get("organic_results", [])[:5]
        if not organic:
            return "没有找到公开网页结果。"

        results = []
        for i, item in enumerate(organic, start=1):
            results.append(
                f"""
            [网页证据{i}]
            标题：
            {item.get('title', '')}

            来源网站：
            {item.get('displayed_link', item.get('link', ''))}

            摘要：
            {item.get('snippet', '')}

            链接：
            {item.get('link', '')}
            """
            )
        return "\n\n".join(results)
    except Exception as exc:
        return f"Web Search 失败：{exc}"
