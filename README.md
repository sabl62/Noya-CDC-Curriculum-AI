# Noya

Noya is a Grade 10 study chat application for Nepal's CDC curriculum. The web client is built with React and Vite; the API and application data are handled by Django REST Framework.

The repository contains curriculum lookup code, but this checkout does **not** contain the `backend-main/api/cdc_curriculum/` PDF directory. Textbook-grounded responses therefore require you to provide the relevant PDFs and configure Qdrant. Without those resources, the app can start, but its curriculum retrieval features are not ready to use.

## What is implemented

- The subject picker currently exposes Science, Mathematics, Optional Mathematics, and English.
- The chat endpoint streams status and answer events using Server-Sent Events (SSE). Guests can chat; saved sessions and history require an account.
- Chat routing checks the database-backed answer cache and knowledge base, then uses selected-chapter PDF context or Qdrant retrieval when available, before requesting a live model answer.
- Live answer providers are DeepSeek, Kira, and Gemini, in a question-dependent fallback order. Groq is used for title generation and question classification.
- The semantic cache uses a process-local LRU plus database-backed semantic answers and precomputed knowledge entries.
- JWT authentication, light/dark themes, Markdown/KaTeX rendering, and chat history are present in the code.
- Daily and monthly chat limits are enforced by the backend. Optional Pro and payment routes are included only when the optional billing modules are present and load successfully.

These features depend on external credentials, database records, and curriculum files as described below. Their presence in the code does not mean the external services or content are configured in a deployment.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer and npm
- A Gemini key for the setup script and a configured live answer provider
- Qdrant and the curriculum PDFs if you want to use PDF indexing and Qdrant retrieval

## Local development

The backend reads environment variables from `backend-main/.env`. Start from the example at the repository root:

```bash
copy .env.example backend-main/.env
```

On macOS or Linux, use `cp .env.example backend-main/.env` instead. Edit the new file and set the values needed for your setup. Do not commit secrets.

Install and start Django:

```bash
cd backend-main
python -m venv venv
```

Activate the environment (`venv\Scripts\activate` on Windows, or `source venv/bin/activate` on macOS/Linux), then run:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In a second terminal, start the web client:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The API client defaults to `http://localhost:8000/api`. If your backend uses another host or port, set `VITE_API_URL` in `frontend/.env` (for example, `http://localhost:8000`).

### Automated setup script

`python setup.py` is an optional interactive installer. It prompts for Gemini and DeepSeek keys, a database choice, and Qdrant credentials; creates `backend-main/venv`; installs both dependency sets; runs migrations and `initialize_rag`; then starts the backend and Vite in separate terminals. The script requires the prompted keys even though the application can use provider fallbacks. The RAG command also needs reachable Qdrant and local PDFs; without them, indexing reports an error and the script continues to server startup. Use the manual steps above if you do not have those resources or want to configure only some providers.

## Textbook PDFs and RAG

The expected PDF directory is `backend-main/api/cdc_curriculum/`. The chapter reader looks for subject-named PDFs such as `science.pdf`, `math.pdf`, `omaths.pdf`, and `english.pdf`, either directly in that directory or under `class_10/`. RAG indexing scans that directory recursively. Place only curriculum content you are permitted to use there; the PDFs are not included in this repository.

Configure `QDRANT_URL` and, for a protected Qdrant instance, `QDRANT_API_KEY` in `backend-main/.env`. Install the backend requirements, make sure the PDFs are present, then run:

```bash
cd backend-main
python manage.py initialize_rag
```

Use `python manage.py initialize_rag --status` to inspect the current index or `python manage.py initialize_rag --force-rebuild` to replace it. Rebuilding deletes and recreates the `cdc_curriculum` collection before indexing.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing key. Set a private value for any shared or deployed environment. |
| `DEBUG` | Django debug setting; defaults to `false`. |
| `ALLOWED_HOSTS` | Comma-separated backend hostnames. |
| `DATABASE_URL` | Optional PostgreSQL URL. If unset, Django uses `backend-main/db.sqlite3`. Configured PostgreSQL URLs are set to require SSL. |
| `GEMINI_API_KEY`, `GEMINI_API_KEY_1` … `GEMINI_API_KEY_5` | Gemini credentials. The service reads either the comma-separated `GEMINI_API_KEYS` variable or the numbered/single-key forms. |
| `DEEPSEEK_API_KEY`, `DEEPSEEK_API_KEY_1` … `DEEPSEEK_API_KEY_5` | Optional DeepSeek credentials for live answers. `DEEPSEEK_ENDPOINT` can override its API endpoint. |
| `KIRA_API_KEY`, `KIRA_API_KEY_1` … `KIRA_API_KEY_5` | Optional Kira credentials for live-answer fallback. |
| `GROQ_API_KEY`, `GROQ_API_KEY_1` … `GROQ_API_KEY_5` | Groq credentials for title generation and question classification. |
| `GROQ_MODEL` | Optional title-generation model override; the service has a Groq-only model fallback chain. |
| `QDRANT_URL`, `QDRANT_API_KEY` | Qdrant connection for RAG. The API key is optional for a local unauthenticated Qdrant instance. |
| `TRUSTED_PROXY_IPS` | Comma-separated IPs/CIDRs allowed to supply `X-Forwarded-For`; leave blank unless the backend is behind a proxy you control. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed by Django. |
| `FRONTEND_URL` | Frontend origin used for referral links and payment returns. |
| `USAGE_FREE_DAILY_LIMIT`, `USAGE_FREE_MONTHLY_LIMIT`, `USAGE_PAID_DAILY_LIMIT`, `USAGE_PAID_MONTHLY_LIMIT`, `USAGE_RATE_LIMIT_PER_MINUTE` | Optional server-side quota overrides. Defaults are 15/300 chats for Free, 150/1,000 for Pro, and 5 requests per minute. See `backend-main/api/usage_limits.py`. |
| `ESEWA_*`, `KHALTI_*`, `STRIPE_*` | Optional payment configuration. Billing is available only when its optional code is present and enabled. |

The setup script writes the provider and database values it collects to `backend-main/.env`; it does not create a `frontend/.env` file.

## Project map

```text
backend-main/
  backend/                 Django project settings and URL configuration
  api/                     API views, models, chat, RAG, cache, and billing code
  api/management/commands/ Django management commands
  requirements.txt         Python dependencies
frontend/
  src/                     React application, components, and API client
  package.json             Vite scripts and JavaScript dependencies
docs/                      Architecture, RAG, cache, and API notes
setup.py                   Optional interactive local setup script
```

## Documentation

- [Architecture](docs/Architecture.md)
- [RAG pipeline](docs/RAG_PIPELINE.md)
- [Cache implementation](docs/cache_architecture.md)
- [API endpoints](docs/API_EndPoints.md)

