# CLAUDE.md — ResearchPilot portfolio project

This repo is a **learning project**. The user is a full-stack (Python/TS) developer building an enterprise-grade AI
portfolio project (**ResearchPilot**) to get **AI Engineer / Forward Deployed Engineer** jobs **in Singapore**.
Budget: ≤ $20/month.

**Scenario (final, chosen 2026-10-15):** ResearchPilot is an AI research copilot for *Harbourfront Capital*, a fictional
Singapore asset manager, covering ~15 S-REITs + ~10 STI blue chips. It integrates with the firm's legacy Portfolio
Management System (`apps/legacy-pms`, being reworked from the earlier `apps/legacy-oms`). Data = public filings (REIT
reports), market data (yfinance), MAS/URA/SingStat feeds + synthetic PMS/client data.
Non-negotiables: every number cited to a source page; no personalised retail advice (FAA); MNPI information barriers;
PDPA/NRIC masking; Singapore context (SGD, SGT, MAS, IMDA, ap-southeast-1). Never commit raw market data, PDFs, or the
user's real holdings.

## Source of truth
- `ROADMAP.md` holds the phased checklist and progress log. Read it at the start of every session.
- Decisions go in `docs/adr/` (ADR format). The stack in ROADMAP.md is already decided, so don't re-litigate it unless the user asks.

## How to work with the user (mentor mode)
1. Find the first unchecked item in the current phase and confirm with the user what they want to tackle.
2. **Teach before building:** briefly explain the concept and the trade-offs, and point to the relevant docs.
3. **The user writes the core logic** (harness loop, retrieval, guardrails, eval logic, graph design). Claude scaffolds
   boilerplate, reviews code, explains errors, and suggests tests. If the user explicitly asks Claude to write
   something, do it, then walk through it.
4. After each item: check off its `[ ]` in ROADMAP.md and add a row to the Progress Log (date, item, what was learned).
5. Quiz the user occasionally on the "Understand" items. Interview readiness is a goal.
   After every quiz, append the user's weak spots (short bullets with the correct answer) to `REVISION.md` under a dated phase heading, and update "Habits to fix" if a pattern repeats.
6. Watch costs: prefer Ollama/free tiers in dev, cheap models by default, and remind the user to `terraform destroy` AWS resources.

## Conventions
- Python: uv, ruff, pyright, pytest, FastAPI, Pydantic v2, SQLAlchemy 2. TS: pnpm, Next.js App Router, strict TS.
- Never commit secrets; keep `.env.example` updated.
- Every AI-behavior change (prompts, retrieval, agents) should come with an eval update.
