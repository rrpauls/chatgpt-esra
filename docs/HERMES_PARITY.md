# Hermes ESRA functional parity

This implementation targets behavioral parity with `rrpauls/hermes-esra` at upstream commit `3de5ab69715908e1f16033722f6aca808fc6d735`. Parity means preserving useful outcomes and safeguards, not copying Hermes-specific paths, automatic assumptions, or class names.

## Skill coverage

| Hermes skill | ChatGPT/Codex equivalent |
|---|---|
| `hermes-evolution-orchestrator` | `esra-orchestrator` |
| `esra-runtime` | `esra-orchestrator` plus `docs/RUNTIME.md` |
| `ooda-framework` | `esra-decisions` |
| `value-clarifier` | `esra-decisions` and the experiment value-alignment gate |
| `optimizer-philosopher` | `esra-decisions` |
| `system-dynamics-thinker` | `esra-decisions` |
| `self-observer` | `esra-reflection` using observable evidence only |
| `self-improver` | `esra-reflection` plus `esra-experiments` |
| `mental-model-updater` | `esra-reflection` revised-working-rule method |
| `loop-auditor` | `esra-reflection` audit mode and runtime `audit` |
| `experimenter` | `esra-experiments` plus runtime `experiment` |
| `antifragility-builder` | `esra-crisis` resilience/fault-test method |
| `crisis-manager` | `esra-crisis` |
| `hermes-codebase-engineer` | Codex's native repository workflow; ESRA applies selectively |
| `github-actions-integrator` | Codex's native GitHub workflow; repository CI validates ESRA |

The consolidation is intentional: ChatGPT and Codex initially discover skill metadata, then load a skill body only when relevant. Five narrower entry points reduce ambiguity and metadata/body overhead while retaining all methods.

## Runtime coverage

| Hermes component | ChatGPT/Codex implementation | Notes |
|---|---|---|
| `evolution_hook.py` | runtime `trigger`; plugin lifecycle hook | Scoring and rate limits recommend one cycle; never auto-executes it |
| `esra_logger.py` | private `events.jsonl` | Concise evidence and lifecycle records |
| `evolution_dashboard.py` | runtime `dashboard` | Event, outcome, and recency summary |
| `baseline_metrics.py` | runtime `baseline` | Named numeric KPI snapshots |
| `skill_validator.py` | `validate_skills.py`, runtime `validate`, plugin validators | Frontmatter, identity, size, symlink, packaging checks |
| `experiment_runner.py` | runtime `experiment` | Canary, staged, A/B, stress, timeout, stop-on-failure, explicit decision |
| `hermes_integration.py` | Codex plugin discovery, hook adapter, five skill routes | Native plugin installation replaces manual skill injection |
| `human_oversight.py` | runtime `oversight` plus normal Codex/GitHub workflow | Produces review artifact and branch suggestion; external mutation stays explicit |
| `esra_paths.py` | `--data-dir`, `ESRA_DATA_DIR`, `PLUGIN_DATA`, safe path helpers | No dependency on a Hermes home directory |

## Deliberate host adaptations

- Automatic post-task evolution becomes a non-steering lifecycle record plus a bounded trigger recommendation. This prevents recursive turns and surprise scope expansion.
- Self-observation is limited to observable task evidence. The skills make no claims about hidden mental state or model-weight learning.
- Skill injection becomes plugin installation and native discovery. Duplicate same-name skills are not merged.
- GitHub issues, branches, and pull requests remain normal authorized Codex actions rather than side effects of a runtime helper.
- Runtime logs do not retain prompt or transcript content.

These adaptations retain the operational purpose of each Hermes component while following ChatGPT/Codex permission, plugin, progressive-disclosure, and hook models.
