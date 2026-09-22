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

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/billing/plans/` | List available subscription plans |
| POST | `/api/billing/checkout/` | Create Stripe Checkout Session |
| GET | `/api/billing/status/` | Get current user's billing status |
| POST | `/api/billing/webhook/` | Stripe webhook handler |

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
