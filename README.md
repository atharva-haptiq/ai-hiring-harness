# 🤖 AI Hiring Harness

> _Because sifting through 200 resumes by hand is a war crime against your time._

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-orange)](https://ollama.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎬 The Hook — What Even Is This?

Picture this: your inbox has **47 unread PDFs** from candidates, your hiring manager is pinging you every 20 minutes, and your coffee went cold an hour ago. You're drowning.

**AI Hiring Harness** is your escape hatch.

It's a full-stack AI-powered recruitment assistant that runs **entirely on your own machine** — no cloud, no API bills, no your-data-is-our-training-data. Drop in your job descriptions, upload a pile of resumes, and let a local LLM do the heavy lifting: ranking candidates, scoring fit, and even drafting outreach emails that don't sound like they were written by a 2009 mail-merge template.

You get a slick chat interface where you can just _talk_ to your hiring pipeline like a human being. Ask it things. It answers. While it's still thinking, you'll see the response stream in **word by word**, because staring at a blank screen for two minutes is not a vibe.

---

## ✨ Features — What This Beast Can Do

### 🧠 Conversational Copilot

Chat with your hiring data in plain English. No forms, no dropdowns, no three-click workflows.

```
"Rank candidates for the ML engineer job"
"Draft an outreach email for candidate 3"
"How many candidates do we have right now?"
```

### 📄 Resume Ingestion (PDF → Brain)

Upload one resume. Upload fifty. It doesn't care. Each PDF is parsed, text extracted, name and email inferred, and the candidate stored — ready to be ranked in seconds.

### 🏆 AI-Powered Candidate Ranking

Every candidate is evaluated against your job description across four dimensions:

- **Skills match** — do they actually know what you need?
- **Experience depth** — not just years, but _real_ depth
- **Seniority fit** — are they overqualified? Underqualified?
- **Domain relevance** — have they worked in your world before?

Each candidate gets a **0–100 score** with a plain-English explanation. No black boxes.

### ✉️ Outreach Email Generator

Point it at a candidate and a job. Get back a warm, personalised email that references _their actual background_. Not a template with `[CANDIDATE NAME]` still in it.

### 📊 Status Dashboard (via Chat)

Ask "show status" and get a live count of jobs, candidates, and scoring progress — right in the conversation.

### ⚡ Streams in Real Time

Responses stream **token by token** from Ollama straight to your browser. No more staring at a loading spinner for two minutes — you see the AI thinking, live.

### 🔒 Runs 100% Locally

Your resumes never leave your machine. No OpenAI. No Anthropic. No "your data helps improve our models." Just you, your CPU, and a local Ollama instance.

---

## 🛠️ Tech Stack — The Dream Team

| Layer             | Technology                                    |
| ----------------- | --------------------------------------------- |
| **Frontend**      | Next.js 15, TypeScript, Tailwind CSS          |
| **Backend**       | FastAPI, Python 3.11+, SQLAlchemy             |
| **Database**      | SQLite (zero config, just works)              |
| **LLM Runtime**   | [Ollama](https://ollama.com) — local, private |
| **Default Model** | `qwen2.5:7b` (swap to any Ollama model)       |
| **PDF Parsing**   | pdfplumber                                    |
| **HTTP Client**   | httpx (async, streaming-ready)                |

---

## 🚀 Getting Started — Let's Light This Candle

### Prerequisites

Before anything else, make sure you have:

- **Python 3.11+** — `python --version`
- **Node.js 18+** — `node --version`
- **[Ollama](https://ollama.com/download)** installed and running

### Step 1 — Pull the Model

Fire up Ollama and grab the model. Get a coffee, this is a one-time download (~4 GB):

```bash
ollama pull qwen2.5:7b
```

Verify it's alive:

```bash
ollama run qwen2.5:7b "Say hello"
```

> 💡 **Prefer speed over quality?** Swap to `qwen2.5:3b` or `gemma3:2b` — roughly 2× faster, modest quality drop. Change `_MODEL` in `backend/copilot/llm.py`.

### Step 2 — Backend

```bash
cd backend

# Create a virtual environment (don't skip this, you'll regret it)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy pdfplumber httpx python-multipart

# Boot the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now live at **http://localhost:8000**. Visit `/docs` for the interactive Swagger UI — it's genuinely useful.

### Step 3 — Frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

The app is now at **http://localhost:3000**. Go there.

---

## 🎮 Usage — How to Actually Use the Thing

### The Copilot (main attraction)

Head to **http://localhost:3000/copilot** and start typing.

| You say                                                          | It does                                             |
| ---------------------------------------------------------------- | --------------------------------------------------- |
| `"Create a job: Senior ML Engineer, must know PyTorch and CUDA"` | Creates the job posting                             |
| `"Rank candidates for job 1"`                                    | Scores every candidate 0–100 against that JD        |
| `"Draft outreach for candidate 2 for job 1"`                     | Writes a personalised email, streaming in real time |
| `"Show status"`                                                  | Gives you a live pipeline summary                   |

### Upload Resumes

Go to **http://localhost:3000/upload** and drag in your PDF stack. Multi-file supported. Each resume is parsed and stored as a candidate record.

### Create Jobs Manually

Go to **http://localhost:3000/create-job** to fill in a job title and description via form if you prefer that over the chat interface.

### View Results

Go to **http://localhost:3000/results** to see a ranked candidate table after scoring.

---

## ⏱️ Performance — Setting Expectations (CPU Reality Check)

Running a 7B parameter model on a CPU is like running a marathon in flip flops — it _works_, but manage your expectations.

| Operation                         | Time to first token | Total time         |
| --------------------------------- | ------------------- | ------------------ |
| Intent classification             | —                   | ~15–30 s           |
| Candidate ranking (per candidate) | —                   | ~60–90 s each      |
| Outreach email generation         | ~5–8 s              | ~60–90 s streaming |

> 🔥 **Want it faster?** Even a modest GPU (RTX 3060, 12 GB VRAM) drops total times to 2–5 seconds. The `keep_alive: -1` setting in `llm.py` ensures the model stays loaded in RAM between requests — eliminates the brutal 30–90 s cold-start penalty.

---

## 📁 Project Structure — Where Everything Lives

```
ai-hiring-harness/
├── backend/
│   ├── main.py               # FastAPI routes
│   ├── models.py             # SQLAlchemy ORM models
│   ├── db.py                 # Database session setup
│   ├── services.py           # Shared service helpers
│   └── copilot/
│       ├── llm.py            # Ollama async client (streaming + keep-alive)
│       ├── orchestrator.py   # Intent → tool dispatch + stream_copilot
│       ├── tools.py          # create_job, rank_candidates, generate_outreach
│       ├── prompts.py        # System prompts and prompt builders
│       └── memory.py         # Per-session chat history (sliding window)
│
└── frontend/
    ├── app/
    │   ├── copilot/page.tsx  # Chat interface (SSE streaming consumer)
    │   ├── upload/page.tsx   # Resume upload
    │   ├── create-job/       # Job creation form
    │   ├── results/page.tsx  # Ranked candidates table
    │   └── api/copilot/chat/ # Next.js SSE proxy route
    └── components/           # Reusable UI components
```

---

## 🤝 Contributing — Join the Chaos

Found a bug? Have a wild idea? Want to add support for a different model or a real database? Pull requests are very welcome.

```bash
# 1. Fork it
# 2. Create your feature branch
git checkout -b feature/my-wild-idea

# 3. Commit your changes
git commit -m "feat: add something brilliant"

# 4. Push and open a PR
git push origin feature/my-wild-idea
```

A few ideas if you're looking for somewhere to start:

- 🗄️ **PostgreSQL support** — swap SQLite for something production-grade
- 📧 **Real email sending** — pipe outreach emails directly to SendGrid/SES
- 🔍 **RAG for large resume sets** — vector search over hundreds of candidates
- 📊 **Analytics dashboard** — hiring funnel visualisation
- 🌐 **Multi-user support** — auth + per-recruiter sessions

> **Please** write tests. Future-you will send present-you a thank-you note.

---

## 📜 License

MIT — do whatever you want with it, just don't blame us if it accidentally hires your cat.

---

<div align="center">

**Built with ☕, frustration, and a deep hatred of manual resume screening.**

_If this saved you time, give it a ⭐ — it costs nothing and means everything._

</div>
