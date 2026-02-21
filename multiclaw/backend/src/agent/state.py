from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import add_messages
from typing_extensions import Annotated


import operator


class OverallState(TypedDict):
    messages: Annotated[list, add_messages]
    search_query: Annotated[list, operator.add]
    web_research_result: Annotated[list, operator.add]
    sources_gathered: Annotated[list, operator.add]
    initial_search_query_count: int
    max_research_loops: int
    research_loop_count: int
    reasoning_model: str


class ReflectionState(TypedDict):
    is_sufficient: bool
    knowledge_gap: str
    follow_up_queries: Annotated[list, operator.add]
    research_loop_count: int
    number_of_ran_queries: int


class Query(TypedDict):
    query: str
    rationale: str


class QueryGenerationState(TypedDict):
    search_query: list[Query]


class WebSearchState(TypedDict):
    search_query: str
    id: str


@dataclass(kw_only=True)
class SearchStateOutput:
    running_summary: str = field(default=None)  # Final report


# Perplexity + Gemini Research State
from langchain_core.messages import BaseMessage

class ResearchState(TypedDict):
    """리서치 에이전트 상태"""
    messages: Annotated[list[BaseMessage], add_messages]
    query: str
    image: str  # 이미지 Base64 추가
    search_results: list[dict]
    citations: list[str]
    related_questions: list[str]
    analysis: str
    final_answer: str
    iteration: int
    needs_more_research: bool
