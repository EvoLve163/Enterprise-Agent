from langchain_openai import ChatOpenAI

from core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID, LLM_TEMPERATURE, LLM_TIMEOUT


def build_llm() -> ChatOpenAI:
    if not LLM_API_KEY:
        raise RuntimeError("缺少 LLM_API_KEY，请先配置 .env")
    return ChatOpenAI(
        model=LLM_MODEL_ID,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=LLM_TEMPERATURE,
        timeout=LLM_TIMEOUT,
        max_retries=2,

        extra_body={
            "thinking": {
                "type": "disabled"
            }
        }
    )