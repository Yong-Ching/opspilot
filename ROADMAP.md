# ResearchPilot — Enterprise AI Engineer Portfolio Roadmap

> **What you're building:** *ResearchPilot*, an AI research copilot for the investment team of **Harbourfront Capital**
> (a fictional Singapore asset manager, not affiliated with any real firm), covering **Singapore REITs and STI blue
> chips**. It plugs into the firm's **existing Portfolio Management System (PMS)** and reads REIT annual reports,
> results presentations, SGX announcements, market prices and MAS interest-rate data. It answers with **page-level
> citations**, screens and compares securities, drafts trade proposals that go through **compliance checks and PM
> approval**, and reports its own cost, accuracy and safety.
>
> **Why this domain:** banks, asset managers and wealth platforms are among Singapore's biggest AI employers. AI Engineer
> and Forward Deployed Engineer (FDE) roles are mostly about **integrating AI into systems that already exist**, so
> the project starts with a "legacy" PMS you don't rewrite. Finance also raises the hardest enterprise questions:
> exact numbers, regulation (MAS, PDPA), information barriers and audit trails.
>
> **Profile:** full-stack (Python + TypeScript) · Target: AI Engineer / FDE in Singapore · Budget: **≤ $20/month** · Pace: self-paced

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

## The business: Harbourfront Capital

| | |
|---|---|
| **What they do** | Singapore boutique asset manager: a REIT income fund, an Asia dividend fund and segregated mandates for wealthy clients |
| **Coverage universe** | ~15 S-REITs (retail, office, industrial, logistics, data centre, healthcare, hospitality) + ~10 STI blue chips (banks, telco, conglomerates). Final list fixed in Phase 1 |
| **Existing system** | *Harbourfront PMS*: an older REST API + Postgres with funds, holdings, transactions, client mandates, a compliance **restricted list** and an order blotter. ResearchPilot must integrate with it, not replace it |
| **Users** | Research analysts, portfolio managers (PMs), compliance officers, relationship managers (RMs) |
| **Example questions** | "Which S-REITs have gearing above 40% and falling interest coverage?" (cited) · "What did CICT say about rental reversions last quarter? Page?" · "If SORA rises 50 bps, which REITs' DPU is most exposed?" · "Draft a proposal to add 2% of a logistics REIT to the income fund" → compliance check → PM approves |
| **Hard rules** | Internal tool for licensed professionals: **no personalised advice to retail investors**. Every number must trace to a source. Research and deal-side information stays separated (MNPI) |

**Data sources** (all free; commit the download *scripts*, never the raw data or PDFs)
- **Filings:** REIT annual reports, results presentations and business updates from company IR pages (~100–150 PDFs, full of tables)
- **Market data:** daily prices, dividends and corporate actions (yfinance; unofficial, for research use)
- **Rates & macro:** MAS (SORA, SGS yields, FX), URA property price and rental indices (data.gov.sg), SingStat (CPI, GDP)
- **News & announcements:** SGX announcements and business news headlines (RSS)
- **Synthetic (Phase 1):** clients (KYC with NRIC, so PDPA applies), funds, mandates, trades at real historical prices, restricted list, ~200 internal analyst notes (some flagged MNPI), ~20 compliance policies

## Singapore & finance layer (applies across phases)

| Topic | Where | What you'll do |
|---|---|---|
| **Financial Advisers Act (FAA) / licensing** | 8 | Scope: an internal tool for licensed staff. Refuse personalised buy/sell advice to the public; add disclaimers |
| **MAS FEAT principles** (Fairness, Ethics, Accountability, Transparency) + MAS guidance on AI model risk management | 8, 9, 15 | Map controls in `docs/governance.md`; check MAS's latest AI risk management guidance and Project MindForge |
| **Information barriers / MNPI** (Securities and Futures Act) | 4, 8, 11 | Restricted notes are invisible to the wrong teams, enforced in retrieval and the database, and tested |
| **PDPA + NRIC** | 1, 2, 8 | Client KYC data: masking (`S****567A`, PDPC NRIC guidance), purpose limitation, retention, audit |
| **MAS Technology Risk Management (TRM)** | 13 | Access control, encryption, logging, backup/recovery in the runbook |
| **REIT rules** (MAS Code on Collective Investment Schemes, property funds appendix) | 2, 4 | Leverage and interest-coverage limits come from the *document*, never model memory (check current limits) |
| **IMDA GenAI framework + AI Verify / Project Moonshot** | 8, 9 | Governance mapping + red-teaming with Singapore's open-source toolkit |
| **Data residency** | 13 | AWS **ap-southeast-1 (Singapore)**; Bedrock in-region where available |
| **Local details** | all | SGD, SGT (UTC+8), `DD/MM/YYYY`, SGX board lots (100 shares), DPU in cents, SGX tickers (e.g. `C38U`) vs Yahoo tickers (`C38U.SI`) |

*Before each phase, verify the current version and availability of the regulatory documents and Singapore tools. They change.*

---

## Architecture (target end state)

```
                ┌──────────────────────────── Next.js (Vercel) ─────────────────────────────┐
                │  Research chat (streaming, page-level citations, PDF preview, approvals)  │
                │  REIT comparison · Fund exposure · Token/cost · Evals · Admin/RBAC        │
                └───────────────▲───────────────────────────────────────────────────────────┘
                                │ SSE / REST (JWT)
┌───────────────────────────────┴───────────── ResearchPilot API (FastAPI) ───────────────────────────┐
│ Auth/RBAC/information barriers · Rate limits & budgets · Guardrails (advice, numbers, PII) · Audit │
│ LLM Gateway (LiteLLM: Claude / Gemini / Ollama, fallback, caching, cost metering)                  │
│ Agent Orchestrator (LangGraph supervisor) ──► Filings agent (RAG over reports, page citations)     │
│                                           ├─► Quant agent (text-to-SQL + sandboxed Python)         │
│                                           ├─► Macro/rates agent · News agent · Risk critic         │
│                                           ├─► Trade agent (proposal → compliance → PM approval)    │
│                                           └─► A2A client ──► Data-vendor agent (separate svc)      │
│ Skills registry · Prompt registry · Memory                                                         │
└──────┬──────────────────┬──────────────────────┬───────────────────────┬──────────────────────────┘
       │                  │                      │                       │
 Postgres + pgvector   Redis (cache,        PMS MCP Server ──► "Legacy" Harbourfront PMS (REST + own DB)
 (app, vectors,        queues, limits)       (wraps legacy API)       ▲ webhooks / outbox events
  analytics marts)                                                    │
       ▲                                                              │
 Ingestion & analytics: Dagster ── dbt ── PDF parsing/table extraction/embedding ── data quality checks
 Feeds: prices & dividends · MAS SORA/SGS · URA indices · SGX announcements & news
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
| Data/ETL | **Dagster** + **dbt** (dbt-postgres) + DuckDB for ad-hoc work; **pandera** for data quality | Airflow (most common in job ads), Prefect, Great Expectations |
| Doc parsing | **Docling** (layout + tables) | `unstructured`, LlamaParse, AWS Textract |
| Market data | **yfinance**, MAS APIs, data.gov.sg, SingStat | Bloomberg / LSEG / S&P (paid; know they exist) |
| LLMs | **LiteLLM** in front of Claude (cheap tier by default, strong tier for hard tasks), Gemini free tier, **Ollama** locally | OpenAI, Bedrock, Azure OpenAI, vLLM |
| Embeddings / rerank | `nomic-embed` / `bge` via Ollama/fastembed (free) · FlashRank or `bge-reranker` | Voyage (has finance models), Cohere |
| Agents | Raw tool-use loop first (from scratch), then **LangGraph** | Claude Agent SDK, OpenAI Agents SDK, PydanticAI, CrewAI |
| Protocols | **MCP** (official Python SDK / FastMCP), **A2A** (a2a-sdk), Agent Skills (`SKILL.md`) | OpenAPI tools, function calling |
| Guardrails | Custom policy layer (advice, numbers, barriers) + **Presidio** (PII, SG recognizers) + **LLM Guard** / Llama Guard (injection) | NeMo Guardrails, Guardrails AI, Bedrock Guardrails |
| Evals | **DeepEval** + **Ragas** + **promptfoo** + **Project Moonshot** | Braintrust, LangSmith; FinanceBench (public benchmark) |
| Observability | **Langfuse** (cloud free/self-host) + **OpenTelemetry** + structlog | Arize Phoenix, LangSmith, Datadog |
| Auth | **Auth.js** (Next) + JWT validation in FastAPI; optional **Keycloak** for SSO/OIDC | Clerk, Auth0, Cognito, Entra ID |
| Containers | **Docker**, docker compose, multi-stage builds | Podman |
| CI/CD | **GitHub Actions** (main) + **Jenkins** (Jenkinsfile, run locally in Docker) | GitLab CI, ArgoCD |
| Cloud | **Vercel** (web) + **Render/Fly.io** (API, free/cheap) + **AWS ap-southeast-1 via Terraform** (ECS Fargate/ECR/RDS/Secrets Manager; deploy, demo, destroy) | GCP Cloud Run, Azure |
| Optional | Kubernetes (kind/k3d + Helm), backtesting (vectorbt), LoRA fine-tuning, GraphRAG | EKS, SageMaker |

## Monthly budget (≤ $20)

| Item | Cost |
|---|---|
| LLM API (cheap model by default, prompt caching, Ollama/Gemini free tier for dev). PDF extraction runs once, locally where possible | $5–12 |
| Vercel Hobby, Neon, Upstash, Langfuse Cloud Hobby, GitHub Actions (public repo) | $0 |
| yfinance, MAS, data.gov.sg, SingStat, company PDFs | $0 |
| API host: Render free (sleeps when idle) or Fly.io | $0–5 |
| AWS: spin up with Terraform → record demo → `terraform destroy` (set an **AWS Budgets alert at $5**) | $1–5 per session |

**Cost safety rules:** set hard spend limits in every LLM provider console. Put a per-user daily token budget in your own app (Phase 11). Never leave an AWS NAT Gateway or ALB running overnight.

---

## Phase 0 — Foundations, repo & walking skeleton (~15–20 h)

**Understand**
- [x] How LLMs work at a working level: tokens, context window, temperature/top-p, why outputs are non-deterministic, hallucination
- [x] Pricing model: input vs output vs cached tokens; how to estimate cost per request and per user per month
- [x] Embeddings: what they are, cosine similarity, dimensions, why domain matters
- [ ] What AI Engineers and FDEs actually do: read 10 job postings and note the repeated keywords in `docs/job-keywords.md`

**Build**
- [x] Monorepo layout:
  ```
  apps/web            # Next.js
  apps/api            # FastAPI (ResearchPilot)
  apps/legacy-pms     # Harbourfront's existing Portfolio Management System (Phase 1)
  apps/partner-agent  # external data vendor's agent, A2A (Phase 7)
  mcp/pms-mcp         # MCP server wrapping the PMS (Phase 6)
  data/               # dagster + dbt + ingestion (Phase 2)
  evals/              # datasets + eval suites (Phase 9)
  infra/              # docker, terraform, jenkins
  docs/adr/           # architecture decision records
  ```
- [x] Tooling: `uv`, ruff, pyright, pytest, pnpm, eslint/prettier, **pre-commit** hooks, `.env.example`, `Makefile` (`make dev`, `make test`, `make lint`)
- [x] `docker compose up` brings up Postgres(pgvector) + Redis + API (hello endpoint) + web (hello page)
- [x] GitHub Actions: lint + test on every PR (start CI on day 1)
- [x] Deploy the hello-world web app to Vercel right away (deploy early, deploy often)
- [ ] Write ADR-001 "Tech stack choices" (use the template in `docs/adr/`)
- [x] Get API keys and **set spend limits**: Anthropic, Google AI Studio (Gemini free tier); install Ollama and pull a small model + an embedding model

**Proof:** public repo, green CI badge, live Vercel URL, ADR-001.

---

## Phase 1 — The "existing enterprise system" you integrate with (~20–25 h)

*FDE mindset: you're joining Harbourfront Capital. They already have a Portfolio Management System (PMS) and you can't rewrite it.*

**Understand**
- [ ] Integration patterns: REST API wrapping, DB read replicas, webhooks, event-driven (transactional outbox), batch export, CDC (change data capture)
- [ ] Why AI should get **least-privilege, read-only** access by default, with writes going through the system's own API (business rules, audit)
- [ ] How to run a customer discovery: stakeholders, success metrics, constraints (security, **PDPA**, **MAS** expectations, data residency, latency, budget)
- [ ] Buy-side basics: funds vs mandates, holdings and weights, NAV, order lifecycle (proposed → approved → executed), restricted list, four-eyes approval, MNPI and information barriers
- [ ] S-REIT basics: DPU, distribution yield, gearing (aggregate leverage), interest coverage ratio (ICR), NAV per unit and P/NAV, occupancy, WALE, rental reversion, sponsor, cost of debt and SORA

**Build**
- [x] v1: `legacy-oms` built as an e-commerce order system (Olist data, API-key auth, legacy quirks, outbox table, tests, CI). The code structure is reused below; the Olist data is dropped
- [ ] **Rename** OpsPilot → ResearchPilot (`opspilot_api` → `researchpilot_api`, `OPSPILOT_` → `RP_`, web title). Optional: rename the GitHub repo (old links redirect) and the Vercel project
- [x] **Coverage universe:** pick ~15 S-REITs across sectors + ~10 STI blue chips; record SGX code, Yahoo ticker, sector, sponsor, IR page URL in `data/universe.csv` (verify each ticker)
- [x] **Rework into `legacy-pms`** (Harbourfront PMS):
  - [x] Tables: `securities` (internal IDs that differ from tickers, so mapping is needed), `funds`, `clients` (synthetic KYC incl. NRIC), `mandates` (limits: single-issuer %, sector caps, exclusions), `transactions`, `holdings` (derived), `restricted_list`, `orders` (blotter)
  - [x] Loader: synthetic funds/clients/mandates + trade history **at real historical prices** (so P&L and weights are realistic)
  - [x] Endpoints: fund + holdings, exposure by sector/issuer, client mandate, restricted-list check, transactions, **propose order**, **approve/reject order** (approver must differ from proposer: four-eyes)
  - [x] Keep the legacy quirks (HTTP 200 errors, `DD/MM/YYYY`, page cap) and add finance ones: quantities in board lots, prices in cents in some fields, internal security codes
- [ ] Emit events (`order.proposed`, `order.approved`, `order.rejected`, `restricted_list.updated`) via a **transactional outbox** table and a webhook dispatcher **(yours)**
- [ ] Synthetic unstructured data: use an LLM (cheap model or Ollama) to generate:
  - [ ] ~20 internal policies, each tagged `public` / `internal` / `compliance-only`: investment policy, mandate guidelines, conflicts of interest, personal trading, **information barrier SOP**, best execution, research note standards, **AI usage policy**, PDPA data protection policy
  - [ ] ~200 internal analyst notes on covered names, some flagged **MNPI / restricted** (for information-barrier tests)
  - [ ] ~1,000 research requests from PMs and RMs (the questions people actually ask), used for analytics and evals
  - [ ] This is synthetic data generation, itself a skill: write about it in `docs/`
- [ ] `docs/discovery.md`: a mock customer discovery write-up covering problem (analysts spend hours reading reports), users (analyst, PM, compliance, RM), success metrics (e.g., -50% time to produce a REIT earnings summary, 0 uncited numbers), constraints (PDPA, MAS, data stays in Singapore, no retail advice), risks

**Proof:** running legacy PMS with OpenAPI docs, universe file, data generator scripts, discovery doc.

---

## Phase 2 — Data integration: ingestion, pipelines, analytics (~30–35 h)

**Understand**
- [ ] ETL vs ELT; batch vs streaming; idempotency; incremental loads (watermarks); backfills
- [ ] Medallion / staging → intermediate → marts modeling; star schema (facts/dimensions)
- [ ] Data quality: schema checks, null/uniqueness/range tests, freshness SLAs, data contracts
- [ ] Unstructured ingestion: PDF parsing (layout, **tables**), cleaning, **chunking strategies** (fixed, recursive, semantic, by heading), metadata, dedup
- [ ] Financial data pitfalls: corporate actions (splits, rights issues), adjusted vs unadjusted prices, ex-dividend dates, currency, restatements
- [ ] Data lineage and why regulated firms care (audit, PII, access control)

**Build**
- [ ] **PMS pipeline (Dagster):** extract from the legacy PMS (API + DB replica) → load into the ResearchPilot warehouse → **incremental** sync with watermarks, plus a webhook-triggered refresh
- [ ] **Market & macro pipelines:** daily prices/dividends (yfinance), MAS SORA + SGS yields, URA indices, SingStat; handle API outages, missing days, SGX holidays
- [ ] **Filings pipeline:** download REIT reports from IR pages → parse with Docling (text + tables, **page numbers kept**) → chunk (compare 2 strategies) → embed → upsert into pgvector with metadata (`security`, `doc_type`, `period`, `page`, `acl`, `version`, `hash`)
  - [ ] Re-ingest only changed docs (content hash); delete vectors for removed docs
  - [ ] Store document-level **ACLs** with each chunk (MNPI notes, compliance-only policies)
- [ ] **Structured extraction:** LLM extracts REIT metrics (DPU, gearing, ICR, occupancy, WALE, NAV/unit, cost of debt, % fixed-rate debt) into a typed schema **with source page**, using **structured outputs**
  - [ ] Hand-verify ~50 values as a golden set; extraction accuracy is a data-quality check
- [ ] **dbt project:** staging → marts (`fct_prices`, `fct_distributions`, `fct_reit_metrics`, `dim_securities`, `mart_reit_comparison` (yield, P/NAV, gearing, ICR, WALE), `mart_fund_exposure`, `mart_rate_sensitivity`) with dbt tests and generated docs
- [ ] **Data quality:** pandera/dbt tests (e.g., gearing between 0–60%, yield sanity bounds, no future-dated prices); failing checks block downstream assets
- [ ] PII handling (**PDPA**): Presidio with **custom Singapore recognizers** (NRIC/FIN with checksum, +65 phones, addresses) on client data; written retention rules
- [ ] Dagster schedules + sensors; the UI shows lineage from source → marts → vector index

**Proof:** Dagster lineage screenshot, dbt docs site, extraction accuracy report, ADR-002 "Chunking & table strategy for financial PDFs" with measured comparison.

---

## Phase 3 — LLM core: gateway, prompts, structured output, cost metering (~20–25 h)

**Understand**
- [ ] Messages API structure (system/user/assistant, tool calls), streaming (SSE), stop reasons
- [ ] **Prompt engineering:** clear role/task/constraints, XML-tagged context, few-shot, chain-of-thought vs extended thinking, output schemas, prompt chaining
- [ ] **Context engineering:** what goes in the window, ordering, compression, why less is often better (long annual reports!)
- [ ] **Prompt caching** (how it cuts cost/latency), semantic caching (risks), batch APIs
- [ ] Model selection and routing: cheap model for easy tasks, strong model for hard ones; fallback chains; timeouts/retries with backoff
- [ ] Structured outputs / JSON schema / tool-forced outputs, and validation with Pydantic
- [ ] Why LLMs are bad at arithmetic, and why calculations belong in code (tools), not in the model's head

**Build**
- [ ] `llm/gateway.py` on top of LiteLLM: one interface for Claude / Gemini / Ollama, streaming, retries, timeout, **fallback model**, provider-agnostic tool calling
- [ ] **Usage metering:** every call writes a row to `llm_calls` (team, user, feature, model, input/output/cached tokens, cost USD, latency, status, trace_id)
- [ ] **Prompt registry:** prompts stored as versioned files (`prompts/*.yaml` with Jinja templates + metadata), loaded by name@version, and synced to Langfuse prompt management
- [ ] Prompt caching for long system prompts and report context; measure the before/after cost
- [ ] **Calculator tools** (yield, P/NAV, rate-sensitivity) so the model never does arithmetic itself
- [ ] Redis exact-match response cache (opt-in per feature) + a note on why semantic caching is risky (especially for numbers)
- [ ] Minimal streaming chat endpoint `POST /chat` (SSE) + bare chat page in Next.js, to get a vertical slice working end to end

**Proof:** a chat that streams, a `llm_calls` table with real costs, prompt files under version control, ADR-003 "LLM gateway & model routing".

---

## Phase 4 — RAG over financial documents (~30–35 h)

**Understand**
- [ ] Naive RAG vs advanced RAG; the common failure modes (bad chunking, tables split apart, wrong period, lost-in-the-middle, stale docs, no-answer cases)
- [ ] Dense vs sparse (BM25) vs **hybrid** retrieval; Reciprocal Rank Fusion; **reranking**
- [ ] Query transformation: rewriting, multi-query, HyDE, decomposition; contextual retrieval (chunk context prefixes such as "CICT FY2025 annual report, p.34")
- [ ] **Temporal correctness:** "latest" vs a specific period; filtering by period metadata
- [ ] HNSW vs IVFFlat indexes in pgvector; filtering with metadata
- [ ] **Permission-aware retrieval** (filter by user ACL *before* the LLM sees anything): information barriers make it a hard requirement
- [ ] Grounding & **page-level citations**; refusing when the context doesn't support an answer
- [ ] When RAG vs fine-tuning vs long context

**Build**
- [ ] Retriever: pgvector dense + Postgres full-text (BM25-like) → RRF → reranker (FlashRank/bge-reranker) → top-k, with security and period filters
- [ ] **Table-aware retrieval:** tables kept whole and also stored as structured rows; numeric questions prefer the metrics table over prose
- [ ] Metadata + **ACL filtering** by role and barrier group (an RM must never retrieve MNPI-flagged notes)
- [ ] Query rewriting with conversation history; multi-query for vague questions ("how is CICT doing?")
- [ ] Answer generation with inline **citations** (document, page, link to the PDF page) + a "not found in sources" path
- [ ] Freshness: report period shown in citations; re-index on new filings (from Phase 2)
- [ ] Build a **golden dataset now**: 50–100 Q&A pairs with expected source pages, including numeric questions, period traps ("FY2024 or FY2025?"), unanswerable questions and permission traps, stored in `evals/datasets/rag.jsonl`

**Proof:** retrieval metrics (recall@k, MRR) for naive vs hybrid vs hybrid+rerank, plus a demo of the same question answered differently for an analyst and an RM.

---

## Phase 5 — Agents: build the harness, then use a framework (~35–40 h)

**Understand**
- [ ] What an **agent harness** is: the loop (model → tool calls → execute → feed results back), stop conditions, max steps, token/time budgets, error recovery, context management
- [ ] Tool design: clear names/descriptions, narrow inputs, idempotency, useful error messages, pagination, returning *just enough*
- [ ] Workflows vs agents: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer, and **when not to use an agent**
- [ ] Memory: short-term (thread state), long-term (user/team facts, e.g. a PM's coverage), episodic; summarization/compaction of long sessions
- [ ] **Human-in-the-loop**: interrupts, approvals, resumable state (checkpointing); four-eyes in finance
- [ ] Text-to-SQL risks: injection, expensive queries, hallucinated columns, data leakage

**Build**
- [ ] **5a. Harness from scratch (~200 lines, no framework):** raw tool-use loop with max steps, per-run token budget, tool timeouts, structured tool errors, parallel tool calls, and tracing of each step. This is the piece you explain in interviews
- [ ] **5b. Quant agent:** text-to-SQL over the dbt **marts** only ("REITs with gearing > 40% and ICR < 3x", "fund exposure to industrial REITs", "1-year total return vs STI")
  - [ ] Schema retrieval (table/column descriptions from dbt docs) instead of dumping the whole schema
  - [ ] SQL validated with **sqlglot**: SELECT-only, allowed tables, `LIMIT` enforced, statement timeout, **read-only DB role**
  - [ ] Sandboxed Python for charts and calculations, e.g. "+50 bps SORA → DPU impact" from cost of debt and fixed-rate share (Docker sandbox or E2B free tier)
- [ ] **5c. Trade agent:** drafts a trade proposal with a cited rationale → **compliance check tool** (restricted list, mandate limits, concentration) → interrupt for **PM approval** (a different user) → submits the order to the PMS
- [ ] **5d. Port to LangGraph:** state graph, checkpointer (Postgres), interrupts for approvals, streaming of intermediate steps
- [ ] Conversation memory: thread history + summarization when over N tokens; long-term "my coverage / my funds" store
- [ ] Background job: a scheduled **morning brief** agent (Celery beat): overnight SGX announcements, price moves, rate changes for each PM's holdings

**Proof:** harness code + write-up "What a harness does", trace screenshot of a multi-step run, a trade proposal paused for PM approval.

---

## Phase 6 — MCP & Skills (~15–20 h)

**Understand**
- [ ] **MCP** architecture: host/client/server; tools, resources, prompts; transports (stdio vs Streamable HTTP); auth (OAuth) for remote servers
- [ ] Why MCP matters for integration: one adapter per system, reusable by any MCP-capable client (Claude Desktop, Claude Code, IDEs, your agent)
- [ ] MCP security: tool poisoning, over-broad permissions, confused deputy, prompt injection via tool results
- [ ] **Agent Skills:** packaged instructions + scripts + resources (`SKILL.md`) loaded on demand (progressive disclosure), and how they differ from tools and from MCP

**Build**
- [ ] `pms-mcp`: an MCP server wrapping the legacy PMS API (tools: `get_holdings`, `get_exposure`, `check_restricted`, `propose_order`; resources: policies; prompts: "review a fund's REIT exposure"). It also hides the legacy quirks (HTTP-200 errors, date formats, board lots) from AI clients
  - [ ] Streamable HTTP transport + token auth; per-tool scopes (read vs write)
  - [ ] Test it with MCP Inspector **and** connect it to Claude Desktop/Claude Code (big demo value: "your PMS now works in any MCP client")
- [ ] Refactor the Trade agent to consume tools **via MCP** instead of direct HTTP calls
- [ ] Also consume one third-party MCP server (e.g., filesystem, GitHub, or a broker's MCP on a **paper account, read-only**). Never put real holdings in this public repo
- [ ] **Skills registry** in ResearchPilot: `skills/reit-earnings-review/SKILL.md`, `skills/rate-sensitivity/`, `skills/morning-brief/`; the agent sees short descriptions and loads full instructions only when relevant
- [ ] Write one Claude Code skill for your own dev workflow (e.g., "add a new tool to the PMS MCP server") to show you use AI tooling well

**Proof:** a video of Claude Desktop using your PMS MCP server, the skills folder, ADR-004 "Direct tools vs MCP".

---

## Phase 7 — Multi-agent systems & Agent-to-Agent (A2A) (~20–25 h)

**Understand**
- [ ] Multi-agent patterns: supervisor/router, hierarchical, handoffs, swarm, debate/critic; costs (tokens × agents) and failure modes (loops, context loss between agents)
- [ ] **A2A protocol:** Agent Cards (discovery), tasks & lifecycle, messages/artifacts, streaming, push notifications, auth, and how it differs from MCP (agent↔agent vs agent↔tool)
- [ ] Cross-organization agent trust: auth, scoping, and not trusting another agent's output

**Build**
- [ ] **Research desk** (LangGraph supervisor): Filings, Quant, Macro/rates and News agents; shared state; handoff with context summaries; max-hop limit
- [ ] **Risk critic agent** (evaluator-optimizer): challenges each thesis ("what if occupancy falls?", "refinancing wall in 2027?") and checks every number is cited before the note is final
- [ ] `partner-agent`: a separate service simulating an **external data vendor's agent** (e.g. consensus estimates, built with a *different* framework such as PydanticAI or Google ADK, to prove interoperability)
- [ ] Expose it via **A2A** (Agent Card at `/.well-known/agent-card.json`); ResearchPilot discovers and calls it as an A2A client, including streaming status updates
- [ ] Treat vendor responses as **untrusted input** (schema validation + guardrails + source labelling)
- [ ] Compare one research note done by a single agent vs the research desk: quality, citation rate, latency, cost. Record it honestly (sometimes single wins)

**Proof:** sequence diagram of a research request across agents, comparison table, ADR-005 "When we use multi-agent".

---

## Phase 8 — Guardrails, safety, compliance (~20–25 h)

**Understand**
- [ ] **OWASP Top 10 for LLM Applications** (prompt injection, sensitive info disclosure, excessive agency, insecure output handling, supply chain, etc.)
- [ ] Direct vs **indirect prompt injection** (malicious text inside PDFs, announcements, news, tool results)
- [ ] Defense in depth: input filters, privilege separation, tool allowlists, output validation, HITL, monitoring. No single filter is enough
- [ ] Regulation: **FAA** (advice needs a licence), **MAS FEAT**, MAS AI risk-management expectations, **SFA** insider trading/MNPI, **PDPA**, IMDA GenAI framework

**Build**
- [ ] Guardrail pipeline as middleware with pluggable checks + per-team policy config:
  - [ ] Input: PII detection/redaction (Presidio + SG recognizers), injection/jailbreak classifier (LLM Guard or Llama Guard via Ollama), scope limits
  - [ ] **Advice guardrail:** detect personalised "should I buy X?" requests from non-licensed contexts → refuse and redirect; disclaimers on research output
  - [ ] Retrieval/tool results: scan for injected instructions and wrap them as data
  - [ ] Output: schema validation, PII leak check, **numeric groundedness check** (every number in the answer must match a cited source value), citation present for every claim
  - [ ] Tools: role-based allowlist, argument validation, rate limits, compliance check + PM approval required for any order
- [ ] **Information-barrier tests:** an RM or analyst outside the barrier group can never see MNPI notes, by search, by summary, or by clever prompting
- [ ] Plant **poisoned documents** (a fake announcement with hidden instructions) and prove they're neutralized
- [ ] **Red teaming** with promptfoo red-team plugins; save the report
- [ ] Audit log: who asked what, which sources/tools were used, which guardrails fired (immutable table; MAS expects record keeping)
- [ ] Threat model doc (`docs/threat-model.md`) with STRIDE-style table
- [ ] `docs/governance.md`: PDPA data inventory + mapping to MAS FEAT, MAS AI risk-management guidance and the IMDA GenAI framework

**Proof:** red-team report before/after, threat model, governance doc, guardrail-trigger stats on the dashboard.

---

## Phase 9 — Evaluation & observability (LLMOps) (~25–30 h)

**Understand**
- [ ] Why evals are the core of AI engineering: you can't improve or safely change what you don't measure
- [ ] Offline evals (golden sets, regression) vs online evals (user feedback, sampled LLM-as-judge on production traffic)
- [ ] Metrics: retrieval (recall@k, MRR, nDCG), generation (faithfulness, answer relevance, context precision), **numeric accuracy**, citation accuracy (right page), agents (task success, tool-call accuracy, steps, cost, latency), safety (attack success rate, advice-refusal rate)
- [ ] LLM-as-judge: rubric design, calibrating judges against human labels, judge bias
- [ ] Tracing: spans for retrieval/LLM/tool calls; p50/p95 latency; time-to-first-token

**Build**
- [ ] Langfuse integrated everywhere (traces per request, sessions, users, costs; prompt versions linked to traces)
- [ ] OpenTelemetry for non-LLM spans (DB, HTTP), structured JSON logs with `trace_id`
- [ ] Eval suites in `evals/`: RAG (Ragas/DeepEval), **numeric QA on REIT reports** (FinanceBench-style: exact match within tolerance), text-to-SQL (execution accuracy vs gold SQL), agent tasks (scenario tests with expected tool sequences), safety (red-team, advice refusal, information barrier)
- [ ] Run **Project Moonshot** (AI Verify Foundation) benchmarks + red-teaming against ResearchPilot; include the report
- [ ] **CI eval gate:** PRs that change prompts/retrieval/agents run a small eval subset; merge blocked if scores drop beyond a threshold (use a cheap judge model to stay in budget)
- [ ] Thumbs up/down + comment in the UI → Langfuse scores → bad answers flow into the golden dataset (data flywheel)
- [ ] Experiment log: at least 3 documented experiments (table parsing strategy, reranker on/off, model A vs B) with quality/cost/latency trade-offs

**Proof:** eval report table in the README (incl. numeric accuracy), CI eval gate screenshot, Langfuse dashboard screenshot.

---

## Phase 10 — Product UI: chat, dashboards, cost (~30–35 h)

**Understand**
- [ ] Streaming UX (SSE, AI SDK data stream protocol), optimistic UI, cancellation
- [ ] Generative UI: rendering tool results as components (metric cards, charts, trade proposals, approval dialogs)
- [ ] Designing trust into AI UX: citations, showing steps, confidence/uncertainty, easy feedback, undo

**Build**
- [ ] **Research chat:** streaming, markdown, inline **citations that open the PDF at the right page**, visible agent steps/tool calls (collapsible), stop/regenerate, conversation history, file upload (ask about a new report)
- [ ] **Approval inbox:** pending trade proposals with rationale, compliance result and approve/reject → resumes the graph
- [ ] **REIT dashboard:** comparison table and charts (yield vs gearing, P/NAV, ICR trend, debt maturity), sector view, SORA overlay + "Ask about this chart" button
- [ ] **Fund view:** holdings, exposure by sector/issuer, mandate limit usage
- [ ] **Morning brief page** from the Phase 5 background agent
- [ ] **Token & cost dashboard:** cost by day/model/feature/user/team, tokens in/out/cached, cache hit rate, p95 latency, error rate, **budgets** with progress bars, top expensive conversations (links to traces)
- [ ] **Quality & safety page:** eval scores over time, numeric accuracy, feedback rate, guardrail triggers
- [ ] **Admin:** users/roles/barrier groups, team settings (allowed models, budget limits, guardrail strictness), prompt versions in use, document sources + ingestion status
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
- [ ] Auth.js login (GitHub OAuth + credentials) → JWT → FastAPI dependency checks roles: `analyst`, `portfolio_manager`, `compliance`, `relationship_manager`, `admin`
- [ ] **Isolation:** each fund/client mandate and each **barrier group** enforced with **Postgres Row-Level Security**; prove an RM never sees another RM's clients or MNPI notes, even by asking the AI
- [ ] Optional: Keycloak in docker compose for enterprise SSO (OIDC) demo
- [ ] Redis rate limits (per user/team) + **token budget enforcement** (hard stop + friendly message)
- [ ] Idempotency keys on order endpoints (never submit an order twice); Celery for long jobs (ingestion, extraction, morning brief) with retries/dead-letter
- [ ] Circuit breaker + fallback model on provider errors; chaos test: kill the LLM provider and show graceful degradation
- [ ] Recorded-LLM fixtures (VCR-style) so unit/integration tests run free and deterministic in CI
- [ ] Load test with **k6** or Locust (mock LLM): find the bottleneck, document p95 at N concurrent users
- [ ] Security hygiene: secrets never in repo (gitleaks in pre-commit), dependency scanning (Dependabot/Trivy), CORS, security headers

**Proof:** RLS / information-barrier isolation tests, load test report, chaos test write-up.

---

## Phase 12 — Containers & CI/CD (~15–20 h)

**Understand**
- [ ] Docker layers & caching, multi-stage builds, slim/distroless images, non-root users, healthchecks
- [ ] CI vs CD; environments (dev/staging/prod); trunk-based development; semantic versioning; rollbacks
- [ ] Database migrations in pipelines (Alembic) and zero-downtime concerns

**Build**
- [ ] Production Dockerfiles for api, legacy-pms, pms-mcp, partner-agent, worker, dagster (multi-stage, non-root, healthcheck, < 300 MB where possible)
- [ ] `docker-compose.yml` (dev) + `docker-compose.prod.yml`; one command spins up the **entire** system with seed data
- [ ] **GitHub Actions:** lint → typecheck → unit tests → build images → **Trivy scan** → eval gate (on AI changes) → push to GHCR/ECR → deploy staging → manual approval → prod
- [ ] **Jenkins:** run Jenkins in Docker locally; write a `Jenkinsfile` with the same stages (declarative pipeline, credentials binding, parallel stages). Banks still use Jenkins heavily, so be able to talk about it
- [ ] Preview deployments on Vercel for every PR

**Proof:** pipeline screenshots (GHA + Jenkins), image sizes, one-command local setup in the README.

---

## Phase 13 — Cloud deployment (~20–25 h)

**Understand**
- [ ] AWS core: IAM (roles, least privilege), VPC/subnets/security groups, ECR, ECS Fargate, ALB, RDS, ElastiCache, S3, Secrets Manager, CloudWatch; and what costs money while idle
- [ ] **Infrastructure as Code** with Terraform: state, modules, plan/apply, remote state, environments
- [ ] Managed AI services: Amazon Bedrock (Claude on AWS), why regulated firms use it (VPC, compliance, billing, data residency)
- [ ] **MAS TRM** basics: access control, encryption at rest/in transit, logging, backup/recovery, change management
- [ ] Serverless vs containers trade-offs for streaming AI workloads

**Build**
- [ ] **Always-on cheap stack (the public demo):** Vercel (web) + Render/Fly.io (API, MCP, partner agent) + Neon (Postgres+pgvector) + Upstash (Redis) + Langfuse Cloud
- [ ] **AWS stack via Terraform** in `infra/terraform/`, region **ap-southeast-1 (Singapore)**: ECR, ECS Fargate services, ALB, RDS Postgres (or Neon to save cost), S3 for filings (ingestion trigger), Secrets Manager, CloudWatch logs/alarms, IAM roles per service, encryption on
  - [ ] `terraform apply` → record demo/screenshots → `terraform destroy`; document cost per hour
  - [ ] Optional: switch one model route to **Bedrock** through LiteLLM for the "data stays in Singapore" path (check in-region model availability)
- [ ] GitHub Actions → AWS via **OIDC** (no long-lived keys)
- [ ] Monitoring: uptime check (free tier, e.g., Better Stack/UptimeRobot), alerts on error rate and daily LLM spend
- [ ] Runbook (`docs/runbook.md`): deploy, rollback, rotate secrets, re-index filings, handle LLM provider outage, restore from backup

**Proof:** live URL, Terraform code, AWS architecture diagram, runbook.

---

## Phase 14 — Optional advanced (pick what matches target jobs)

- [ ] **Backtesting:** a simple dividend/quality strategy over the universe with vectorbt; the agent explains results and their limits (look-ahead bias, survivorship bias)
- [ ] **GraphRAG** / knowledge graph: sponsors → REITs → properties → tenants (e.g. "which REITs share a sponsor or a major tenant?")
- [ ] **Earnings-call / results-briefing** transcripts: speech-to-text + summarization
- [ ] **Fine-tuning:** LoRA fine-tune a small open model (Colab/Kaggle free GPU) for metric extraction; compare with prompting a large model on cost/latency/accuracy
- [ ] **Local/private deployment:** run the full stack with Ollama/vLLM only ("our data can't leave the building", common at banks)
- [ ] **Kubernetes:** kind/k3d locally, Helm chart for the API + worker, HPA, readiness/liveness probes (EKS concepts)
- [ ] **Streaming data:** Redpanda/Kafka for announcements and price events instead of polling

---

## Phase 15 — Package it for the job hunt (~15–20 h, don't skip)

- [ ] **README** as a case study: problem → architecture diagram → demo GIF/video → key decisions (link the ADRs) → **eval results (numeric accuracy!)** → cost per research note → security & governance → what you'd do next
- [ ] `docs/architecture.md` with C4-style diagrams (context, container, component)
- [ ] 3–5 min demo video (Loom): business story first, tech second
- [ ] **FDE artifacts:** discovery doc (Phase 1), integration playbook ("how to deploy ResearchPilot at a new asset manager in 2 weeks"), customer-facing summary of a pilot's ROI
- [ ] 2–3 blog posts / LinkedIn write-ups (e.g., "Citing the right page: RAG over REIT annual reports", "Building an agent harness from scratch", "Information barriers for AI agents", "Mapping an AI copilot to MAS FEAT")
- [ ] Resume bullets with numbers (e.g., "table-aware retrieval raised numeric accuracy on REIT reports from 71% → 94% while cutting cost per answer 40% via prompt caching")
- [ ] **Singapore target list** (`docs/target-companies.md`): banks (DBS, OCBC, UOB, foreign banks' Singapore hubs), asset managers and wealth (GIC, Temasek, Eastspring, Lion Global, Fullerton, Endowus, Syfe, StashAway), exchanges and data (SGX, Bloomberg, LSEG, S&P), regulators (MAS), GovTech, AI vendors and consultancies. Use MyCareersFuture and LinkedIn; consider AI Singapore's **AIAP**
- [ ] Interview prep: be able to whiteboard any part of this system and answer:
  - [ ] Design a RAG system over 10M financial documents with per-user permissions and information barriers
  - [ ] How do you make sure every number the AI states is correct?
  - [ ] How do you evaluate and safely ship a prompt change?
  - [ ] An agent is looping and burning tokens: how do you detect it and prevent it?
  - [ ] How do you defend against indirect prompt injection (e.g., a poisoned announcement)?
  - [ ] Cut LLM cost by 50% without hurting quality: what do you try, in what order?
  - [ ] RAG vs fine-tuning vs long context: when do you pick each?
  - [ ] MCP vs A2A vs plain function calling
  - [ ] A PM says "the AI is wrong": walk through your debugging process (traces → retrieval → prompt → model)
  - [ ] How would you deploy this at a Singapore bank (PDPA, MAS TRM, data residency, model risk management)?
  - [ ] Where does an AI research tool end and regulated financial advice begin?

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
- FinanceBench paper and dataset (numeric QA over financial filings)
- **Singapore & finance:** MAS (FEAT principles, Veritas, Project MindForge, AI model risk management papers, TRM guidelines, Code on CIS property funds appendix) · PDPC (PDPA + NRIC advisory guidelines) · IMDA Model AI Governance Framework for GenAI · AI Verify Foundation (Project Moonshot) · SGX investor education on REITs · REIT Association of Singapore (REITAS) · data.gov.sg and SingStat API docs

---

## Progress Log

| Date | Phase / item | Notes (what I learned, blockers, decisions) |
|---|---|---|
| 2026-10-10 | Roadmap created | Starting Phase 0 |
| 2026-10-11 | P0: monorepo, tooling, docker compose | Walking skeleton runs: web → api health, Postgres(pgvector) + Redis. CI workflow written (runs once pushed). Next.js is v16.4: read `node_modules/next/dist/docs` before using new APIs. |
| 2026-10-11 | P0: GitHub Actions CI | Repo pushed to github.com/Yong-Ching/opspilot, CI green (api/web/docker). Note: `astral-sh/setup-uv` has no major tags, so pin the full version. |
| 2026-10-11 | P0: API keys + local models | Anthropic + Gemini keys verified (in gitignored apps/api/.env). Ollama: `qwen3:4b-instruct` (~45 tok/s on M3 Pro) + `nomic-embed-text` (768-dim). Lesson: the `qwen3:4b` thinking variant used 365 output tokens for a 1-sentence answer vs 34 for instruct, so watch hidden reasoning tokens in cost estimates. Pending: confirm Anthropic spend limit. |
| 2026-10-11 | P0: Vercel + keys | Vercel production deploy succeeded (root dir `apps/web`, auto-deploys on push). Keys rotated + spend limit set. Started job research (4 postings). |
| 2026-10-11 | P0 quiz (4 Qs) | Strong instincts, but stops before the why and the numbers. Practise: (1) finish calculations, cost/month = per-request × volume × 30; (2) find the biggest cost before optimizing (prompt caching beats prompt summarizing); (3) temperature 0 ≠ no hallucination; prevent it with grounding, citations, groundedness checks and evals; (4) FDE: measure first and pick tools after. Live demo: https://opspilot-virid.vercel.app |
| 2026-10-14 | P1: Olist + legacy OMS | 99k orders loaded (13 s, COPY). Data tails off with stray canceled orders: loader finds the last day with ≥10 orders, trims after it, shifts dates so it lands on 2026-10-10. Learned: psycopg rejects f-string SQL (injection protection); use `sql.SQL`/`sql.Identifier`. Quirks documented in apps/legacy-oms/README.md. Next: outbox (yours). |
| 2026-10-15 | Domain → Singapore last-mile courier | Switched from generic e-commerce to **Lion City Express (LCX)**, a Singapore courier. Olist data is kept but will be localised (addresses, SGD, 1–3 day SLAs, translated feedback). Added the Singapore layer (PDPA, NRIC, SEA-LION, LionGuard, IMDA, Moonshot, LTA/NEA live data, ap-southeast-1). Phase 1 code to be reworked into `legacy-dms`; outbox task unchanged. |
| 2026-10-15 | Domain → investment research (final) | Switched from the courier idea to **ResearchPilot**: an enterprise research copilot for *Harbourfront Capital*, a fictional Singapore asset manager, covering ~15 S-REITs + ~10 STI blue chips. Legacy system becomes a PMS (funds, holdings, mandates, restricted list, order blotter); Olist data dropped, code structure reused. Finance layer added: FAA (no retail advice), MAS FEAT / AI risk / TRM, MNPI information barriers, numeric groundedness, PDPA. Outbox task unchanged (new event names). |
| 2026-10-15 | P1: coverage universe | `data/universe.csv`: 15 S-REITs (7 sectors, incl. a USD-quoted REIT) + 10 STI blue chips, all verified against live Yahoo data (`data/scripts/verify_universe.py`). Lessons: ESR-REIT's code changed J91U → 9A4U (so the PMS needs internal security IDs + identifier history); several IR sites block non-browser user agents; sponsors (CapitaLand, Mapletree, Frasers, Keppel) link REITs to blue chips, useful for GraphRAG later. |
| 2026-10-15 | P1: legacy PMS | `apps/legacy-pms` replaces the OMS. Real prices/dividends/FX for 25 names (`make market-data`, not committed) + synthetic firm: 9 staff, 40 clients, 5 funds, 1.6k trades simulated at real closes. Bug found: buys drained cash to 0 because overweights inside the tolerance band weren't sold, so redemptions went negative. Fixed with a cash reserve + full rebalance when below it. Lesson: always check invariants (cash ≥ 0, limits) on generated data. Order workflow: board lots, restricted list, four-eyes. 28 tests on synthetic fixtures. |
