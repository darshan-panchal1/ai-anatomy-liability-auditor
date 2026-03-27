import os
import httpx
from typing import Optional

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "AnatomyLiabilityAuditor/1.0 (Educational/Research)"


async def lookup_anatomical_entity(entity_name: str) -> str:
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
      ?item wdt:P31/wdt:P279* wd:Q4936952.
      ?item schema:description ?description.
      FILTER(LANG(?description) = "en")
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 3
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
            if not bindings:
                return f"No anatomical entities found for '{entity_name}'."
            results = []
            for b in bindings:
                label = b.get("itemLabel", {}).get("value", "Unknown")
                qid = b.get("item", {}).get("value", "").split("/")[-1]
                desc = b.get("description", {}).get("value", "No description")
                results.append(f"- Name: {label} (ID: {qid})\n  Description: {desc}")
            return "\n".join(results)
        except Exception as e:
            return f"Anatomy Server Error: {str(e)}"


async def get_anatomical_connections(qid: str) -> str:
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
            if not bindings:
                return f"No structural connections found for {qid}."
            connections = []
            for b in bindings:
                rel = b.get("relation", {}).get("value", "related to")
                label = b.get("connectedLabel", {}).get("value", "Unknown")
                connections.append(f"- {rel}: {label}")
            return "\n".join(connections)
        except Exception as e:
            return f"Connection Query Error: {str(e)}"


async def search_liability_precedent(
    query: str,
    jurisdiction: Optional[str] = None,
    min_date: Optional[str] = None
) -> str:
    api_key = os.environ.get("COURTLISTENER_API_KEY")
    if not api_key:
        return "Error: CourtListener API key not configured."

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "q": query,
        "type": "o",
        "order_by": "score desc",
        "stat_Precedential": "on"
    }
    if jurisdiction:
        params["court"] = jurisdiction
    if min_date:
        params["filed_after"] = min_date

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                "https://www.courtlistener.com/api/rest/v4/search/",
                headers=headers,
                params=params
            )
            if response.status_code == 429:
                return "Error: CourtListener API rate limit exceeded. Please try again later."
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return f"No case law found for query: '{query}'."
            formatted_cases = []
            for i, case in enumerate(results[:5], 1):
                case_name = case.get("caseName", "Unknown Case")
                date_filed = case.get("dateFiled", "Unknown Date")
                court = case.get("court_citation_string", "Unknown Court")
                raw_snippet = case.get("snippet", "No text snippet available.")
                clean_snippet = raw_snippet.replace("<em>", "").replace("</em>", "")
                citation = case.get("citation", ["No citation"])
                if isinstance(citation, list):
                    citation = citation[0] if citation else "No citation"
                entry = (
                    f"{i}. CASE: {case_name} ({citation})\n"
                    f"   COURT: {court} | DATE: {date_filed}\n"
                    f"   RELEVANCE: {clean_snippet[:500]}...\n"
                )
                formatted_cases.append(entry)
            return "\n".join(formatted_cases)
        except Exception as e:
            return f"Search execution failed: {str(e)}"