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
- [Enviroment Variables](#environment-variables)
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
- **Free & Paid Plans** — billing integration with plan-based model selection, paid via **eSewa**, **Khalti**, and Stripe

---

## Local Development

### Prerequisites

| Requirement | Version | Link |
|---|---|---|
| Python | 3.10+ | [python.org](https://python.org/downloads) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Git | Any recent | [git-scm.com](https://git-scm.com) |

---

### Step1: Clone/Download the Repository:

```bash
git clone <repo_url>
```
---

### Step2: Get into the "Noya/" folder, open it in an IDE.

---

### Step3: Run the Automated Script:
```bash
python setup.py
```
### Add all valid inputs the script asks, and you are ready to go!

---

### Open the App

Go to **http://localhost:5173**, register an account, select a subject, and start studying. 

---

## Environment Variables

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
| `FRONTEND_URL` | No | Frontend origin gateways redirect back to (default: `http://localhost:5173`) |
| `ESEWA_MODE` | No | `sandbox` (default, public UAT keys) or `production` |
| `ESEWA_PRODUCT_CODE` | No | eSewa merchant code (defaults to `EPAYTEST` in sandbox) |
| `ESEWA_SECRET_KEY` | No | eSewa HMAC secret (defaults to the public UAT secret in sandbox) |
| `KHALTI_MODE` | No | `sandbox` (default) or `production` |
| `KHALTI_PUBLIC_KEY` | No | Khalti public key (required to enable Khalti checkout) |
| `KHALTI_SECRET_KEY` | No | Khalti secret key (required to enable Khalti checkout) |

### Frontend Variables

Create `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Frontend** | React 18, Vite 5, React Router 6, Tailwind CSS 3, KaTeX (LaTeX math) |
| **Backend** | Django 4.2+, Django REST Framework |
| **Authentication** | SimpleJWT (access / refresh tokens with blacklisting) |
| **Database** | PostgreSQL (Supabase) |
| **Vector Store** | Qdrant Cloud |
| **Embedding Model** | paraphrase-multilingual-MiniLM-L12-v2 |
| **LLM Providers** | Gemini (primary), DeepSeek (fallback), Kira AI (backup), Groq (titles/classification) |
| **Caching** | Custom Built Semantic Cache System |

---

<p align="center">
  <strong>Developed, Designed, and Created by Sabal Bajagain</strong>
</p>
