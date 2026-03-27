# rp_handler.py
import runpod
import os
from dotenv import load_dotenv

load_dotenv()

from app.agent_graph import agent_app
from langchain_core.messages import HumanMessage

async def handler(job):
    job_input = job.get("input", {})
    query = job_input.get("query", "")
    thread_id = job_input.get("thread_id", "default-thread")

    if not query:
        return {"error": "Missing 'query' field in input"}

    initial_state = {
        "messages": [HumanMessage(content=query)],
        "anatomical_context": "",
        "legal_context": "",
        "query_plan": ""
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_app.ainvoke(initial_state, config=config)

    final_message = result["messages"][-1]
    cases_count = result.get("legal_context", "").count("CASE:")

    return {
        "report": final_message.content,
        "metadata": {
            "anatomical_context_used": bool(result.get("anatomical_context")),
            "legal_query_used": result.get("query_plan", ""),
            "cases_found_count": cases_count,
            "thread_id": thread_id
        }
    }

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})