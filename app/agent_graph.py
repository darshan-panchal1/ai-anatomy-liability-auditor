import os
import sys
import re
from typing import Annotated, TypedDict, List, Optional, Dict

from groq import AsyncGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

# -------------------------------------------------------------------
# Configuration & Environment
# -------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("CRITICAL: GROQ_API_KEY not found in environment.")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ANATOMY_SCRIPT = os.path.join(CURRENT_DIR, "servers", "anatomy_server.py")
LEGAL_SCRIPT = os.path.join(CURRENT_DIR, "servers", "legal_server.py")

# -------------------------------------------------------------------
# Global MCP Client (singleton)
# -------------------------------------------------------------------

mcp_client: Optional[MultiServerMCPClient] = None

async def get_mcp_client() -> MultiServerMCPClient:
    global mcp_client

    if mcp_client is None:
        print("[MCP CLIENT] Initializing MCP client")

        mcp_client = MultiServerMCPClient(
            {
                "anatomy": {
                    "command": sys.executable,
                    "args": [ANATOMY_SCRIPT],
                    "transport": "stdio",
                    "env": dict(os.environ),
                },
                "legal": {
                    "command": sys.executable,
                    "args": [LEGAL_SCRIPT],
                    "transport": "stdio",
                    "env": dict(os.environ),
                },
            }
        )

        tools = await mcp_client.get_tools()
        print("[MCP CLIENT] Available tools:", [t.name for t in tools])

    return mcp_client

# -------------------------------------------------------------------
# MCP Tool Invocation Helper (CRITICAL FIX)
# -------------------------------------------------------------------

_tool_cache: Dict[str, Dict[str, BaseTool]] = {}

async def invoke_mcp_tool(
    client: MultiServerMCPClient,
    server_name: str,
    tool_name: str,
    args: dict,
):
    """
    Correct way to invoke MCP tools.
    """
    if server_name not in _tool_cache:
        tools = await client.get_tools(server_name=server_name)
        _tool_cache[server_name] = {t.name: t for t in tools}

    tool = _tool_cache[server_name].get(tool_name)
    if not tool:
        raise ValueError(
            f"Tool '{tool_name}' not found on server '{server_name}'. "
            f"Available: {list(_tool_cache[server_name].keys())}"
        )

    return await tool.ainvoke(args)

# -------------------------------------------------------------------
# Agent State
# -------------------------------------------------------------------

class AuditorState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    anatomical_context: str
    legal_context: str
    query_plan: str

# -------------------------------------------------------------------
# Groq Client
# -------------------------------------------------------------------

groq_client = AsyncGroq(api_key=GROQ_API_KEY)

async def invoke_groq(messages: List[BaseMessage], system_instruction: str) -> str:
    formatted = [{"role": "system", "content": system_instruction}]

    for m in messages:
        if isinstance(m, HumanMessage):
            formatted.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            formatted.append({"role": "assistant", "content": m.content})

    completion = await groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=formatted,
        temperature=0.2,
        max_tokens=2048,
    )

    return completion.choices[0].message.content

# -------------------------------------------------------------------
# Nodes
# -------------------------------------------------------------------

async def anatomy_node(state: AuditorState):
    user_query = state["messages"][-1].content
    print("[ANATOMY NODE] Query:", user_query)

    term = await invoke_groq(
        [HumanMessage(content=user_query)],
        "Identify the primary anatomical structure. Return ONLY the term.",
    )
    term = term.strip().strip('"').strip("'")
    print("[ANATOMY NODE] Term:", term)

    client = await get_mcp_client()

    try:
        lookup_result = await invoke_mcp_tool(
            client,
            "anatomy",
            "lookup_anatomical_entity",
            {"entity_name": term},
        )

        connections = "No connections found."
        qid_match = re.search(r"(Q\d+)", str(lookup_result))
        if qid_match:
            qid = qid_match.group(1)
            connections = await invoke_mcp_tool(
                client,
                "anatomy",
                "get_anatomical_connections",
                {"qid": qid},
            )

    except Exception as e:
        lookup_result = f"ERROR: {e}"
        connections = ""

    context = (
        f"Target Structure: {term}\n"
        f"Wikidata Resolution:\n{lookup_result}\n\n"
        f"Structural Connections:\n{connections}"
    )

    return {
        "anatomical_context": context,
        "messages": [AIMessage(content=f"Anatomical context resolved for {term}")],
    }

# -------------------------------------------------------------------

async def legal_strategy_node(state: AuditorState):
    prompt = (
        "Create a CourtListener boolean search query.\n\n"
        f"User Query:\n{state['messages'][0].content}\n\n"
        f"Anatomical Context:\n{state['anatomical_context']}\n\n"
        "Return ONLY the query string."
    )

    query = await invoke_groq([], prompt)
    query = query.strip().strip('"').strip("'")

    return {
        "query_plan": query,
        "messages": [AIMessage(content=f"Legal search strategy: {query}")],
    }

# -------------------------------------------------------------------

async def legal_retrieval_node(state: AuditorState):
    client = await get_mcp_client()

    try:
        results = await invoke_mcp_tool(
            client,
            "legal",
            "search_liability_precedent",
            {"query": state["query_plan"]},
        )
    except Exception as e:
        results = f"ERROR: {e}"

    return {
        "legal_context": str(results),
        "messages": [AIMessage(content="Legal precedents retrieved.")],
    }

# -------------------------------------------------------------------

async def auditor_synthesis_node(state: AuditorState):
    system_prompt = (
        "You are The Anatomy-of-Liability Auditor.\n"
        "Write a professional liability report using anatomy + case law."
    )

    content = (
        f"User Query:\n{state['messages'][0].content}\n\n"
        f"ANATOMY:\n{state['anatomical_context']}\n\n"
        f"LEGAL:\n{state['legal_context']}"
    )

    report = await invoke_groq([HumanMessage(content=content)], system_prompt)

    return {"messages": [AIMessage(content=report)]}

# -------------------------------------------------------------------
# Graph Assembly
# -------------------------------------------------------------------

def create_agent_graph():
    builder = StateGraph(AuditorState)

    builder.add_node("anatomy", anatomy_node)
    builder.add_node("strategy", legal_strategy_node)
    builder.add_node("legal", legal_retrieval_node)
    builder.add_node("auditor", auditor_synthesis_node)

    builder.add_edge(START, "anatomy")
    builder.add_edge("anatomy", "strategy")
    builder.add_edge("strategy", "legal")
    builder.add_edge("legal", "auditor")
    builder.add_edge("auditor", END)

    return builder.compile()

agent_app = create_agent_graph()
