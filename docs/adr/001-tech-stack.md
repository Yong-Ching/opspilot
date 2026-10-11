# ADR-001: Core tech stack

- **Status:** Draft. *You fill in the reasoning.*
- **Date:** 2026-10-11

## Context
OpsPilot adds AI to an existing e-commerce company's systems. Constraints: ≤ $20/month, one developer,
must look and behave like an enterprise system, must use technologies that appear in AI Engineer / FDE job postings.

## Options considered
<!-- TODO(you): for each layer, write 1–2 alternatives and why you did or didn't pick them.
     Use docs/job-keywords.md as evidence: "appears in N of 10 job postings". -->

| Layer | Chosen | Alternatives | Why (your words) |
|---|---|---|---|
| Backend | FastAPI (Python) | Django, Node/Express | |
| Frontend | Next.js + TypeScript | Vite SPA, Streamlit | |
| Database / vectors | Postgres + pgvector | Pinecone, Qdrant | |
| Cache / queue | Redis + Celery | SQS, Kafka | |
| Package mgmt | uv / pnpm workspace | poetry, npm | |
| CI | GitHub Actions (+ Jenkins later) | GitLab CI | |

## Decision
<!-- TODO(you) -->

## Consequences
<!-- TODO(you): e.g. "One database for relational + vectors keeps ops simple and free, but we may need a
     dedicated vector DB beyond ~10M chunks." -->
