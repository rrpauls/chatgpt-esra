# chatgpt-esra

A compact ChatGPT and Codex adaptation of **ESRA — Evolutionary Self-Recursive Architecture**.

This repository consolidates the original Hermes-oriented implementation into five task-scoped skills. It improves decision discipline, experiment design, evidence integration, and incident response without assuming background hooks, persistent memory, or model retraining.

## Design goals

- Keep routine work lightweight.
- Activate one focused skill when it is sufficient.
- Reserve a full ESRA review for major changes, repeated failures, or an explicit request.
- Base lessons on observable evidence.
- Stop recursive reviews and unbounded self-improvement loops.
- Respect the host's authorization, storage, and skill-management rules.

## Skills

| Skill | Use it for |
|---|---|
| `esra-orchestrator` | One bounded review after consequential work |
| `esra-decisions` | OODA, trade-offs, and system feedback |
| `esra-experiments` | Baselines, comparisons, guardrails, and rollback |
| `esra-reflection` | Evidence-backed lessons and cycle audits |
| `esra-crisis` | Incident containment, recovery, and resilience |

## Activation model

```text
Routine task                -> no ESRA skill
One difficult decision      -> one focused skill
Major change/repeated fault -> one bounded orchestrator cycle
Active incident             -> crisis handling first
```

The skills may be selected implicitly when their descriptions match a task or explicitly by name. The full cycle is not a background process and does not run after every response.

## Install in Codex

Using the built-in skill installer:

```text
$skill-installer Install these skills from rrpauls/chatgpt-esra:
skills/esra-orchestrator
skills/esra-decisions
skills/esra-experiments
skills/esra-reflection
skills/esra-crisis
```

Or use the installer helper directly:

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo rrpauls/chatgpt-esra \
  --path skills/esra-orchestrator \
         skills/esra-decisions \
         skills/esra-experiments \
         skills/esra-reflection \
         skills/esra-crisis
```

Restart Codex if the new skills do not appear immediately. Each destination directory must not already exist; remove or rename an older installation intentionally before reinstalling.

## Validate locally

No third-party Python packages are required:

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
```

## What changed from hermes-esra

- 15 overlapping skills became 5 focused skills.
- Hermes-only paths, runtime tools, and automatic hooks were removed.
- Full-chain activation became selective routing.
- Reviews are limited to one per primary task and cannot trigger further reviews.
- Persistent history is used only when an authorized record actually exists.
- Token savings are not claimed from file size alone; measure them in comparable runs.

## Relationship to ESRA

- [rrpauls/esra](https://github.com/rrpauls/esra) — architecture and principles.
- [rrpauls/hermes-esra](https://github.com/rrpauls/hermes-esra) — Hermes implementation.
- `rrpauls/chatgpt-esra` — ChatGPT and Codex adaptation.

Derived from `rrpauls/hermes-esra` and released under the MIT License.
