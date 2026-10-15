# ResearchPilot

[![CI](https://github.com/Yong-Ching/opspilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Yong-Ching/opspilot/actions/workflows/ci.yml)

AI research copilot for the investment team of **Harbourfront Capital**, a fictional Singapore asset manager,
covering Singapore REITs and STI blue chips. It plugs into the firm's existing Portfolio Management System and answers
from REIT reports and market data with page-level citations. Trade proposals pass compliance checks and portfolio
manager approval, and cost, numeric accuracy and safety are all measured.

**Live demo:** https://opspilot-virid.vercel.app

> 🚧 Under active development. See [ROADMAP.md](ROADMAP.md) for the plan and progress.

## Quick start

```bash
make install   # uv sync, pnpm install, pre-commit hooks
make up        # whole stack in Docker → web :3000, api :8000
# or, for hot reload:
make infra && make api   # terminal 1
make web                 # terminal 2
```

## Repo layout
| Path | What |
|---|---|
| `apps/api` | ResearchPilot AI backend (FastAPI) |
| `apps/web` | Dashboard & chat UI (Next.js) |
| `apps/legacy-oms` | Simulated existing system (being reworked into the legacy PMS) |
| `apps/partner-agent` | External data vendor's agent (A2A) |
| `mcp/pms-mcp` | MCP server wrapping the legacy PMS |
| `data/` | Ingestion pipelines (filings, market data), dbt models |
| `evals/` | Eval datasets & suites |
| `infra/` | Docker, Terraform, Jenkins |
| `docs/adr/` | Architecture decision records |
