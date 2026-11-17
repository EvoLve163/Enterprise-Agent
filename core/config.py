import os
from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量 {name}，请检查 .env")
    return value


LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "deepseek-v4-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
TOP_K = int(os.getenv("TOP_K", "4"))
MAX_REFLECTIONS = int(os.getenv("MAX_REFLECTIONS", "1"))
