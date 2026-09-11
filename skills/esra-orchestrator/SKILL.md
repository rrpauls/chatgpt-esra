---
name: esra-orchestrator
description: Run bounded ESRA reviews after major architecture or skill changes, repeated failures, or an explicit full-cycle request. Skip routine work.
---

# ESRA Orchestrator
Adapt ESRA (Evolutionary Self-Recursive Architecture) to Codex as a task-scoped workflow, not a background service or model-training mechanism.

## Route by need
- Routine answers, simple edits, and successful ordinary tests: stop without an ESRA cycle.
- One difficult decision or hypothesis: use only the relevant focused skill.
- Major architecture/skill changes, repeated failures, or explicit full-cycle requests: run one bounded review after the primary task. Task length alone is not a trigger.
- An active incident takes priority over retrospective work.

## One cycle
1. Observe the actual result: tests, tool output, user feedback, and missing evidence. Separate completed work from proposals.
2. Orient around the user's objective, constraints, and the highest-impact mismatch.
3. Decide on at most two improvements with observable success criteria. Check scope and value alignment before experiments.
4. Act only within the current authorization. For an analysis request, propose changes; do not implement them. For implementation, verify the selected change and summarize the result.
5. Close with one lesson and the evidence needed to revisit it. If blocked or inconclusive, say so; do not manufacture progress.

Load only a specialist that is genuinely needed: esra-decisions for trade-offs, esra-experiments for comparisons, esra-reflection for evidence integration, esra-crisis for incidents. Resolve names in the host's current catalog; if absent, apply the relevant step directly. Do not require all four, delegate by default, or invoke legacy Hermes skills.

## Bounds and persistence
Never let an ESRA review, log entry, or audit trigger another cycle. Allow one review per primary task; stop when evidence is exhausted or the agreed test budget is reached. Ask before expanding scope.
No Hermes paths, services, memory APIs, or automatic post-task hooks are assumed. A trigger script's recommendation is not an executed review.
Use an existing authorized project record when available. Save only concise evidence-backed conclusions, not private deliberations, secrets, full transcripts, or invented emotional states. Skill changes use the host's supported skill-management process.
Audit after 5-10 recorded significant cycles or an explicit request. Count only accessible completed records since the last audit; if history is missing, report the cadence as unknown. This is task-time review, not scheduling.
Keep the user-facing closeout brief: outcome, evidence, improvement, remaining uncertainty. Do not enforce ceremonial headings.

Derived from rrpauls/hermes-esra (MIT), adapted for Codex.
