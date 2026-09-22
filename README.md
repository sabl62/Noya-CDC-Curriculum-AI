<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="frontend/src/assets/noya-logo.svg">
    <img src="frontend/src/assets/noya-logo.svg" width="200" height="200" alt="Noya">
  </picture>
</p>

<h1 align="center">Noya</h1>

<p align="center">
  <img src="https://img.shields.io/badge/React-18-blue?logo=react" alt="React 18">
  <img src="https://img.shields.io/badge/Django-4.2-green?logo=django" alt="Django 4.2">
  <img src="https://img.shields.io/badge/Gemini-2.5_Flash-orange?logo=google" alt="Gemini 2.5 Flash">
  <img src="https://img.shields.io/badge/PostgreSQL-Supabase-336791?logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
</p>

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Local Development](#local-development)
- [Enviroment Variables](#enviroment-variables)
- [Tech Stack](#tech-stack)
- [File Structure](#file-structure)

---

## About

Noya is a **Retrieval-Augmented Generation (RAG)** system built for **Grade 10 students** following Nepal's **CDC (Curriculum Development Centre) national curriculum**.

In Simple Language, **Noya is an AI for grade 10 books**. It is built for Nepali students of grade 10 to help them with their assignments, studies and more. 

---

## Features

- **Textbook Related AI Chat** — Answers come directly from CDC Textbooks (Janak Sikshya Samagri)
- **Subject & Chapter Selection** — Science, Mathematics, Optional Mathematics, English (Social Studies & Nepali coming soon)
- **4-Tier Semantic Cache** — Built as Noya's own brain, Check The docs folder.
- **JWT Authentication** — Secure Authentication System with token rotation.
- **Dark / Light Theme** — Clean, minimal design with Light and Dark themes.
- **Markdown + LaTeX Rendering** — LaTeX Math Support, Same mathematical Symbols as your textbook.
- **Chat Sessions** — Create, continue, and delete conversation histories
- **Free & Paid Plans** — billing integration with plan-based model selection

---

## Local Development

### Prerequisites

| Requirement | Version | Link |
|---|---|---|
| Python | 3.10+ | [python.org](https://python.org/downloads) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | Any recent | [git-scm.com](https://git-scm.com) |

---

### 1. Clone the Repository

```bash
git clone <repo-url>
cd Noya
```
---

### 2. Configure Environment Variables

Copy the example env file into `backend-main/`:

<details open>
<summary><strong>macOS / Linux</strong></summary>

```bash
cp .env.example backend-main/.env
```
</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
Copy-Item .env.example backend-main\.env
```
</details>

<details>
<summary><strong>Windows (Command Prompt)</strong></summary>

```cmd
copy .env.example backend-main\.env
```
</details>

> **You must manually edit `backend-main/.env`** with your own keys before continuing.

**Required:**
| Variable | Description |
|---|---|
| `SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY_1` | From [Google AI Studio](https://aistudio.google.com/apikey) |
| `QDRANT_URL` + `QDRANT_API_KEY` | From [Qdrant Cloud](https://cloud.qdrant.io) |
| `DATABASE_URL` | PostgreSQL connection string (Supabase, Neon, or local). Leave empty for SQLite. |

**Optional (for full functionality):**
| Variable | Purpose |
|---|---|
| `DEEPSEEK_API_KEY_1` | Fallback LLM provider ([DeepSeek](https://platform.deepseek.com)) |
| `GROQ_API_KEY_1` | Title generation & question classification ([Groq](https://console.groq.com)) |
| `KIRAA_API_KEY_1` | Backup LLM provider ([Kira AI](https://kiraai.vn)) |

---

### 3. Backend Setup

```bash
cd backend-main
python -m venv venv
```

**Activate the virtual environment** (pick the one for your shell):

<details open>
<summary><strong>macOS / Linux / Git Bash</strong></summary>

```bash
source venv/bin/activate
```
</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
.\venv\Scripts\Activate.ps1
```
</details>

<details>
<summary><strong>Windows (Command Prompt)</strong></summary>

```cmd
venv\Scripts\activate.bat
```
</details>

Then install dependencies, run migrations, and initialize the RAG pipeline:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py initialize_rag
python manage.py runserver
```

> Use `python manage.py initialize_rag --force-rebuild` to re-chunk and re-index

Backend runs at **http://localhost:8000**

---

### 4. Frontend Setup

Open a **new terminal** (keep the backend running in the first one):

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

### 5. Open the App

Go to **http://localhost:5173**, register an account, select a subject, and start studying. 

---

## Environment Variables

Copy `.env.example` to `backend-main/.env` (see Step 2 above) and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Django secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | No | PostgreSQL URL. Falls back to SQLite if empty |
| `GEMINI_API_KEY_1` | Yes | Google Gemini API key ([get one here](https://aistudio.google.com/apikey)) |
| `QDRANT_URL` | Yes | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Yes | Qdrant Cloud API key |
| `DEEPSEEK_API_KEY_1` | No | DeepSeek API key (fallback LLM provider) |
| `KIRAA_API_KEY_1` | No | Kira AI API key (backup LLM provider) |
| `GROQ_API_KEY_1` | No | Groq API key (title generation + question classification) |
| `DEBUG` | No | Set to `true` for development (default: `false`) |
| `ALLOWED_HOSTS` | No | Comma-separated list of allowed hosts (default: `localhost,127.0.0.1`) |
| `CORS_ALLOWED_ORIGINS` | No | Comma-separated CORS origins (default: `http://localhost:5173`) |

### Frontend Variables

Create `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

Firebase variables are legacy and not required for local development.

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Frontend** | React 18, Vite 5, React Router 6, Tailwind CSS 3, KaTeX (LaTeX math) |
| **Backend** | Django 4.2+, Django REST Framework |
| **Authentication** | SimpleJWT (access / refresh tokens with blacklisting) |
| **Database** | PostgreSQL (Supabase) |
| **Vector Store** | Qdrant Cloud |
| **Embedding Model** | `paraphrase-multilingual-MiniLM-L12-v2` (Sentence Transformers) |
| **LLM Providers** | Gemini (primary), DeepSeek (fallback), Kira AI (backup), Groq (titles/classification) |
| **Caching** | Custom Built Semantic Cache System |

---

## File Structure

```
Noya/
│
├── frontend/                          # React + Vite SPA
│   ├── public/
│   ├── src/
│   │   ├── assets/                    # Logo, favicon
│   │   ├── components/
│   │   │   ├── ChatView.jsx           # Main chat (SSE streaming, sessions)
│   │   │   ├── SubjectSelection.jsx   # Grid of subjects + chapters
│   │   │   ├── Login.jsx              # JWT login form
│   │   │   ├── SignUp.jsx             # Registration with referral
│   │   │   ├── MarkdownRenderer.jsx   # KaTeX LaTeX, code blocks, tooltips
│   │   │   └── FormField.jsx          # Reusable input component
│   │   ├── context/AuthContext.jsx    # React Context for JWT auth state
│   │   ├── data/curriculum.js         # CDC subject + chapter definitions
│   │   ├── services/api.js            # Axios client with JWT interceptor
│   │   ├── firebase/                  # Firebase config (legacy)
│   │   ├── styles/                    # Design token CSS
│   │   ├── tokens.css                 # CSS custom properties
│   │   ├── index.css                  # Global styles + Tailwind
│   │   ├── App.jsx                    # Router + AuthProvider
│   │   └── main.jsx                   # Vite entry point
│   ├── package.json
│   └── vite.config.js
│
├── backend-main/                      # Django REST API
│   ├── backend/
│   │   └── settings.py                # Django config (DB, JWT, CORS, cache)
│   ├── api/
│   │   ├── ai_service.py              # LLM orchestration (Gemini/DeepSeek/Kira)
│   │   ├── rag_service.py             # Qdrant vector search + PDF ingestion
│   │   ├── semantic_cache.py          # 4-tier semantic caching system
│   │   ├── chapter_pdf_context.py     # Page-range maps per subject/chapter
│   │   ├── curriculum_scope.py        # Subject detection + out-of-scope handling
│   │   ├── content_processor.py       # AI-powered textbook transformation
│   │   ├── models.py                  # User, ChatSession, ChatMessage, Cache
│   │   ├── serializers.py             # DRF serializers
│   │   ├── views.py                   # All API endpoints
│   │   ├── urls.py                    # Route definitions
│   │   ├── admin.py                   # Django admin configuration
│   │   └── apps.py                    # App config + RAG warmup
│   ├── cdc_curriculum/                # CDC textbook PDFs (class_10/)
│   ├── manage.py                      # Django management script
│   └── requirements.txt               # Python dependencies
│
├── .env.example                       # Environment variable template
└── README.md and other docs           # Project Description
```
---

<p align="center">
  <strong>Developed, Designed, and Created by Sabal Bajagain</strong>
</p>