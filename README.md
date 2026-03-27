# ⚖️ Anatomy-of-Liability Auditor

> **Agentic AI system combining anatomical ontologies with US case law to produce structured medical malpractice liability assessments — in seconds.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-ai--anatomy--liability--auditor.netlify.app-4ade80?style=flat-square&logo=netlify&logoColor=white)](https://ai-anatomy-liability-auditor.netlify.app/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph-f97316?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-Educational%20%26%20Research-blue?style=flat-square)](#license)

---

## 🌐 Live Application

**[https://ai-anatomy-liability-auditor.netlify.app/](https://ai-anatomy-liability-auditor.netlify.app/)**

The UI is hosted on Netlify and connects to the FastAPI backend. No installation required to try the demo.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Pipeline](#pipeline)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Deployment](#deployment)
  - [Frontend — Netlify](#frontend--netlify)
  - [Backend — Any Cloud Provider](#backend--any-cloud-provider)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

**Anatomy-of-Liability Auditor** is a 4-node agentic AI pipeline that automates the preliminary analysis of medical malpractice and personal injury cases. It bridges the gap between clinical anatomy and legal research by:

- Extracting and resolving anatomical entities to Wikidata ontology identifiers
- Mapping structural relationships between affected anatomical regions
- Querying CourtListener's RECAP Archive for relevant US case law precedents
- Synthesising all findings into a structured liability assessment report

**Key capabilities:**

| Capability | Implementation |
|---|---|
| Anatomical entity extraction | Groq LLM (openai/gpt-oss-20b) + Wikidata SPARQL |
| Ontology resolution | Wikidata Q-IDs via `P361`, `P2789`, `P927` properties |
| Legal precedent retrieval | CourtListener REST API v4 (Opinions, Precedential) |
| Structured report synthesis | LLM-generated markdown with 6-section schema |
| Agent orchestration | LangGraph `StateGraph` with typed state |
| Sub-second LLM inference | Groq LPU architecture |

> ⚠️ **Disclaimer:** This system is for educational and research purposes only. Output is not legal advice. Consult a licensed attorney for any legal matter.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React UI (Netlify)                       │
│              https://ai-anatomy-liability-auditor.netlify.app   │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /audit
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                     │
│                    POST /audit  ·  GET /health                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LangGraph Agent (StateGraph)                   │
│                                                                 │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│   │ Anatomy  │──▶│ Strategy │──▶│  Legal   │──▶│ Auditor  │     │
│   │  Node    │   │  Node    │   │  Node    │   │  Node    │     │
│   └────┬─────┘   └──────────┘   └────┬─────┘   └──────────┘     │
│        │                             │                          │
│        ▼  Direct async call          ▼  Direct async call       │
│   ┌──────────┐                  ┌─────────────┐                 │
│   │ Wikidata │                  │CourtListener│                 │
│   │  Server  │                  │   Server    │                 │
│   └──────────┘                  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              Groq API (openai/gpt-oss-20b)
```

**Tech stack:**

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, vanilla CSS-in-JS |
| Backend | Python 3.8+, FastAPI, Uvicorn |
| Agent Framework | LangGraph, LangChain Core |
| LLM Provider | Groq (openai/gpt-oss-20b) |
| Knowledge Sources | Wikidata SPARQL, CourtListener REST API v4 |
| Frontend Hosting | Netlify |

---

## Pipeline

The system processes every query through a **4-node linear graph**:

### 1 — Anatomy Node
- Sends the case description to Groq to extract the primary anatomical term
- Resolves the term to a Wikidata Q-ID via SPARQL (`EntitySearch` + `P31/P279*` subclass filter)
- Retrieves structurally related entities using `P2789` (connects with) and `P361` (part of)

### 2 — Strategy Node
- Receives the resolved anatomical context
- Prompts Groq to construct a targeted CourtListener boolean search string
- Identifies applicable legal theories: negligence, informed consent, standard of care

### 3 — Legal Node
- Executes the boolean query against CourtListener's Opinions index (`type=o`, `stat_Precedential=on`)
- Returns the top 5 precedential cases with citation, court, date, and relevance snippet

### 4 — Auditor Node
- Synthesises anatomical context + case law into a structured 6-section markdown report:
  1. Executive Summary
  2. Anatomical Analysis
  3. Relevant Legal Precedents
  4. Liability Risk Assessment
  5. Recommended Legal Theories
  6. Disclaimer

---

## Project Structure

```
ai-anatomy-liability-auditor/
├── app/                          # FastAPI backend
│   ├── __init__.py
│   ├── main.py                   # API endpoints, middleware, lifespan
│   ├── agent_graph.py            # LangGraph state machine
│   └── tools.py                  # Wikidata + CourtListener async tools
├── ui/                           # React frontend (Vite)
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── AuditApp.jsx          # Main application component
│   │   ├── main.jsx              # React entry point
│   │   └── App.jsx               # Vite default (unused)
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── .env                      # VITE_API_BASE (local dev only)
├── netlify.toml                  # Netlify build configuration
├── requirements.txt              # Python dependencies
├── .env                          # Backend API keys (never commit)
├── .gitignore
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.8+
- Node.js 18+
- API keys for [Groq](https://console.groq.com) and [CourtListener](https://www.courtlistener.com/api/)

---

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/darshan-panchal1/ai-anatomy-liability-auditor.git
cd ai-anatomy-liability-auditor

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # or create .env manually
```

Add your keys to `.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
COURTLISTENER_API_KEY=your_courtlistener_api_key_here
```

```bash
# 5. Start the FastAPI server
python -m app.main
```

Backend runs at **http://localhost:8000**  
Interactive API docs at **http://localhost:8000/docs**

---

### Frontend Setup

```bash
# In a separate terminal, navigate to the UI directory
cd ui

# Install Node dependencies
npm install

# Configure the backend URL
echo "VITE_API_BASE=http://localhost:8000" > .env

# Start the development server
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Deployment

### Frontend — Netlify

The repository includes a `netlify.toml` at the root that fully automates the build configuration.

```toml
[build]
  base    = "ui"
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"
```

**Steps:**

1. Connect your GitHub repository on [netlify.com](https://netlify.com)
2. Leave all build fields **blank** in the Netlify UI — the `netlify.toml` handles everything
3. Add one environment variable in **Site settings → Environment variables**:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE` | Your deployed backend URL (no trailing slash) |

4. Deploy — Netlify will auto-deploy on every push to `main`

> **SPA routing:** A `_redirects` file (`/* /index.html 200`) inside `ui/public/` ensures React Router paths resolve correctly on Netlify.

---

### Backend — Any Cloud Provider

The FastAPI backend can be deployed to any platform that supports Python. Recommended options:

| Platform | Notes |
|---|---|
| [Railway](https://railway.app) | Zero-config, free tier available |
| [Render](https://render.com) | `python -m app.main` as start command |
| [Fly.io](https://fly.io) | Good for always-on low-latency |

Set the following environment variables on your chosen platform:

```
GROQ_API_KEY=...
COURTLISTENER_API_KEY=...
```

---

## API Reference

### `GET /health`

Returns API key configuration status.

```json
{
  "status": "operational",
  "version": "1.0.0",
  "groq_configured": true,
  "courtlistener_configured": true
}
```

---

### `POST /audit`

Runs a full 4-node liability analysis pipeline.

**Request body:**

```json
{
  "query": "A patient suffered a femoral nerve injury during a total hip replacement surgery...",
  "thread_id": "optional-uuid-for-tracing"
}
```

**Response:**

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "report": "## Executive Summary\n...",
  "duration_ms": 4823,
  "metadata": {
    "thread_id": "...",
    "anatomical_context_used": true,
    "legal_query": "femoral nerve AND negligence AND 'hip replacement'",
    "cases_cited": 4,
    "query_length_chars": 312
  }
}
```

**cURL example:**

```bash
curl -X POST "https://your-backend-url/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "A patient suffered a femoral neck fracture during hip replacement surgery. The surgeon did not discuss femoral nerve injury risk during informed consent. Assess potential medical malpractice liability."
  }'
```

---

## Usage Examples

The UI ships with four preloaded example cases accessible via the quick-select buttons:

| Scenario | Key Issue |
|---|---|
| **Hip replacement nerve injury** | Femoral nerve traction injury + informed consent gap |
| **Carpal tunnel surgery** | Median nerve laceration + absent pre-op NCS |
| **Lumbar discectomy** | Conus medullaris trauma + no intraoperative monitoring |
| **Laparoscopic cholecystectomy** | Common bile duct transection + absent cholangiogram |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `GROQ_API_KEY not found` | Missing `.env` file | Create `.env` in project root with valid keys |
| `ui/ui/dist does not exist` on Netlify | `publish` path double-prefixed | Ensure `netlify.toml` has `publish = "dist"` not `ui/dist` |
| Blank page on Netlify refresh | Missing SPA redirect rule | Add `_redirects` file to `ui/public/` |
| `No anatomical entities found` | Term not in Wikidata anatomy subclass | Try a more specific or alternative medical term |
| CourtListener 429 error | Rate limit hit | Wait 60s or upgrade API tier |
| CORS error in browser | Backend missing CORS header | Confirm `allow_origins=["*"]` in `main.py` middleware |

---

## Limitations

- **Jurisdictional scope:** CourtListener covers US federal and state courts only
- **Medical accuracy:** Anatomical extraction is probabilistic, not clinically validated
- **Legal authority:** Generated reports are preliminary analysis, not legal advice
- **Rate limits:** Free-tier Groq and CourtListener keys have per-minute request caps

---

## Roadmap

- [ ] Multi-jurisdiction support (EU, UK, Canada)
- [ ] PubMed integration for supporting medical literature
- [ ] Fine-tuned NER model for anatomical entity recognition
- [ ] Streaming response support (Server-Sent Events)
- [ ] PDF export of liability reports
- [ ] Authentication layer for multi-user deployments

---

## Contributing

This is an educational and research project. Issues and pull requests are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push and open a Pull Request

---

## Acknowledgments

- **[Wikidata](https://www.wikidata.org/)** — open anatomical ontology via SPARQL
- **[CourtListener / RECAP](https://www.courtlistener.com/)** — public US legal data
- **[Groq](https://groq.com/)** — high-throughput LPU inference
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — agent state machine framework

---

## License

**Educational and Research Use Only.**  
This project is not intended for clinical or legal decision-making without professional oversight. Output must not be used as a substitute for advice from a licensed attorney or medical professional.