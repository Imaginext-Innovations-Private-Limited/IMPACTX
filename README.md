# IMPACTX
The Industry Driven Hackathon | Dayananda Sagar University | Imaginext &amp; Wise  Work

# 🎓 Socratic AI Tutor Agent

> **An adaptive, RAG-powered learning platform that guides students through guided inquiry, active recall, and dynamic difficulty calibration rather than giving away direct answers.**

---

## 📖 Table of Contents
- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project File Structure](#-project-file-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Running the Project](#-running-the-project)
- [Usage Guide](#-usage-guide)
- [Troubleshooting & Windows Fixes](#-troubleshooting--windows-fixes)
- [API Reference](#-api-reference)

---

## 🌟 Overview

The **Socratic AI Tutor** shifts AI education from passive lookup to **active critical reasoning**. Instead of generating ready-made answers, the system acts as a personalized Socrates:
1. It retrieves authoritative curriculum chunks from user-uploaded textbook PDFs using **Retrieval-Augmented Generation (RAG)**.
2. It generates probing, progressive guiding questions using a locally hosted **Ollama LLM (Qwen2.5)**.
3. It assesses student responses, adjusts difficulty dynamically, and persists learning metrics to **SQLite**.
4. It provides teachers with a real-time cohort analytics dashboard in **Streamlit** to spot class-wide misconceptions.

---

## ⚡ Key Features

- **Strict Socratic Guardrails:** Zero answer leakage. The tutor scaffolds learning through analogies, clues, and progressive questioning.
- **RAG Knowledge Ingestion:** Upload any domain textbook or syllabus PDF (e.g., Computer Networks, Cloud, AI) for grounded domain accuracy.
- **Adaptive Mastery Tracking:** Calibrates question difficulty (Novice → Intermediate → Advanced) and tracks concept scores (0–100%).
- **Teacher Cohort Oversight:** Class-level heatmaps, struggle alerts, and concept mastery distributions.
- **100% Local & Private LLM Inference:** Runs locally via Ollama with no external API keys or cloud data exposure.

---

## 🏗 System Architecture

The application is engineered across three interconnected phases:

```
[ Phase 1: Knowledge Ingestion & RAG ]
Textbook PDF ──> PyMuPDF Text Extraction ──> 500-Token Chunking ──> Sentence Transformers ──> FAISS IndexFlatL2
                                                                                                    │
[ Phase 2: Adaptive Socratic Dialogue ]                                                             ▼
Student Query ───────────────────────────────────────────> Top-3 Vector Retrieval ──> Prompt Assembly
                                                                                             │
Student Response <── Socratic Guiding Question <── Qwen2.5 Local Engine (Ollama) <────────────┘
      │
      ▼
[ Phase 3: Adaptive Calibration & Analytics ]
Response Evaluator ──> Score Delta (+15%) ──> Dynamic Difficulty ──> SQLite DB ──> Teacher Dashboard (Plotly)
```

1. **Phase 1: Knowledge Ingestion (Offline/On-Demand Pipeline)**
   - PyMuPDF extracts text and tabular content.
   - Recursive chunking splits text into 500-token blocks with 100-token overlap.
   - `sentence-transformers/all-MiniLM-L6-v2` produces dense 384-dimensional embeddings stored in a local `FAISS` index (`IndexFlatL2`).

2. **Phase 2: Adaptive Socratic Dialogue Engine (Real-Time Interaction)**
   - Top-3 relevant context chunks are retrieved based on student query similarity.
   - Context is injected into a Socratic system prompt with zero-leak guardrails.
   - Local Ollama (`qwen2.5:1.5b` or `qwen2.5:7b`) evaluates reasoning and poses the next progressive inquiry with optional hints.

3. **Phase 3: Adaptive Analytics & Teacher Oversight (Persistence Layer)**
   - Student attempts, responses, and score deltas (+15% to +20%) are recorded in `data/tutor.db` via SQLite.
   - Streamlit renders real-time class mastery distributions and flags common misconceptions.

---

## 🛠 Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Student interactive chat portal & Teacher analytics dashboard |
| **Backend API** | FastAPI + Uvicorn | Asynchronous REST API routing, RAG pipeline, and session coordination |
| **Document Parser** | PyMuPDF (`fitz`) | High-speed PDF text extraction and normalization |
| **Embeddings** | Sentence Transformers | Local `all-MiniLM-L6-v2` dense vector generation (384-d) |
| **Vector Database** | FAISS (`faiss-cpu`) | High-performance L2 similarity search (`IndexFlatL2`) |
| **Local LLM** | Ollama (`qwen2.5:1.5b`) | Offline, privacy-preserving Socratic dialogue reasoning |
| **Database** | SQLite3 | ACID-compliant persistence for student attempts, scores, and logs |
| **Data Visualization** | Plotly & Streamlit Charts | Real-time mastery progress bars and class concept distribution |

---

## 📁 Project File Structure

```text
socratic-tutor/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application endpoints & lifespan
│   ├── socratic_engine.py       # Ollama prompt assembly, scoring, & next-question logic
│   ├── rag_indexer.py           # PyMuPDF parser, chunker, & FAISS vector storage
│   └── database.py              # SQLite schemas, tables, and progress queries
├── frontend/
│   └── app.py                   # Streamlit multi-tab UI (Chat, Progress, Teacher View)
├── data/
│   ├── uploads/                 # Uploaded curriculum PDFs
│   ├── faiss_index/             # FAISS index and chunk metadata files
│   └── tutor.db                 # SQLite database file
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 📋 Prerequisites

1. **Python 3.10 to 3.12** installed on your system.
2. **Ollama for Windows/macOS/Linux** installed:
   - Download from [ollama.com](https://ollama.com).
   - Verify in terminal:
     ```bash
     ollama --version
     ```
3. **Pull the Qwen Model:**
   ```bash
   ollama pull qwen2.5:1.5b
   ```
   *(Note: `qwen2.5:1.5b` offers fast CPU inference on laptops. If you have an NVIDIA GPU, you can run `ollama pull qwen2.5`.)*

---

## 🚀 Installation & Setup

### 1. Clone or Open Project
```powershell
cd C:\Users\<YourUser>\socratic-tutor
```

### 2. Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate in PowerShell (Windows)
.\.venv\Scripts\Activate.ps1
```
*(If script execution is blocked on Windows, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### 3. Install Dependencies
Ensure your `requirements.txt` contains:
```text
fastapi>=0.110.0
uvicorn>=0.28.0
streamlit>=1.32.0
requests>=2.31.0
pydantic>=2.6.0
pymupdf>=1.23.0
sentence-transformers>=2.5.0
faiss-cpu>=1.8.0
python-multipart>=0.0.9
```
Install with:
```powershell
pip install -r requirements.txt
```

---

## 💻 Running the Project

You will need **two terminal windows** (both inside `.venv`):

### Terminal 1: Start FastAPI Backend
```powershell
uvicorn backend.main:app --reload --port 8000
```
- API will be active at: `http://127.0.0.1:8000`
- Interactive Swagger documentation: `http://127.0.0.1:8000/docs`

### Terminal 2: Start Streamlit Frontend
```powershell
streamlit run frontend/app.py --server.port 8501
```
- Student & Teacher Portal opens automatically at: `http://localhost:8501`

---

## 🎯 Usage Guide

1. **Upload Textbook (Sidebar):**
   - Click **Browse files** and select your curriculum PDF (e.g., OSI model or Cloud Computing).
   - Click **📥 Index Textbook** to generate FAISS embeddings.
2. **Configure Profile:**
   - Enter your name (e.g., `Reehan`).
   - Select a topic preset (e.g., *OSI Model & 7 Network Layers*) or enter a custom topic.
   - Choose your starting difficulty level.
3. **Start Socratic Session:**
   - Click **🚀 Begin Socratic Session**.
   - Read the opening question, reason through the concept, and submit your explanation.
   - If stuck, open the **💡 Need a hint** expander.
   - Notice your mastery score increasing as your explanations demonstrate comprehension!
4. **Teacher View:**
   - Switch to the **📊 Teacher & Class Analytics** tab to inspect cohort progress, mastery bars, and common flagged misconceptions.

---

## 🔧 Troubleshooting & Windows Fixes

| Issue / Error | Root Cause | Verified Solution |
| :--- | :--- | :--- |
| `[WinError 183] Cannot create a file when that file already exists` | `data\uploads` or `data\faiss_index` was created as an empty file instead of a folder. | Delete the file and create the directory: `Remove-Item data\uploads -Force; New-Item -ItemType Directory -Path data\uploads` |
| `Ollama connection timed out (60s)` | Qwen 7B running on CPU exceeded the default 60s timeout. | 1. Switch to `qwen2.5:1.5b` in `backend/socratic_engine.py`<br>2. Set `timeout=180` in requests calls. |
| `sqlite3.DatabaseError: file is not a database` | `data/tutor.db` was touched as an empty raw text file. | Remove `data/tutor.db` and restart Uvicorn so `init_db()` auto-creates tables. |
| `JSONDecodeError: Expecting value line 1 column 1` | Frontend attempted `.json()` on a 500 error page. | Wrapped backend call in `res.status_code == 200` checks with regex JSON parser fallback. |

---

## 📡 API Reference

- `POST /api/documents/upload`: Uploads and chunks a PDF, generates vectors, and saves to FAISS.
- `POST /api/tutor/interact`: Accepts `{ student_id, topic, student_message, chat_history, difficulty }`, runs RAG search, queries Qwen2.5, logs attempt, and returns feedback + next question.
- `GET /api/progress/{student_id}`: Retrieves student mastery history across concepts from SQLite.
- `GET /api/teacher/analytics`: Returns aggregated cohort statistics, average mastery scores, and struggle alerts.

---

## 📄 License
This project is licensed under the MIT License — open for academic, instructional, and research applications.
