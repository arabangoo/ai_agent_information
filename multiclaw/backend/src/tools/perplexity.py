"""Perplexity API 검색 도구"""
import os
from typing import Literal
import httpx
from langchain_core.tools import tool

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


@tool
async def perplexity_search(
    query: str,
    search_recency: Literal["hour", "day", "week", "month", "year"] = "month"
) -> dict:
    """
    Perplexity API로 최신 웹 정보를 검색합니다.
    
    Args:
        query: 검색할 질문
        search_recency: 검색 시간 범위
    
    Returns:
        검색 결과, 출처, 관련 질문
    """
    
    if not PERPLEXITY_API_KEY:
        return {
            "error": "PERPLEXITY_API_KEY not found",
            "content": "",
            "citations": []
        }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise research assistant providing accurate information."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "search_recency_filter": search_recency,
        "return_citations": True,
        "return_related_questions": True,
        "temperature": 0.2,
        "top_p": 0.9,
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                PERPLEXITY_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "content": result["choices"][0]["message"]["content"],
                "citations": result.get("citations", []),
                "related_questions": result.get("related_questions", []),
                "model": result.get("model", "unknown"),
                "usage": result.get("usage", {})
            }
            
    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = e.response.text
        except:
            pass
        print(f"❌ Perplexity API Error: {e.response.status_code}")
        print(f"❌ Error Detail: {error_detail}")
        return {
            "error": f"API Error: {e.response.status_code} - {error_detail}",
            "content": "",
            "citations": []
        }
    except Exception as e:
        print(f"❌ Search Error: {str(e)}")
        return {
            "error": str(e),
            "content": "",
            "citations": []
        }
