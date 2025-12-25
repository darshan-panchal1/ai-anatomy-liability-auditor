import os
import httpx
from fastmcp import FastMCP
from typing import Optional

# Initialize the Legal Knowledge Base Server
mcp = FastMCP("Legal-Liability-Archive")

# Configuration
COURTLISTENER_API_KEY = os.environ.get("COURTLISTENER_API_KEY")
SEARCH_ENDPOINT = "https://www.courtlistener.com/api/rest/v4/search/"

if not COURTLISTENER_API_KEY:
    print("WARNING: COURTLISTENER_API_KEY is not set. Legal tools will fail.")

@mcp.tool()
async def search_liability_precedent(
    query: str, 
    jurisdiction: Optional[str] = None,
    min_date: Optional[str] = None
) -> str:
    """
    Search US Federal Case Law for liability precedents using Boolean queries.
    
    Args:
        query: The boolean search string (e.g., "negligence AND 'femoral nerve'")
        jurisdiction: Optional court filter (e.g., "scotus" for Supreme Court, "ca9")
        min_date: Optional start date in YYYY-MM-DD format
        
    Returns:
        A structured summary of the top 5 relevant cases including snippets
    """
    print(f"[LEGAL SERVER] Received search request")
    print(f"[LEGAL SERVER] Query: {query}")
    print(f"[LEGAL SERVER] API Key configured: {bool(COURTLISTENER_API_KEY)}")
    
    if not COURTLISTENER_API_KEY:
        error_msg = "Error: CourtListener API key not configured. Set COURTLISTENER_API_KEY environment variable."
        print(f"[LEGAL SERVER] {error_msg}")
        return error_msg
    
    headers = {
        "Authorization": f"Token {COURTLISTENER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Configure parameters for the 'Opinions' search (type='o')
    params = {
        "q": query,
        "type": "o",               # Restrict to Opinions
        "order_by": "score desc",  # Relevance sorting
        "stat_Precedential": "on"  # Prefer precedential cases
    }
    
    if jurisdiction:
        params["court"] = jurisdiction
        print(f"[LEGAL SERVER] Jurisdiction filter: {jurisdiction}")
    if min_date:
        params["filed_after"] = min_date
        print(f"[LEGAL SERVER] Date filter: after {min_date}")

    print(f"[LEGAL SERVER] Making request to: {SEARCH_ENDPOINT}")
    print(f"[LEGAL SERVER] Parameters: {params}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(SEARCH_ENDPOINT, headers=headers, params=params)
            
            print(f"[LEGAL SERVER] Response status: {response.status_code}")
            
            # Handle Rate Limiting
            if response.status_code == 429:
                error_msg = "Error: CourtListener API rate limit exceeded. Please try again later."
                print(f"[LEGAL SERVER] {error_msg}")
                return error_msg
            
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            count = data.get("count", 0)
            
            print(f"[LEGAL SERVER] Total results found: {count}")
            print(f"[LEGAL SERVER] Results returned: {len(results)}")
            
            if not results:
                return f"No case law found for query: '{query}'."
            
            # Format the output for the LLM's consumption
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
                
                print(f"[LEGAL SERVER] Case {i}: {case_name}")
                
                entry = (
                    f"{i}. CASE: {case_name} ({citation})\n"
                    f"   COURT: {court} | DATE: {date_filed}\n"
                    f"   RELEVANCE: {clean_snippet[:500]}...\n"
                )
                formatted_cases.append(entry)
            
            result_text = "\n".join(formatted_cases)
            print(f"[LEGAL SERVER] Returning {len(formatted_cases)} formatted cases")
            return result_text

        except httpx.HTTPStatusError as e:
            error_msg = f"Legal API Error {e.response.status_code}: {e.response.text}"
            print(f"[LEGAL SERVER] {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Search execution failed: {str(e)}"
            print(f"[LEGAL SERVER] {error_msg}")
            return error_msg

if __name__ == "__main__":
    print("[LEGAL SERVER] Starting in stdio mode...")
    mcp.run(transport="stdio")