# OpsPilot — Enterprise AI Engineer Portfolio Roadmap

> **What you're building:** *OpsPilot*, an AI operations copilot added to an **existing** e‑commerce company's systems
> (fictional company: **Acme Market**). It reads their orders database, policy documents and support tickets. It answers
> questions with citations, analyzes the business data, takes actions with human approval, and reports its own cost,
> quality and safety.
>
> **Why this domain:** AI Engineer and Forward Deployed Engineer (FDE) roles are mostly about **integrating AI into a system
> that already exists**, not building a demo from scratch. So the project starts with a "legacy" system you don't
> rewrite, and every AI feature has to plug into it the way it would at a real customer.
>
> **Profile:** full-stack (Python + TypeScript) · Target: AI Engineer / FDE · Budget: **≤ $20/month** · Pace: self-paced

---

## How to use this file

- Work through the phases **in order**. Each phase has:
  - **Understand**: concepts you should be able to explain in an interview (check them off only when you can explain them without notes).
  - **Build**: implementation tasks.
  - **Proof**: what you show on GitHub, in the README or in a demo. A phase is done when its proof exists.
- Mark items `[x]` as you finish them, and add a line to the **Progress Log** at the bottom with the date and any notes.
- To continue in any new Claude Code session, say: *"Read ROADMAP.md, check my progress, and guide me through the next item."* (`CLAUDE.md` tells Claude how to mentor you.)
- Rule of thumb: **write the core logic yourself**. Use AI to explain, review and scaffold boilerplate. You need to be able to defend every line in an interview.
- Hour estimates are rough. Total is about **280–350 hours**.

---

## Architecture (target end state)

```
                ┌──────────────────────────── Next.js (Vercel) ─────────────────────────────┐
                │  Chat UI (streaming, citations, tool cards, approvals)                    │
                │  Ops dashboard · Token/cost dashboard · Eval & trace viewer · Admin/RBAC  │
                └───────────────▲───────────────────────────────────────────────────────────┘
                                │ SSE / REST (JWT)
┌───────────────────────────────┴──────────────── OpsPilot API (FastAPI) ─────────────────────────────┐
│ Auth/RBAC/tenancy · Rate limits & budgets · Guardrails (input/output/tool) · Audit log             │
│ LLM Gateway (LiteLLM: Claude / Gemini / Ollama, fallback, caching, cost metering)                  │
│ Agent Orchestrator (LangGraph supervisor) ──► Knowledge agent (RAG)                                │
│                                           ├─► Analyst agent (text-to-SQL + sandboxed Python)       │
│                                           ├─► Ops agent (actions via MCP, human-in-the-loop)       │
│                                           └─► A2A client ──► Logistics Partner Agent (separate svc)│
│ Skills registry · Prompt registry · Memory                                                         │
└──────┬──────────────────┬──────────────────────┬───────────────────────┬──────────────────────────┘
       │                  │                      │                       │
 Postgres + pgvector   Redis (cache,        OMS MCP Server ──► "Legacy" Order Mgmt System (REST + own DB)
 (app, vectors,        queues, limits)       (wraps legacy API)       ▲ webhooks / outbox events
  analytics marts)                                                    │
       ▲                                                              │
 Ingestion & analytics: Dagster ── dbt ── document parsing/chunking/embedding ── data quality checks
 Observability: Langfuse (LLM traces, evals, prompts) + OpenTelemetry + structured logs
 CI/CD: GitHub Actions (+ Jenkins pipeline) → Docker images → Vercel / Render|Fly / AWS (Terraform)
```

## Tech stack (decided, so you're not choosing forever)

| Layer | Primary choice | Also learn the concept of / alternatives |
|---|---|---|
| Backend | Python 3.12, **FastAPI**, Pydantic v2, SQLAlchemy 2 + Alembic, `uv`, ruff, pyright, pytest | Django, Flask |
| Frontend | **Next.js** (App Router) + TypeScript, Tailwind, shadcn/ui, **Vercel AI SDK**, Recharts, TanStack Query | assistant-ui, Streamlit (prototyping only) |
| Database | **Postgres 16 + pgvector** (local Docker → Neon free tier) | Qdrant, Pinecone, Weaviate, OpenSearch |
| Cache/queue | **Redis** (local → Upstash free) + **Celery** workers | arq, SQS, Kafka (concept) |
| Data/ETL | **Dagster** + **dbt** (dbt-postgres) + DuckDB for ad-hoc work; **pandera** for data quality | Airflow (most common in job ads), Prefect, Great Expectations, Fivetran/Airbyte |
| Doc parsing | **Docling** or `unstructured` | LlamaParse, AWS Textract |
| LLMs | **LiteLLM** in front of Claude (cheap tier by default, strong tier for hard tasks), Gemini free tier, **Ollama** locally | OpenAI, Bedrock, Azure OpenAI, vLLM |
| Embeddings / rerank | `bge-small`/`nomic-embed` via Ollama/fastembed (free) · FlashRank or `bge-reranker` | Voyage, Cohere, OpenAI embeddings |
| Agents | Raw tool-use loop first (from scratch), then **LangGraph** | Claude Agent SDK, OpenAI Agents SDK, PydanticAI, CrewAI, AutoGen |
| Protocols | **MCP** (official Python SDK / FastMCP), **A2A** (a2a-sdk), Agent Skills (`SKILL.md`) | OpenAPI tools, function calling |
| Guardrails | Custom policy layer + **Presidio** (PII) + **LLM Guard** / Llama Guard (injection/toxicity) | NeMo Guardrails, Guardrails AI, Bedrock Guardrails |
| Evals | **DeepEval** (pytest-style) + **Ragas** metrics + **promptfoo** (red teaming) | Braintrust, LangSmith |
| Observability | **Langfuse** (cloud free/self-host) + **OpenTelemetry** + structlog | Arize Phoenix, LangSmith, Datadog |
| Auth | **Auth.js** (Next) + JWT validation in FastAPI; optional **Keycloak** for SSO/OIDC | Clerk, Auth0, Cognito, Entra ID |
| Containers | **Docker**, docker compose, multi-stage builds | Podman |
| CI/CD | **GitHub Actions** (main) + **Jenkins** (Jenkinsfile, run locally in Docker) | GitLab CI, ArgoCD |
| Cloud | **Vercel** (web) + **Render/Fly.io** (API, free/cheap) + **AWS via Terraform** (ECS Fargate/ECR/RDS/Secrets Manager; deploy, demo, destroy) | GCP Cloud Run, Azure |
| Optional | Kubernetes (kind/k3d + Helm), LoRA fine-tuning, voice | EKS, SageMaker |

## Monthly budget (≤ $20)

| Item | Cost |
|---|---|
| LLM API (cheap model by default, prompt caching, Ollama/Gemini free tier for dev) | $5–12 |
| Vercel Hobby, Neon, Upstash, Langfuse Cloud Hobby, GitHub Actions (public repo) | $0 |
| API host: Render free (sleeps when idle) or Fly.io | $0–5 |
| AWS: spin up with Terraform → record demo → `terraform destroy` (set an **AWS Budgets alert at $5**) | $1–5 per session |
| Domain name (optional, yearly) | ~$1/mo |

**Cost safety rules:** set hard spend limits in every LLM provider console. Put a per-user daily token budget in your own app (Phase 9). Never leave an AWS NAT Gateway or ALB running overnight.

---

## Phase 0 — Foundations, repo & walking skeleton (~15–20 h)

**Understand**
- [ ] How LLMs work at a working level: tokens, context window, temperature/top-p, why outputs are non-deterministic, hallucination
- [ ] Pricing model: input vs output vs cached tokens; how to estimate cost per request and per user per month
- [ ] Embeddings: what they are, cosine similarity, dimensions, why domain matters
- [ ] What AI Engineers and FDEs actually do: read 10 job postings and note the repeated keywords in `docs/job-keywords.md`

**Build**
- [x] Monorepo layout:
  ```
  apps/web            # Next.js
  apps/api            # FastAPI (OpsPilot)
  apps/legacy-oms     # the "existing" system (Phase 1)
  apps/partner-agent  # A2A logistics agent (Phase 7)
  mcp/oms-mcp         # MCP server (Phase 6)
  data/               # dagster + dbt + ingestion (Phase 2)
  evals/              # datasets + eval suites (Phase 9)
  infra/              # docker, terraform, jenkins
  docs/adr/           # architecture decision records
  ```
- [x] Tooling: `uv`, ruff, pyright, pytest, pnpm, eslint/prettier, **pre-commit** hooks, `.env.example`, `Makefile` (`make dev`, `make test`, `make lint`)
- [x] `docker compose up` brings up Postgres(pgvector) + Redis + API (hello endpoint) + web (hello page)
- [x] GitHub Actions: lint + test on every PR (start CI on day 1)
- [ ] Deploy the hello-world web app to Vercel right away (deploy early, deploy often)
- [ ] Write ADR-001 "Tech stack choices" (use the template in `docs/adr/`)
- [ ] Get API keys and **set spend limits**: Anthropic, Google AI Studio (Gemini free tier); install Ollama and pull a small model + an embedding model

**Proof:** public repo, green CI badge, live Vercel URL, ADR-001.

---

## Phase 1 — The "existing enterprise system" you integrate with (~15–20 h)

*FDE mindset: you're joining Acme Market. They already have an Order Management System (OMS) and you can't rewrite it.*

**Understand**
- [ ] Integration patterns: REST API wrapping, DB read replicas, webhooks, event-driven (transactional outbox), batch export, CDC (change data capture)
- [ ] Why AI should get **least-privilege, read-only** access by default, with writes going through the system's own API (business rules, audit)
- [ ] How to run a customer discovery: stakeholders, success metrics, constraints (security, data residency, latency, budget)

**Build**
- [ ] Download the **Olist Brazilian E-Commerce dataset** (Kaggle, ~100k orders: customers, orders, items, payments, sellers, products, reviews)
- [ ] `legacy-oms`: a separate FastAPI service with its **own** Postgres schema loaded from Olist. Endpoints: get order, search orders, customer history, create refund request, update order status. Add API-key auth and deliberately "legacy" quirks (pagination limits, odd field names) to make the integration realistic
- [ ] Emit events (`order.updated`, `refund.requested`) via a **transactional outbox** table and a webhook dispatcher
- [ ] Synthetic unstructured data: use an LLM (cheap model or Ollama) to generate:
  - [ ] ~30 policy/runbook docs (returns, shipping SLAs, seller handbook, fraud procedure, refund approval matrix) as PDF/Markdown/HTML, each tagged `public` / `internal` / `finance-only`
  - [ ] ~2,000 support tickets tied to real Olist order IDs (categories, sentiment, resolution)
  - [ ] This is synthetic data generation, itself a skill: write about it in `docs/`
- [ ] `docs/discovery.md`: a mock customer discovery write-up covering problem, users (support agent, ops manager, analyst, exec), success metrics (e.g., -30% ticket handling time), constraints, risks

**Proof:** running legacy OMS with OpenAPI docs, data generator scripts, discovery doc.

---

## Phase 2 — Data integration: ingestion, pipelines, analytics (~30–35 h)

**Understand**
- [ ] ETL vs ELT; batch vs streaming; idempotency; incremental loads (watermarks); backfills
- [ ] Medallion / staging → intermediate → marts modeling; star schema (facts/dimensions)
- [ ] Data quality: schema checks, null/uniqueness/range tests, freshness SLAs, data contracts
- [ ] Unstructured ingestion: parsing (layout, tables), cleaning, **chunking strategies** (fixed, recursive, semantic, by heading), metadata, dedup
- [ ] Data lineage and why enterprises care (governance, PII, access control)

**Build**
- [ ] **Structured pipeline (Dagster):** extract from the legacy OMS (API + DB replica) → load into the OpsPilot warehouse schema → **incremental** sync with watermarks, plus a webhook-triggered refresh
- [ ] **dbt project:** staging → marts (`fct_orders`, `fct_reviews`, `dim_customers`, `dim_sellers`, `mart_daily_sales`, `mart_delivery_sla`) with dbt tests and generated docs
- [ ] **Data quality:** pandera/dbt tests; failing checks block downstream assets; record results
- [ ] **Unstructured pipeline:** watch a docs folder (or S3 bucket later) → parse (Docling) → clean → chunk (compare 2 strategies) → embed → upsert into pgvector with metadata (`source`, `section`, `acl`, `version`, `hash`)
  - [ ] Re-ingest only changed docs (content hash); delete vectors for removed docs
  - [ ] Store document-level **ACLs** with each chunk (needed for permission-aware RAG)
- [ ] Ticket pipeline: tickets → embeddings + LLM-extracted fields (category, product, sentiment) using **structured outputs** (batch API if available, which is cheaper)
- [ ] PII handling at ingestion: detect and mask emails/phones/names in tickets with Presidio, keeping a reversible token vault only where justified
- [ ] Dagster schedules + sensors; the UI shows lineage from source → marts → vector index

**Proof:** Dagster lineage screenshot, dbt docs site, data quality report, ADR-002 "Chunking strategy" with measured comparison (filled in after Phase 4/9 evals).

---

## Phase 3 — LLM core: gateway, prompts, structured output, cost metering (~20–25 h)

**Understand**
- [ ] Messages API structure (system/user/assistant, tool calls), streaming (SSE), stop reasons
- [ ] **Prompt engineering:** clear role/task/constraints, XML-tagged context, few-shot, chain-of-thought vs extended thinking, output schemas, prompt chaining
- [ ] **Context engineering:** what goes in the window, ordering, compression, why less is often better
- [ ] **Prompt caching** (how it cuts cost/latency), semantic caching (risks), batch APIs
- [ ] Model selection and routing: cheap model for easy tasks, strong model for hard ones; fallback chains; timeouts/retries with backoff
- [ ] Structured outputs / JSON schema / tool-forced outputs, and validation with Pydantic

**Build**
- [ ] `llm/gateway.py` on top of LiteLLM: one interface for Claude / Gemini / Ollama, streaming, retries, timeout, **fallback model**, provider-agnostic tool calling
- [ ] **Usage metering:** every call writes a row to `llm_calls` (tenant, user, feature, model, input/output/cached tokens, cost USD, latency, status, trace_id)
- [ ] **Prompt registry:** prompts stored as versioned files (`prompts/*.yaml` with Jinja templates + metadata), loaded by name@version, and synced to Langfuse prompt management
- [ ] Prompt caching enabled for long system prompts and doc context; measure the before/after cost
- [ ] Redis exact-match response cache (opt-in per feature) + a note on why semantic caching is risky
- [ ] Minimal streaming chat endpoint `POST /chat` (SSE) + bare chat page in Next.js, to get a vertical slice working end to end

**Proof:** a chat that streams, a `llm_calls` table with real costs, prompt files under version control, ADR-003 "LLM gateway & model routing".

---

## Phase 4 — RAG that holds up in production (~30–35 h)

**Understand**
- [ ] Naive RAG vs advanced RAG; the common failure modes (bad chunking, wrong retrieval, lost-in-the-middle, stale docs, no-answer cases)
- [ ] Dense vs sparse (BM25) vs **hybrid** retrieval; Reciprocal Rank Fusion; **reranking**
- [ ] Query transformation: rewriting, multi-query, HyDE, decomposition; contextual retrieval (chunk context prefixes)
- [ ] HNSW vs IVFFlat indexes in pgvector; filtering with metadata
- [ ] **Permission-aware retrieval** (filter by user ACL *before* the LLM sees anything) and why it's a hard requirement in enterprise settings
- [ ] Grounding & **citations**; refusing when the context doesn't support an answer
- [ ] When RAG vs fine-tuning vs long context

**Build**
- [ ] Retriever: pgvector dense + Postgres full-text (BM25-like) → RRF → reranker (FlashRank/bge-reranker) → top-k
- [ ] Metadata + **ACL filtering** by the user's role (a support agent must not retrieve `finance-only` docs)
- [ ] Query rewriting with conversation history; multi-query for vague questions
- [ ] Answer generation with inline **citations** (doc, section, link) + a "not found in knowledge base" path
- [ ] Ticket similarity search ("show similar resolved tickets") as a second retrieval source
- [ ] Freshness: doc version shown in citations; re-index on doc change (from Phase 2)
- [ ] Build a **golden dataset now**: 50–100 Q&A pairs with expected source docs (including unanswerable and permission-trap questions), stored in `evals/datasets/rag.jsonl`

**Proof:** retrieval metrics (recall@k, MRR) for naive vs hybrid vs hybrid+rerank in a table, plus a demo of the same question answered differently for two roles.

---

## Phase 5 — Agents: build the harness, then use a framework (~35–40 h)

**Understand**
- [ ] What an **agent harness** is: the loop (model → tool calls → execute → feed results back), stop conditions, max steps, token/time budgets, error recovery, context management
- [ ] Tool design: clear names/descriptions, narrow inputs, idempotency, useful error messages, pagination, returning *just enough*
- [ ] Workflows vs agents: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, and **when not to use an agent**
- [ ] Memory: short-term (thread state), long-term (user/org facts), episodic; summarization/compaction of long sessions
- [ ] **Human-in-the-loop**: interrupts, approvals, resumable state (checkpointing)
- [ ] Text-to-SQL risks: injection, expensive queries, hallucinated columns, data leakage

**Build**
- [ ] **5a. Harness from scratch (~200 lines, no framework):** raw tool-use loop with max steps, per-run token budget, tool timeouts, structured tool errors, parallel tool calls, and tracing of each step. This is the piece you explain in interviews
- [ ] **5b. Analyst agent:** text-to-SQL over the dbt **marts** only
  - [ ] Schema retrieval (table/column descriptions from dbt docs) instead of dumping the whole schema
  - [ ] SQL validated with **sqlglot**: SELECT-only, allowed tables, `LIMIT` enforced, statement timeout, **read-only DB role**
  - [ ] Sandboxed Python for charts/stats (Docker sandbox or E2B free tier) → returns chart spec to the UI
- [ ] **5c. Ops agent:** tools that call the legacy OMS (look up order, customer history, draft reply, **request refund**)
  - [ ] Write actions require **approval** (interrupt → UI approve/reject → resume), checked against the refund approval matrix from the policy docs
- [ ] **5d. Port to LangGraph:** state graph, checkpointer (Postgres), interrupts for approvals, streaming of intermediate steps
- [ ] Conversation memory: thread history + summarization when over N tokens; long-term "user preferences" store
- [ ] Background job: a scheduled "daily ops digest" agent (Celery beat) that writes a report and posts it to the dashboard

**Proof:** harness code + write-up "What a harness does", trace screenshot of a multi-step run, a refund flow paused for approval.

---

## Phase 6 — MCP & Skills (~15–20 h)

**Understand**
- [ ] **MCP** architecture: host/client/server; tools, resources, prompts; transports (stdio vs Streamable HTTP); auth (OAuth) for remote servers
- [ ] Why MCP matters for integration: one adapter per system, reusable by any MCP-capable client (Claude Desktop, Claude Code, IDEs, your agent)
- [ ] MCP security: tool poisoning, over-broad permissions, confused deputy, prompt injection via tool results
- [ ] **Agent Skills:** packaged instructions + scripts + resources (`SKILL.md`) loaded on demand (progressive disclosure), and how they differ from tools and from MCP

**Build**
- [ ] `oms-mcp`: an MCP server wrapping the legacy OMS API (tools: `get_order`, `search_orders`, `create_refund_request`; resources: policy docs; prompts: "investigate late delivery")
  - [ ] Streamable HTTP transport + token auth; per-tool scopes (read vs write)
  - [ ] Test it with MCP Inspector **and** connect it to Claude Desktop/Claude Code (big demo value: "your system now works in any MCP client")
- [ ] Refactor the Ops agent to consume tools **via MCP** instead of direct HTTP calls
- [ ] Also consume one third-party MCP server (e.g., filesystem or GitHub) to show client-side integration
- [ ] **Skills registry** in OpsPilot: folders like `skills/refund-investigation/SKILL.md`, `skills/weekly-sales-report/`; the agent sees short descriptions and loads full instructions only when relevant
- [ ] Write one Claude Code skill for your own dev workflow (e.g., "add a new tool to the OMS MCP server") to show you use AI tooling well

**Proof:** a video of Claude Desktop using your OMS MCP server, the skills folder, ADR-004 "Direct tools vs MCP".

---

## Phase 7 — Multi-agent systems & Agent-to-Agent (A2A) (~20–25 h)

**Understand**
- [ ] Multi-agent patterns: supervisor/router, hierarchical, handoffs, swarm, debate/critic; costs (tokens × agents) and failure modes (loops, context loss between agents)
- [ ] **A2A protocol:** Agent Cards (discovery), tasks & lifecycle, messages/artifacts, streaming, push notifications, auth, and how it differs from MCP (agent↔agent vs agent↔tool)
- [ ] Cross-organization agent trust: auth, scoping, and not trusting another agent's output

**Build**
- [ ] **Supervisor graph** (LangGraph): routes to Knowledge / Analyst / Ops agents; shared state; handoff with context summaries; max-hop limit
- [ ] `partner-agent`: a separate service simulating a **third-party logistics company's agent** (built with a *different* framework, e.g. PydanticAI or Google ADK, to prove interoperability). It answers "where is shipment X / delay reason / ETA"
- [ ] Expose it via **A2A** (Agent Card at `/.well-known/agent-card.json`); OpsPilot discovers and calls it as an A2A client, including streaming status updates
- [ ] Treat partner responses as **untrusted input** (schema validation + guardrails)
- [ ] Compare one task done by a single agent vs multi-agent: quality, latency, cost. Record it honestly (sometimes single wins)

**Proof:** sequence diagram of a cross-agent request, comparison table, ADR-005 "When we use multi-agent".

---

## Phase 8 — Guardrails, safety & security (~20–25 h)

**Understand**
- [ ] **OWASP Top 10 for LLM Applications** (prompt injection, sensitive info disclosure, excessive agency, insecure output handling, supply chain, etc.)
- [ ] Direct vs **indirect prompt injection** (malicious text inside docs/tickets/tool results)
- [ ] Defense in depth: input filters, privilege separation, tool allowlists, output validation, HITL, monitoring. No single filter is enough
- [ ] PII/data protection basics: GDPR-style principles, data minimization, retention, audit logs

**Build**
- [ ] Guardrail pipeline as middleware with pluggable checks + per-tenant policy config:
  - [ ] Input: PII detection/redaction (Presidio), injection/jailbreak classifier (LLM Guard or Llama Guard via Ollama), topic/scope limits
  - [ ] Retrieval/tool results: scan for injected instructions and wrap them as data
  - [ ] Output: schema validation, PII leak check, **groundedness check** (claims supported by citations), toxicity
  - [ ] Tools: role-based allowlist, argument validation, rate limits, approval required for writes/high-value refunds
- [ ] Plant **poisoned documents/tickets** in the corpus (indirect injection) and prove they're neutralized
- [ ] **Red teaming** with promptfoo red-team plugins; save the report
- [ ] Audit log: who asked what, which data/tools were used, which guardrails fired (immutable table)
- [ ] Threat model doc (`docs/threat-model.md`) with STRIDE-style table

**Proof:** red-team report before/after, threat model, guardrail-trigger stats on the dashboard.

---

## Phase 9 — Evaluation & observability (LLMOps) (~25–30 h)

**Understand**
- [ ] Why evals are the core of AI engineering: you can't improve or safely change what you don't measure
- [ ] Offline evals (golden sets, regression) vs online evals (user feedback, sampled LLM-as-judge on production traffic)
- [ ] Metrics: retrieval (recall@k, MRR, nDCG), generation (faithfulness, answer relevance, context precision), agents (task success, tool-call accuracy, steps, cost, latency), safety (attack success rate)
- [ ] LLM-as-judge: rubric design, calibrating judges against human labels, judge bias
- [ ] Tracing: spans for retrieval/LLM/tool calls; p50/p95 latency; time-to-first-token

**Build**
- [ ] Langfuse integrated everywhere (traces per request, sessions, users, costs; prompt versions linked to traces)
- [ ] OpenTelemetry for non-LLM spans (DB, HTTP), structured JSON logs with `trace_id`
- [ ] Eval suites in `evals/`: RAG (Ragas/DeepEval), text-to-SQL (execution accuracy vs gold SQL), agent tasks (scenario tests with expected tool sequences), safety (red-team set)
- [ ] **CI eval gate:** PRs that change prompts/retrieval/agents run a small eval subset; merge blocked if scores drop beyond a threshold (use a cheap judge model to stay in budget)
- [ ] Thumbs up/down + comment in the UI → Langfuse scores → bad answers flow into the golden dataset (data flywheel)
- [ ] Experiment log: at least 3 documented experiments (chunk size, reranker on/off, model A vs B) with quality/cost/latency trade-offs

**Proof:** eval report table in the README, CI eval gate screenshot, Langfuse dashboard screenshot.

---

## Phase 10 — Product UI: chat, dashboards, cost (~30–35 h)

**Understand**
- [ ] Streaming UX (SSE, AI SDK data stream protocol), optimistic UI, cancellation
- [ ] Generative UI: rendering tool results as components (order cards, charts, approval dialogs)
- [ ] Designing trust into AI UX: citations, showing steps, confidence/uncertainty, easy feedback, undo

**Build**
- [ ] **Chat interface:** streaming, markdown, inline **citations** with source preview, visible agent steps/tool calls (collapsible), stop/regenerate, conversation history, file upload (ask about an uploaded PDF)
- [ ] **Approval inbox:** pending agent actions (refunds) with context and approve/reject → resumes the graph
- [ ] **Ops dashboard:** KPIs from dbt marts (sales, late deliveries, review scores, ticket volume by category/sentiment) + "Ask about this chart" button
- [ ] **Token & cost dashboard:** cost by day/model/feature/user/tenant, tokens in/out/cached, cache hit rate, p95 latency, error rate, **budgets** with progress bars, top expensive conversations (links to traces)
- [ ] **Quality & safety page:** eval scores over time, feedback rate, guardrail triggers
- [ ] **Admin:** users/roles, tenant settings (allowed models, budget limits, guardrail strictness), prompt versions in use, document sources + ingestion status
- [ ] Embeddable **chat widget** (script tag / iframe) to show "drop AI into an existing app"
- [ ] Accessibility basics + responsive layout; Playwright E2E tests for the key flows

**Proof:** a 3–5 min demo video walking through the user journeys; screenshots in the README.

---

## Phase 11 — Production hardening (~20–25 h)

**Understand**
- [ ] AuthN vs AuthZ; OAuth2/OIDC flows; JWT validation; RBAC vs ABAC; **multi-tenancy** (row-level security)
- [ ] Rate limiting & quotas (token bucket), backpressure, idempotency keys
- [ ] Resilience: timeouts, retries with jitter, circuit breakers, graceful degradation (LLM down → fallback model → canned response)
- [ ] Latency optimization: streaming, parallel tool calls, caching, smaller models, prompt trimming
- [ ] Testing pyramid for AI apps: unit (deterministic parts), integration (with recorded LLM responses), evals (non-deterministic), E2E

**Build**
- [ ] Auth.js login (GitHub OAuth + credentials) → JWT → FastAPI dependency checks roles: `support_agent`, `ops_manager`, `analyst`, `admin`
- [ ] Multi-tenant: `tenant_id` everywhere + **Postgres Row-Level Security**; second demo tenant to prove isolation
- [ ] Optional: Keycloak in docker compose for enterprise SSO (OIDC) demo
- [ ] Redis rate limits (per user/tenant) + **token budget enforcement** (hard stop + friendly message)
- [ ] Idempotency keys on action endpoints; Celery for long jobs (ingestion, reports) with retries/dead-letter
- [ ] Circuit breaker + fallback model on provider errors; chaos test: kill the LLM provider and show graceful degradation
- [ ] Recorded-LLM fixtures (VCR-style) so unit/integration tests run free and deterministic in CI
- [ ] Load test with **k6** or Locust (mock LLM): find the bottleneck, document p95 at N concurrent users
- [ ] Security hygiene: secrets never in repo (gitleaks in pre-commit), dependency scanning (Dependabot/Trivy), CORS, security headers

**Proof:** RLS isolation test, load test report, chaos test write-up.

---

## Phase 12 — Containers & CI/CD (~15–20 h)

**Understand**
- [ ] Docker layers & caching, multi-stage builds, slim/distroless images, non-root users, healthchecks
- [ ] CI vs CD; environments (dev/staging/prod); trunk-based development; semantic versioning; rollbacks
- [ ] Database migrations in pipelines (Alembic) and zero-downtime concerns

**Build**
- [ ] Production Dockerfiles for api, legacy-oms, oms-mcp, partner-agent, worker, dagster (multi-stage, non-root, healthcheck, < 300 MB where possible)
- [ ] `docker-compose.yml` (dev) + `docker-compose.prod.yml`; one command spins up the **entire** system with seed data
- [ ] **GitHub Actions:** lint → typecheck → unit tests → build images → **Trivy scan** → eval gate (on AI changes) → push to GHCR/ECR → deploy staging → manual approval → prod
- [ ] **Jenkins:** run Jenkins in Docker locally; write a `Jenkinsfile` with the same stages (declarative pipeline, credentials binding, parallel stages). Many enterprises still use Jenkins, so be able to talk about it
- [ ] Preview deployments on Vercel for every PR

**Proof:** pipeline screenshots (GHA + Jenkins), image sizes, one-command local setup in the README.

---

## Phase 13 — Cloud deployment (~20–25 h)

**Understand**
- [ ] AWS core: IAM (roles, least privilege), VPC/subnets/security groups, ECR, ECS Fargate, ALB, RDS, ElastiCache, S3, Secrets Manager, CloudWatch; and what costs money while idle
- [ ] **Infrastructure as Code** with Terraform: state, modules, plan/apply, remote state, environments
- [ ] Managed AI services: Amazon Bedrock (Claude on AWS), why enterprises use it (VPC, compliance, billing)
- [ ] Serverless vs containers trade-offs for streaming AI workloads

**Build**
- [ ] **Always-on cheap stack (the public demo):** Vercel (web) + Render/Fly.io (API, MCP, partner agent) + Neon (Postgres+pgvector) + Upstash (Redis) + Langfuse Cloud
- [ ] **AWS stack via Terraform** in `infra/terraform/`: ECR, ECS Fargate services, ALB, RDS Postgres (or Neon to save cost), S3 for documents (ingestion trigger), Secrets Manager, CloudWatch logs/alarms, IAM roles per service
  - [ ] `terraform apply` → record demo/screenshots → `terraform destroy`; document cost per hour
  - [ ] Optional: switch one model route to **Bedrock** through LiteLLM to show the enterprise cloud path
- [ ] GitHub Actions → AWS via **OIDC** (no long-lived keys)
- [ ] Monitoring: uptime check (free tier, e.g., Better Stack/UptimeRobot), alerts on error rate and daily LLM spend
- [ ] Runbook (`docs/runbook.md`): deploy, rollback, rotate secrets, re-index docs, handle LLM provider outage

**Proof:** live URL, Terraform code, AWS architecture diagram, runbook.

---

## Phase 14 — Optional advanced (pick what matches target jobs)

- [ ] **Kubernetes:** kind/k3d locally, Helm chart for the API + worker, HPA, readiness/liveness probes (EKS concepts)
- [ ] **Fine-tuning:** LoRA fine-tune a small open model (Colab/Kaggle free GPU) for ticket classification; compare with prompting a large model on cost/latency/accuracy
- [ ] **Local/private deployment:** run the full stack with Ollama/vLLM only ("air-gapped customer" scenario, which FDEs run into)
- [ ] **GraphRAG** / knowledge graph over sellers-products-orders
- [ ] **Voice** support agent (speech-to-text → agent → text-to-speech)
- [ ] **Computer use / browser agent** for a legacy system without an API
- [ ] **Streaming data:** Redpanda/Kafka for order events instead of webhooks

---

## Phase 15 — Package it for the job hunt (~15–20 h, don't skip)

- [ ] **README** as a case study: problem → architecture diagram → demo GIF/video → key decisions (link the ADRs) → **eval results** → cost per conversation → security → what you'd do next
- [ ] `docs/architecture.md` with C4-style diagrams (context, container, component)
- [ ] 3–5 min demo video (Loom): business story first, tech second
- [ ] **FDE artifacts:** discovery doc (Phase 1), integration playbook ("how to deploy OpsPilot at a new customer in 2 weeks"), customer-facing summary of a pilot's ROI
- [ ] 2–3 blog posts / LinkedIn write-ups (e.g., "Permission-aware RAG in Postgres", "Building an agent harness from scratch", "Exposing a legacy API to any AI client with MCP")
- [ ] Resume bullets with numbers (e.g., "hybrid retrieval + rerank raised recall@5 from 0.62 → 0.87 while cutting cost per answer 40% via prompt caching")
- [ ] Interview prep: be able to whiteboard any part of this system and answer:
  - [ ] Design a RAG system for 10M documents with per-user permissions
  - [ ] How do you evaluate and safely ship a prompt change?
  - [ ] An agent is looping and burning tokens: how do you detect it and prevent it?
  - [ ] How do you defend against indirect prompt injection?
  - [ ] Cut LLM cost by 50% without hurting quality: what do you try, in what order?
  - [ ] RAG vs fine-tuning vs long context: when do you pick each?
  - [ ] MCP vs A2A vs plain function calling
  - [ ] A customer says "the AI is wrong": walk through your debugging process (traces → retrieval → prompt → model)
  - [ ] Walk me through deploying this at a bank with strict data residency

---

## Learning resources (free)

- Anthropic docs: prompt engineering guide, tool use, prompt caching, *Building Effective Agents* (engineering blog), *Effective context engineering for AI agents*, Agent Skills docs
- Model Context Protocol docs + spec (modelcontextprotocol.io); A2A protocol docs (a2a-protocol.org)
- LangGraph docs + LangChain Academy (free "Intro to LangGraph" course)
- DeepLearning.AI short courses (free): RAG, agents, evals, MCP, A2A
- *AI Engineering* by Chip Huyen (book, paid but the best single overview)
- OWASP Top 10 for LLM Applications (genai.owasp.org)
- Hamel Husain's and Eugene Yan's blogs on evals and LLM systems
- dbt Learn (free), Dagster University (free), Terraform tutorials (developer.hashicorp.com)
- Full Stack Deep Learning / Made With ML (MLOps fundamentals)

---

## Progress Log

| Date | Phase / item | Notes (what I learned, blockers, decisions) |
|---|---|---|
| 2026-10-10 | Roadmap created | Starting Phase 0 |
| 2026-10-11 | P0: monorepo, tooling, docker compose | Walking skeleton runs: web → api health, Postgres(pgvector) + Redis. CI workflow written (runs once pushed). Next.js is v16.4: read `node_modules/next/dist/docs` before using new APIs. |
| 2026-10-11 | P0: GitHub Actions CI | Repo pushed to github.com/Yong-Ching/opspilot, CI green (api/web/docker). Note: `astral-sh/setup-uv` has no major tags, so pin the full version. |
| 2026-10-11 | P0: API keys + local models | Anthropic + Gemini keys verified (in gitignored apps/api/.env). Ollama: `qwen3:4b-instruct` (~45 tok/s on M3 Pro) + `nomic-embed-text` (768-dim). Lesson: the `qwen3:4b` thinking variant used 365 output tokens for a 1-sentence answer vs 34 for instruct, so watch hidden reasoning tokens in cost estimates. Pending: confirm Anthropic spend limit. |
