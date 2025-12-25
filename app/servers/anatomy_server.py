import asyncio
import httpx
from fastmcp import FastMCP
from typing import List, Dict, Any, Optional

# Initialize the FastMCP server with a descriptive name
mcp = FastMCP("Anatomy-Liability-Knowledge-Base")

# Wikidata SPARQL Endpoint
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "AnatomyLiabilityAuditor/1.0 (Educational/Research)"

@mcp.tool()
async def lookup_anatomical_entity(entity_name: str) -> str:
    """
    Resolves a natural language body part name to a Wikidata Q-ID and description.
    
    Args:
        entity_name: The common name of the body part (e.g., "tibial nerve", "femur")
        
    Returns:
        A formatted string containing the Name, Q-ID, and Description of the top matches
    """
    print(f"[ANATOMY SERVER] Received lookup request for: {entity_name}")
    
    sparql_query = f"""
    SELECT ?item ?itemLabel ?description WHERE {{
      SERVICE wikibase:mwapi {{
        bd:serviceParam wikibase:api "EntitySearch".
        bd:serviceParam wikibase:endpoint "www.wikidata.org".
        bd:serviceParam mwapi:search "{entity_name}".
        bd:serviceParam mwapi:language "en".
        ?item wikibase:apiOutputItem mwapi:item.
        ?num wikibase:apiOrdinal true.
      }}
      # Ensure the item is an anatomical structure
      ?item wdt:P31/wdt:P279* wd:Q4936952.
      ?item schema:description ?description.
      FILTER(LANG(?description) = "en")
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 3
    """
    
    print(f"[ANATOMY SERVER] Querying Wikidata SPARQL endpoint...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                WIKIDATA_ENDPOINT, 
                params={"query": sparql_query, "format": "json"},
                headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            data = response.json()
            
            bindings = data.get("results", {}).get("bindings", [])
            print(f"[ANATOMY SERVER] Found {len(bindings)} results")
            
            if not bindings:
                return f"No anatomical entities found for '{entity_name}'."
            
            results = []
            for b in bindings:
                label = b.get("itemLabel", {}).get("value", "Unknown")
                qid = b.get("item", {}).get("value", "").split("/")[-1]
                desc = b.get("description", {}).get("value", "No description")
                results.append(f"- Name: {label} (ID: {qid})\n  Description: {desc}")
                print(f"[ANATOMY SERVER] Result: {label} ({qid})")
            
            return "\n".join(results)
            
        except httpx.HTTPError as e:
            error_msg = f"Wikidata Network Error: {str(e)}"
            print(f"[ANATOMY SERVER] {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Anatomy Server Error: {str(e)}"
            print(f"[ANATOMY SERVER] {error_msg}")
            return error_msg

@mcp.tool()
async def get_anatomical_connections(qid: str) -> str:
    """
    Retrieves structures physically connected to, part of, or containing the entity.
    Uses Wikidata properties P2789 (connects with) and P361 (part of).
    
    Args:
        qid: The Wikidata Q-ID of the structure (e.g., "Q19602")
        
    Returns:
        A list of connected anatomical structures and their relationship types
    """
    print(f"[ANATOMY SERVER] Fetching connections for: {qid}")
    
    sparql_query = f"""
    SELECT ?connectedLabel ?relation WHERE {{
      {{
        wd:{qid} wdt:P2789 ?connected.
        BIND("physically connects with" AS ?relation)
      }} UNION {{
        wd:{qid} wdt:P361 ?connected.
        BIND("is part of" AS ?relation)
      }} UNION {{
        ?connected wdt:P361 wd:{qid}.
        BIND("contains part" AS ?relation)
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 20
    """
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                WIKIDATA_ENDPOINT, 
                params={"query": sparql_query, "format": "json"},
                headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            data = response.json()
            
            bindings = data.get("results", {}).get("bindings", [])
            print(f"[ANATOMY SERVER] Found {len(bindings)} connections")
            
            if not bindings:
                return f"No structural connections found for {qid}."
            
            connections = []
            for b in bindings:
                rel = b.get("relation", {}).get("value", "related to")
                label = b.get("connectedLabel", {}).get("value", "Unknown")
                connections.append(f"- {rel}: {label}")
                print(f"[ANATOMY SERVER] Connection: {rel} -> {label}")
            
            return "\n".join(connections)
            
        except Exception as e:
            error_msg = f"Connection Query Error: {str(e)}"
            print(f"[ANATOMY SERVER] {error_msg}")
            return error_msg

if __name__ == "__main__":
    print("[ANATOMY SERVER] Starting in stdio mode...")
    # The server runs over stdio, allowing the LangGraph agent to spawn it as a subprocess
    mcp.run(transport="stdio")