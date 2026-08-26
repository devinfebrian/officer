# Workflow

- Prefers to handle git commit and push themselves rather than delegating version control to the agent — after finishing a feature they commit/push on their own and expect the agent to proceed to the next task (e.g., "i already commit and push, plan s2"). Confidence: 0.7

- Prefers test-first TDD in small vertical slices: write the failing test, confirm it's red, implement just enough to go green, then move to the next seam — each slice pairs one test with one implementation unit. Confidence: 0.8

- Prefers empirically probing framework/library behavior with a throwaway scratchpad script before committing to a design or wiring decision (e.g., confirming LangGraph conditional-edge routing and dict-merge semantics before rewriting the orchestrator). Confidence: 0.8
