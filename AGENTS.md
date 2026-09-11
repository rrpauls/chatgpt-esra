# AGENTS.md

## Purpose

Apply ESRA selectively in this repository.

## Working rules

- Do not invoke ESRA for routine questions, simple edits, or ordinary successful tests.
- Use one focused skill for a single difficult decision, experiment, reflection, or incident.
- Use `esra-orchestrator` only after a major architecture or skill change, repeated failure, or an explicit full-cycle request.
- Allow at most one ESRA review per primary task. A review, log, or audit must never trigger another review.
- Separate observations from assumptions and unsupported claims.
- Do not assume background execution, cross-session memory, model-weight updates, production access, or Hermes runtime paths.
- Execute only within the user's authorization. Prefer bounded tests with observable success criteria and rollback.
- If recorded cycle history is unavailable, report audit cadence as unknown.

## Verification

Run:

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
```
