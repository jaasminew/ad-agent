# tools.py
import os
import logging
from langchain.tools import tool
from tavily import TavilyClient

# Configure logging
logger = logging.getLogger(__name__)

# Lazy initialization of TavilyClient to avoid requiring API key at import time
_tav = None

def get_tavily_client():
    global _tav
    if _tav is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        _tav = TavilyClient(api_key=api_key)
        logger.info("✓ Tavily client initialized")
    return _tav

MEM = []

@tool("web_search")
def web_search(query: str) -> str:
    """Search the web for factual/background context. Return concise bullets with URLs."""
    logger.info(f"🔍 [web_search] Called - Query: '{query}'")
    tav = get_tavily_client()
    res = tav.search(query=query, max_results=5)
    out = []
    for r in res.get("results", []):
        out.append(f"- {r['title']} | {r['url']}\n  {r['content'][:300]}…")
    result = "\n".join(out) or "(no results)"
    logger.info(f"✓ [web_search] Returned {len(res.get('results', []))} results")
    return result

@tool("remember")
def remember(note: str) -> str:
    """Store a note for this session."""
    logger.info(f"💾 [remember] Storing note: '{note[:50]}...'")
    MEM.append(note)
    result = f"stored ({len(MEM)} total)"
    logger.info(f"✓ [remember] Note stored, total count: {len(MEM)}")
    return result

@tool("recall")
def recall(_: str="") -> str:
    """Return all stored notes."""
    logger.info(f"🔖 [recall] Retrieving notes - Current count: {len(MEM)}")
    result = "\n".join(MEM) or "(empty)"
    logger.info(f"✓ [recall] Returned {len(MEM)} notes")
    return result

