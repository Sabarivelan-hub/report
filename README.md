# IntelliReport AI — Production Multi-Agent Report Generation & RAG Backend

A clean, modular, production-oriented backend for an AI-powered Report Generation Web Application built with **Python 3.11+**, **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL + pgvector**, **Alembic**, and **Google Gemini AI**.

---

## 🏛 High-Level Architecture

```
                               ┌─────────────────────────────────┐
                               │           Client / UI           │
                               └────────────────┬────────────────┘
                                                │ REST API
                                                ▼
                               ┌─────────────────────────────────┐
                               │       FastAPI Application       │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │   Agent Workflow Orchestrator   │
                               └────────────────┬────────────────┘
                                                │
         ┌───────────────────┬──────────────────┼──────────────────┬──────────────────┐
         │                   │                  │                  │                  │
         ▼                   ▼                  ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ ┌─────────────────┐ ┌────────────────┐
│     Agent 1     │ │     Agent 2     │ │    Agent 3    │ │     Agent 4     │ │    Agent 5     │
│ Input Analysis  │ │ Semantic Vector │ │ Report Plan   │ │ Report Synthesis│ │ Integrity QA & │
│ (Factual Extr.) │ │ Retrieval (RAG) │ │ Architecture  │ │ & Rich Content  │ │ Validation     │
└────────┬────────┘ └────────┬────────┘ └───────┬───────┘ └────────┬────────┘ └───────┬────────┘
         │                   │                  │                  │                  │
         │                   ▼                  │                  │                  │
         │         ┌──────────────────┐         │                  │                  │
         │         │ PostgreSQL RAG   │         │                  │                  │
         │         │ + pgvector HNSW  │         │                  │                  │
         │         └──────────────────┘         │                  │                  │
         │                                      │                  │                  │
         └──────────────────────────────────────┴──────────────────┴──────────────────┘
                                                │
                          Validation Failed? ───┴───► Regenerate (Max 2 Attempts)
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │          Final Report           │
                               │   (PDF / DOCX / JSON Export)    │
                               └─────────────────────────────────┘
```

---

## 🤖 5-Stage Multi-Agent Workflow

| Agent | Responsibility | Key Rules & Mechanism |
|---|---|---|
| **1. Input Analysis Agent** | Parse raw user prompt into typed parameters (`report_type`, `company`, `date`, `student_count`, `department`, `topics`) | Extract **only** information supported by user. **No hallucinations**. Flag missing mandatory fields. |
| **2. Retrieval Agent** | Synthesize search query, compute embeddings with Gemini `text-embedding-004`, query pgvector | Vector cosine distance `<=>` search. Default `top_k=5`. Completely independent repository layer. |
| **3. Report Planner Agent** | Formulate exhaustive structural outline with section purposes and requirements | Adheres strictly to configured `report_templates` when provided; incorporates domain guidance from references. |
| **4. Report Generator Agent** | Generate rich Markdown report sections, takeaways, and executive summary | Ground-truth facts derived from user input; tone, domain knowledge, and structure guided by retrieved chunks. |
| **5. Validation Agent** | Audit factual integrity, mandatory sections presence, absence of hallucinations, and technical depth | Computes quality score; on critical failure, triggers regeneration loop (max 2 attempts). Attaches warnings if unresolved. |

---

## 🗄 Database Design (PostgreSQL + pgvector)

7 production tables managed via SQLAlchemy 2.0 and Alembic:

1. **`users`**: User identity, email, created_at.
2. **`report_templates`**: Standardized blueprint schemas (`template_structure` JSONB, `report_type`).
3. **`reference_documents`**: Ingested reference reports (`title`, `file_name`, `file_path`, `document_type`, `metadata` JSONB).
4. **`document_chunks`**: Overlapping document segments with `embedding Vector(768)` and HNSW cosine distance index (`idx_document_chunks_embedding_hnsw`).
5. **`generated_reports`**: Master report records (`report_type`, `input_data` JSONB, `final_content` JSONB, `status`).
6. **`report_versions`**: Iterative drafts saved across regeneration attempts (`version_number`, `content`, `validation_result`).
7. **`generation_logs`**: Step-by-step audit logs tracking `agent_name`, `input_data`, `output_data`, `execution_time`, and `status`.

---

## 📂 Project Structure

```
├── alembic/                      # Database migrations
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py # Initial schema with pgvector HNSW index
├── app/
│   ├── agents/                   # Gemini AI Agents
│   │   ├── base.py               # BaseAgent with execution telemetry
│   │   ├── input_analyzer.py     # Agent 1
│   │   ├── retrieval_agent.py    # Agent 2
│   │   ├── report_planner.py     # Agent 3
│   │   ├── report_generator.py   # Agent 4
│   │   └── validator.py          # Agent 5
│   ├── api/                      # FastAPI Endpoints
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── documents.py      # /api/v1/documents (Ingestion, inspection)
│   │       ├── templates.py      # /api/v1/templates (Template CRUD)
│   │       └── reports.py        # /api/v1/reports (Workflow, logs, versions, export)
│   ├── core/
│   │   └── config.py             # Pydantic Settings
│   ├── db/
│   │   ├── database.py           # Engine & async sessionmaker
│   │   └── models.py             # 7 SQLAlchemy models + pgvector
│   ├── orchestrator/
│   │   └── orchestrator.py       # OrchestrationPipeline & retry loop
│   ├── rag/
│   │   ├── chunker.py            # Recursive overlapping text chunker
│   │   ├── document_loader.py    # PyMuPDF (PDF) & python-docx (DOCX)
│   │   ├── embeddings.py         # Gemini text-embedding-004
│   │   └── retriever.py          # VectorRetrieverRepository (pgvector)
│   ├── schemas/                  # Pydantic validation schemas
│   ├── services/
│   │   ├── document_service.py   # Ingestion pipeline
│   │   └── export_service.py     # PDF, DOCX, JSON exports
│   └── main.py                   # FastAPI app entry point
├── docker-compose.yml            # Multi-container setup (PostgreSQL + pgvector + FastAPI)
├── Dockerfile                    # Containerization with PyMuPDF & C-libraries
└── requirements.txt
```

---

## 🚀 Quickstart & Setup

### 1. Environment Variables
Create `.env`:
```bash
GEMINI_API_KEY="your-google-gemini-api-key"
DATABASE_URL="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/intellireport"
SYNC_DATABASE_URL="postgresql+psycopg2://postgres:postgrespassword@localhost:5432/intellireport"
```

### 2. Run with Docker Compose
```bash
docker-compose up --build
```
This automatically starts:
- PostgreSQL 16 with pgvector on port `5432`
- Runs Alembic migrations (`alembic upgrade head`)
- Launches FastAPI on `http://localhost:8000` with Swagger docs at `http://localhost:8000/api/v1/docs`
