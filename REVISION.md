# Revision Notes: my weak spots

Short notes from quizzes. Re-read these before interviews.

## Habits to fix
- Finish with the **actual number**, not just the formula.
- Explain **why**, not just what. Name the idea, then the reason.

## Phase 0 (2026-10-11)

**Cost math**
- Monthly cost = cost per request × requests per day × **30**. Don't forget the ×30.
- Optimize the **biggest** cost first. Break it down before guessing "about 30%".
- A large repeated system prompt → **prompt caching** (~90% cheaper on repeat reads). Summarizing a 50-token user question saves almost nothing.
- Chat history is re-sent every turn, so later questions in a chat cost more.

**Embeddings**
- An embedding is **one vector** (list of numbers), not a matrix: coordinates on a "map of meaning".
- IDs like `#A-48213` have no meaning to embed, so a near-identical ID could be returned. Use exact lookup or keyword search; production uses **hybrid**.
- Changing embedding model = **re-embed everything** (migration cost).

**AI Engineer vs FDE**
- AI Engineer ≠ infrastructure (that's MLOps). An AI Engineer makes the AI system *good*; an FDE makes it *succeed at one customer*.
- First 2 weeks at a customer: talk to real users → agree a metric and measure today's number → get data access and security review → prototype on real data → *then* choose architecture and tools.

**LLM behavior**
- Answers vary because the model **samples** the next token from probabilities. Temperature reshapes them. Policy bot: **0–0.3**.
- **Temperature 0 does not stop hallucination.** It just repeats the same wrong answer.
- Main cause of hallucination: the right document wasn't retrieved, or the model fell back on "plausible" training knowledge.
- Prevent it **in the system**, not the prompt: retrieval with citations, a groundedness check, exact facts from structured data, evals.
