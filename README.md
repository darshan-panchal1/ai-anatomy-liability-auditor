# ANATOMY-LIABILITY-AUDITOR

An AI-powered liability analysis system that combines anatomical knowledge from Wikidata with legal precedents from CourtListener to assess medical malpractice and personal injury cases.

## Overview

Anatomy Liability Auditor uses an agentic architecture to automatically analyze medical liability scenarios. It extracts anatomical entities from case descriptions, maps them to medical ontologies, searches relevant legal precedents, and generates comprehensive liability assessments.

**Key Capabilities:**
- Automated extraction and validation of anatomical entities
- Graph-based reasoning about anatomical relationships
- Retrieval of relevant case law precedents
- Synthesis of medical and legal insights into actionable reports

## Architecture

- **Agent Framework**: LangGraph for multi-step reasoning workflows
- **LLM Provider**: Groq (ultra-low latency inference)
- **Tool Layer**: Model Context Protocol (MCP) servers
- **API Framework**: FastAPI
- **Knowledge Sources**: 
  - **Wikidata**: Anatomical ontology via SPARQL queries
  - **CourtListener**: Legal precedents from RECAP Archive

## Quick Start

### Prerequisites

- Python 3.8+
- API keys for Groq and CourtListener

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd anatomy_auditor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
COURTLISTENER_API_KEY=your_courtlistener_api_key_here
```

**Obtaining API Keys:**
- **Groq**: Sign up at [console.groq.com](https://console.groq.com)
- **CourtListener**: Register at [courtlistener.com/api](https://www.courtlistener.com/api/)

### Running the Application

Start the FastAPI server:

```bash
python -m app.main
```

Server runs at `http://localhost:8000`

Access the interactive API documentation at `http://localhost:8000/docs`

## Usage Examples

### Basic Liability Analysis

```bash
curl -X POST "http://localhost:8000/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "A patient suffered a femoral neck fracture during hip replacement surgery. Assess potential medical malpractice liability."
  }'
```

### Response Format

```json
{
  "anatomical_entities": ["femur", "hip joint"],
  "related_structures": ["acetabulum", "femoral head"],
  "legal_precedents": [...],
  "liability_assessment": "...",
  "confidence_score": 0.87
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

## How It Works

The system processes queries through a four-node graph:

1. **Anatomy Node**
   - Extracts anatomical terms from the case description
   - Maps entities to Wikidata identifiers (Q-IDs)
   - Retrieves related anatomical structures using graph relationships

2. **Strategy Node**
   - Analyzes anatomical context
   - Formulates targeted Boolean search queries
   - Identifies relevant legal theories (e.g., informed consent, standard of care)

3. **Legal Node**
   - Searches CourtListener's case database
   - Filters for jurisdiction and relevance
   - Extracts key holdings and reasoning

4. **Auditor Node**
   - Synthesizes medical and legal findings
   - Identifies liability risk factors
   - Generates structured assessment report

## Project Structure

```
anatomy_auditor/
├── app/
│   ├── main.py                 # FastAPI application and endpoints
│   ├── agent_graph.py          # LangGraph state machine definition
│   └── servers/
│       ├── anatomy_server.py   # Wikidata MCP server (SPARQL queries)
│       └── legal_server.py     # CourtListener MCP server (case search)
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not in version control)
└── README.md
```

## Testing Individual Components

Test MCP servers independently:

```bash
# Test anatomy knowledge retrieval
python app/servers/anatomy_server.py

# Test legal precedent search
python app/servers/legal_server.py
```

## Technical Details

### Performance Optimizations

- **Sub-second inference**: Groq's LPU architecture provides <1s LLM response times
- **Parallel tool calls**: MCP servers can be queried concurrently
- **Caching**: Repeated anatomical queries leverage Wikidata's CDN

### Knowledge Graph Integration

The system uses Wikidata's anatomical ontology with relationships like:
- `P361` (part of): Hierarchical anatomical relationships
- `P2789` (connects with): Anatomical connections for transitive liability analysis
- `P927` (anatomical location): Spatial relationships

### Agentic Design Benefits

- **Multi-turn reasoning**: LangGraph enables iterative refinement of queries
- **Self-correction**: Agents can backtrack if initial searches are unproductive
- **Explainability**: Full reasoning trace is preserved in the state graph

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `GROQ_API_KEY not found` | Verify `.env` file exists in project root with valid keys |
| `No anatomical entities found` | Try alternative medical terminology or check Wikidata coverage |
| `CourtListener rate limit exceeded` | Wait 60 seconds between requests or upgrade API tier |
| `Connection timeout` | Check network connectivity and API service status |

## Limitations

- **Jurisdictional scope**: CourtListener primarily covers US federal and state courts
- **Medical accuracy**: System provides preliminary analysis, not clinical diagnosis
- **Legal authority**: Generated reports are not legal advice; consult licensed attorneys

## Development Roadmap

- [ ] Multi-jurisdiction support (EU, UK, Canada)
- [ ] Integration with PubMed for medical literature
- [ ] Fine-tuned models for medical entity recognition
- [ ] Interactive web UI for case exploration

## Contributing

This is an educational/research project. For collaboration inquiries, please open an issue.

## License

Educational and Research Use Only. Not intended for clinical or legal decision-making without professional oversight.

## Acknowledgments

- **Wikidata** for comprehensive anatomical ontology
- **CourtListener/RECAP** for public legal data access
- **Groq** for high-performance inference infrastructure
```