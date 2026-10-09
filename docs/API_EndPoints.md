# API endpoints

The root URL configuration mounts the API at `/api/`. Unless noted otherwise, protected endpoints use the JWT access token in `Authorization: Bearer <access-token>`. Permissions below reflect the current Django views.

## Health and system

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/ping/` | Public | Returns `{"status":"ok"}`. |
| GET | `/api/system/check/` | Public | Reports AI/RAG setup issues from the current process. |
| GET | `/api/rag/status/` | Public | Reports RAG initialization and indexed chunk count. |

## Authentication and account

| Method | Path | Access | Behavior |
|---|---|---|---|
| POST | `/api/auth/register/` | Public | Creates an account; accepts serializer fields and optional referral code `ref`. |
| POST | `/api/auth/login/` | Public | SimpleJWT token-pair endpoint. |
| POST | `/api/auth/refresh/` | Public | Refreshes an access token. |
| POST | `/api/auth/logout/` | Public | Accepts `refresh`; blacklists it when supplied. |
| GET | `/api/auth/user/` | JWT required | Returns the current profile; returns 401 without an authenticated user. |
| PATCH | `/api/auth/user/` | JWT required | Partially updates fields allowed by `UserSerializer`. Billing fields, `plan_tier`, and referral code are read-only. |
| GET | `/api/referral/info/` | JWT required | Returns referral code, referral count, and referral URL. |

## Chat and history

| Method | Path | Access | Behavior |
|---|---|---|---|
| POST | `/api/chat/` | Public; optional JWT | Sends a chat request and returns a Server-Sent Events stream. Guests may chat; only authenticated users get persisted sessions and message history. Daily/monthly quotas apply to successful non-cache answers; per-minute limits count attempts. |
| GET | `/api/chat/sessions/` | JWT required | Lists the current user's recent sessions (up to 50). |
| POST | `/api/chat/sessions/` | JWT required | Creates a session. The view reads `title`, `subject`, `grade`, and `language`. |
| DELETE | `/api/chat/sessions/` | JWT required | Deletes the owned session whose `session_id` is in the JSON body. |
| GET | `/api/chat/sessions/{session_id}/` | JWT required | Returns one owned session and its messages. |
| GET | `/api/chat/history/?limit=50&session_id={id}` | JWT required | Returns the user's messages. `session_id` is optional; without it, the most recent messages are returned. |
| DELETE | `/api/chat/history/?session_id={id}` | JWT required | Deletes messages and the owned session when `session_id` is supplied; otherwise clears the user's history and sessions. |
| DELETE | `/api/chat/clear/` | JWT required | Alias to the same history-clear view. |

Chat events are sent as `data: {JSON}\n\n` records. The final event includes the response and source fields, and may include session metadata for authenticated users. Cache hits and failed model generations do not consume daily/monthly chat quota.

## Usage

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/usage/stats/` | Public; optional JWT | Returns the caller's current daily and monthly `used`, `limit`, `remaining`, and `resets_at` values. Authenticated callers are keyed by user; guests are keyed by the resolved client IP. It also returns account message/session totals for authenticated callers. |

Default quotas are 15 daily/300 monthly chats for Free and 150 daily/1,000 monthly for Pro when optional billing is enabled; the request-rate limit defaults to 5 per minute. Configure `USAGE_FREE_DAILY_LIMIT`, `USAGE_FREE_MONTHLY_LIMIT`, `USAGE_PAID_DAILY_LIMIT`, `USAGE_PAID_MONTHLY_LIMIT`, and `USAGE_RATE_LIMIT_PER_MINUTE` to override them. Blocked chat requests return HTTP 429 with `limit_type` (`daily`, `monthly`, or `rate`) and `plan`.

## Textbooks and curriculum retrieval

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/textbooks/{subject}/pdf/` | Public | Streams a local subject PDF if present; otherwise returns 404. |
| GET | `/api/textbooks/pages/?subject=math&chapter=1&include_text=false` | Public | Returns the configured chapter page range; optionally includes extracted page text when `include_text=true`. Query fields include `subject`, `unit`, `chapter`, and `title`. |
| GET | `/api/rag/search/?query=...&grade=10&subject=science&top_k=5` | Public | Diagnostic Qdrant search. Requires RAG to be initialized and returns 503 otherwise. |
| POST | `/api/rag/init/` | Django admin user | Initializes/re-indexes local PDFs. Body may include `force_rebuild`; rebuilding replaces the Qdrant collection. |

The PDF files and reachable Qdrant service are external setup requirements; they are not included in this checkout. See [RAG and textbook context](RAG_PIPELINE.md).

## Cache and knowledge base

| Method | Path | Access | Behavior |
|---|---|---|---|
| POST | `/api/cache/inspect/` | JWT required | Runs cache lookup for the supplied message/context and returns the decision and match metadata. |
| GET | `/api/cache/knowledge/` | JWT required | Lists active knowledge entries; supports `subject`, `grade`, and `chapter` filters. |
| POST | `/api/cache/knowledge/` | Staff user | Creates a knowledge entry after deriving its scope and fingerprint. |
| GET | `/api/cache/answers/` | JWT required | Lists active learned answers; supports `subject`, `grade`, and `limit`. |
| GET | `/api/cache/metrics/` | JWT required | Returns decision counts and timing for the latest 1,000 lookup events. |
| POST | `/api/cache/process-content/` | Staff user | Uses Gemini to process supplied textbook text into up to six answer types; accepts `save` to control persistence. |
| POST | `/api/cache/clear/` | Public | Clears only the current process's in-memory LRU. It does not delete database cache or knowledge entries. |

## Other

| Method | Path | Access | Behavior |
|---|---|---|---|
| POST | `/api/analytics/track/` | Public | Prints the event and data to the backend log and returns `{"ok":true}`; this view does not persist analytics records. |

## Optional billing

Billing routes are added only when the optional billing backend and frontend files exist and the billing module imports successfully. When enabled:

| Method | Path | Access | Behavior |
|---|---|---|---|
| GET | `/api/billing/plans/` | Public | Lists available plans and configured payment providers. |
| POST | `/api/billing/checkout/` | JWT required | Starts checkout for the requested plan/provider. |
| GET | `/api/billing/status/` | JWT required | Returns the current user's billing state and recent payments. |
| POST | `/api/billing/verify/` | JWT required | Verifies a returned payment with its gateway before activating access. |
| POST | `/api/billing/webhook/` | Public endpoint; Stripe signature required | Receives Stripe events. A missing webhook secret causes the handler to reject the request. |

Provider credentials and the relevant optional modules must be configured before these routes are available. See `backend-main/api/features.py` and `.env.example`.

