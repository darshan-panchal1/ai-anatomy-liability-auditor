"""
Anatomy-of-Liability Auditor — Agent Graph
LangGraph state machine powering the 4-node analysis pipeline.
"""

import os
import re
import logging
from typing import Annotated, TypedDict, List

from groq import AsyncGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Direct imports replacing MCP servers
from app.tools import lookup_anatomical_entity, get_anatomical_connections, search_liability_precedent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("CRITICAL: GROQ_API_KEY not found in environment.")

# ---------------------------------------------------------------------------
# Agent State
# ---------------------------------------------------------------------------

class AuditorState(TypedDict):
    messages:           Annotated[List[BaseMessage], add_messages]
    anatomical_context: str
    legal_context:      str
    query_plan:         str


# ---------------------------------------------------------------------------
# Groq LLM helper
# ---------------------------------------------------------------------------

groq_client = AsyncGroq(api_key=GROQ_API_KEY)


async def invoke_groq(
    messages: List[BaseMessage],
    system_instruction: str,
    max_tokens: int = 2048,
) -> str:
    """Send a chat completion request to Groq."""
    formatted: List[dict] = [{"role": "system", "content": system_instruction}]

    for m in messages:
        if isinstance(m, HumanMessage):
            formatted.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            formatted.append({"role": "assistant", "content": m.content})

    completion = await groq_client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL"),
        messages=formatted,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


# ---------------------------------------------------------------------------
# Node 1 — Anatomy Extraction
# ---------------------------------------------------------------------------

async def anatomy_node(state: AuditorState) -> dict:
    user_query = state["messages"][0].content
    logger.info("[ANATOMY NODE] Processing query: %.80s...", user_query)

    # Ask the LLM for the primary anatomical term
    term = await invoke_groq(
        [HumanMessage(content=user_query)],
        (
            "You are a medical terminology expert. "
            "Identify the single most relevant primary anatomical structure "
            "mentioned in this legal/medical query. "
            "Return ONLY the anatomical term — no punctuation, no explanation."
        ),
        max_tokens=512,
    )
    term = term.strip().strip('"').strip("'").split("\n")[0]
    logger.info("[ANATOMY NODE] Extracted term: %s", term)

    try:
        lookup_result = await lookup_anatomical_entity(term)

        connections = "No structural connections found."
        qid_match = re.search(r"\b(Q\d+)\b", str(lookup_result))
        if qid_match:
            qid = qid_match.group(1)
            logger.info("[ANATOMY NODE] Fetching connections for QID: %s", qid)
            connections = await get_anatomical_connections(qid)

    except Exception as exc:
        logger.warning("[ANATOMY NODE] Tool call failed: %s", exc, exc_info=True)
        lookup_result = f"Wikidata lookup unavailable: {exc}"
        connections = ""

    context = (
        f"Primary Structure: {term}\n"
        f"Wikidata Resolution:\n{lookup_result}\n\n"
        f"Structural Connections:\n{connections}"
    )

    return {
        "anatomical_context": context,
        "messages": [AIMessage(content=f"Anatomical context resolved for: {term}")],
    }


# ---------------------------------------------------------------------------
# Node 2 — Legal Search Strategy
# ---------------------------------------------------------------------------

async def legal_strategy_node(state: AuditorState) -> dict:
    logger.info("[STRATEGY NODE] Formulating legal search query")

    prompt = (
        f"You are a legal research expert specialising in US medical malpractice and "
        f"personal injury litigation.\n\n"
        f"Case description:\n{state['messages'][0].content}\n\n"
        f"Anatomical context:\n{state['anatomical_context']}\n\n"
        "Construct a precise CourtListener boolean search string that will surface the "
        "most relevant case-law precedents. Focus on: the injured structure, the "
        "mechanism of injury, and applicable legal theories (negligence, informed "
        "consent, standard of care).\n\n"
        "Return ONLY the boolean query string — nothing else."
    )

    query = await invoke_groq(
        [HumanMessage(content=prompt)],
        "You are a precise legal search query generator. Output only the query string.",
        max_tokens=512,
    )
    query = query.strip().strip('"').strip("'").split("\n")[0]
    logger.info("[STRATEGY NODE] Legal query: %s", query)

    return {
        "query_plan": query,
        "messages": [AIMessage(content=f"Legal search strategy formulated: {query}")],
    }


# ---------------------------------------------------------------------------
# Node 3 — Legal Precedent Retrieval
# ---------------------------------------------------------------------------

async def legal_retrieval_node(state: AuditorState) -> dict:
    logger.info("[LEGAL NODE] Retrieving precedents for: %s", state["query_plan"])

    try:
        results = await search_liability_precedent(state["query_plan"])
    except Exception as exc:
        logger.warning("[LEGAL NODE] Tool call failed: %s", exc, exc_info=True)
        results = f"Legal search unavailable: {exc}"

    return {
        "legal_context": str(results),
        "messages": [AIMessage(content="Legal precedents retrieved successfully.")],
    }


# ---------------------------------------------------------------------------
# Node 4 — Synthesis & Report
# ---------------------------------------------------------------------------

async def auditor_synthesis_node(state: AuditorState) -> dict:
    logger.info("[AUDITOR NODE] Synthesising final liability report")

    system_prompt = (
        "You are The Anatomy-of-Liability Auditor — a specialist AI combining "
        "clinical anatomy with US case law to produce actionable liability assessments.\n\n"
        "Write a professional, structured report with the following sections:\n"
        "1. EXECUTIVE SUMMARY\n"
        "2. ANATOMICAL ANALYSIS\n"
        "3. RELEVANT LEGAL PRECEDENTS\n"
        "4. LIABILITY RISK ASSESSMENT\n"
        "5. RECOMMENDED LEGAL THEORIES\n"
        "6. DISCLAIMER\n\n"
        "Be precise, cite the provided cases by name, and clearly distinguish "
        "between established fact and legal opinion."
    )

    content = (
        f"Original Query:\n{state['messages'][0].content}\n\n"
        f"=== ANATOMICAL CONTEXT ===\n{state['anatomical_context']}\n\n"
        f"=== LEGAL PRECEDENTS ===\n{state['legal_context']}"
    )

    report = await invoke_groq(
        [HumanMessage(content=content)],
        system_prompt,
        max_tokens=4096,
    )

    return {"messages": [AIMessage(content=report)]}


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------

def create_agent_graph():
    builder = StateGraph(AuditorState)

    builder.add_node("anatomy",   anatomy_node)
    builder.add_node("strategy",  legal_strategy_node)
    builder.add_node("legal",     legal_retrieval_node)
    builder.add_node("auditor",   auditor_synthesis_node)

    builder.add_edge(START,      "anatomy")
    builder.add_edge("anatomy",  "strategy")
    builder.add_edge("strategy", "legal")
    builder.add_edge("legal",    "auditor")
    builder.add_edge("auditor",  END)

    return builder.compile()


agent_app = create_agent_graph()