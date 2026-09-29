## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Create account (username, email, password, referral) |
| POST | `/api/auth/login/` | Obtain JWT tokens |
| POST | `/api/auth/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| GET | `/api/auth/user/` | Get current user profile |
| PATCH | `/api/auth/user/` | Update profile (grade, school, bio) |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send message (SSE streaming response) |
| GET | `/api/chat/sessions/` | List chat sessions |
| GET | `/api/chat/sessions/:id/` | Load session with full message history |

Chat usage limits: free users have a daily and monthly chat quota, Pro users a
much larger one, and every client is capped at a few requests per minute.
Blocked requests return `429` with `{error, limit_type, plan}` where
`limit_type` is `daily`, `monthly` or `rate` — the exact numbers are never
exposed. Cache hits and failed AI generations do not consume quota. See the
`USAGE_*` variables in `.env.example`.

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/billing/plans/` | List plans plus enabled providers (eSewa, Khalti, Stripe) |
| POST | `/api/billing/checkout/` | Start checkout — body `{plan, provider}`; returns `checkout_url` (+ `form_fields` for eSewa) |
| POST | `/api/billing/verify/` | Confirm a redirected payment — body `{provider, reference}` or eSewa `{data}`; activates Pro |
| GET | `/api/billing/status/` | Get current user's billing status and recent payments |
| POST | `/api/billing/webhook/` | Stripe webhook handler |

Payment flow: `checkout/` → customer pays on eSewa/Khalti → gateway redirects to
`/billing?data=...` (eSewa) or `/billing?pidx=...` (Khalti) → frontend calls `verify/`,
which checks the transaction with the gateway's status/lookup API before granting Pro.

### RAG

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rag/status/` | RAG system health check |
| POST | `/rag/init/` | Initialize / re-ingest PDF textbooks |
| POST | `/rag/search/` | Manual curriculum search (debug) |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/` | Usage statistics (messages, sessions) |
| GET | `/api/cache/metrics/` | Cache hit rates and latency |
| GET | `/api/system/check/` | Full system health check |

---
