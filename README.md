# OpsPilot

[![CI](https://github.com/Yong-Ching/opspilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Yong-Ching/opspilot/actions/workflows/ci.yml)

AI operations copilot for **Acme Market**, a fictional e-commerce company. It's built on top of their existing
order management system: answers grounded in policy docs, analysis of business data, and agent actions with
human approval, all with cost, quality and safety tracked.

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
| `apps/api` | OpsPilot AI backend (FastAPI) |
| `apps/web` | Dashboard & chat UI (Next.js) |
| `apps/legacy-oms` | Simulated existing order management system |
| `apps/partner-agent` | Third-party logistics agent (A2A) |
| `mcp/oms-mcp` | MCP server wrapping the legacy OMS |
| `data/` | Ingestion pipelines, dbt models |
| `evals/` | Eval datasets & suites |
| `infra/` | Docker, Terraform, Jenkins |
| `docs/adr/` | Architecture decision records |
