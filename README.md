# Evolutionary Self-Recursive Architecture for OpenAI

<p align="center">
  <img src="assets/logo-openai.png" alt="Evolutionary Self-Recursive Architecture for OpenAI logo" width="240"/>
</p>

<p align="center">
  <strong>OpenAI platform implementation of ESRA for ChatGPT and Codex</strong>
</p>

<p align="center">
  Focused skills and a privacy-preserving runtime for systematic, value-aligned, auditable improvement cycles.
</p>

<p align="center">
  <a href="https://github.com/rrpauls/esra">ESRA specification</a> ·
  <a href="https://github.com/rrpauls/hermes-esra">Hermes Agent implementation</a> ·
  <a href="https://github.com/rrpauls/claude-esra">Claude implementation</a> ·
  <a href="docs/HERMES_PARITY.md">Hermes parity</a> ·
  <a href="docs/RUNTIME.md">Runtime guide</a> ·
  <a href="LICENSE">MIT License</a>
</p>

---

## What this is

ChatGPT ESRA is a portable ChatGPT/Codex implementation that preserves the functional coverage of [hermes-esra](https://github.com/rrpauls/hermes-esra) while using Codex-native skills, plugin packaging, lifecycle hooks, and local data paths.

The repository intentionally consolidates fifteen overlapping Hermes skills into five selective skills. This reduces prompt overhead without removing the underlying decision, experiment, reflection, crisis, or orchestration methods.

## What is included

| Layer | Components | Purpose |
|---|---|---|
| Shared skill layer | `esra-orchestrator`, `esra-decisions`, `esra-experiments`, `esra-reflection`, `esra-crisis` | On-demand reasoning workflows for ChatGPT and Codex |
| Codex runtime | `scripts/esra_runtime.py` | Triggers, evidence logs, metrics, experiments, audits, validation, and oversight artifacts |
| Lifecycle adapter | `hooks/hooks.json`, `scripts/esra_hook.py` | Privacy-preserving task/session counters using Codex hooks |
| Distribution | `plugin.json`, `.codex-plugin/plugin.json`, per-skill `agents/openai.yaml` | Portable plugin metadata and user-facing skill metadata |

See [Hermes parity](docs/HERMES_PARITY.md) for the complete component mapping and [runtime guide](docs/RUNTIME.md) for commands and safeguards.

## Install

The five skill folders follow the shared Agent Skills format. For a simple user-scoped skill install:

```text
$skill-installer install every skill from https://github.com/rrpauls/chatgpt-esra/tree/main/skills for my user scope
```

For the complete Codex integration, install the repository as a plugin so Codex also discovers its runtime hook. Plugin hooks require explicit review and trust in Codex; use `/hooks` to inspect or disable them.

The runtime is also usable directly from a clone and has no third-party dependencies:

```bash
python3 scripts/esra_runtime.py --data-dir /tmp/esra-demo dashboard
python3 scripts/esra_runtime.py --data-dir /tmp/esra-demo trigger --major-change --new-skill
python3 scripts/esra_runtime.py --data-dir /tmp/esra-demo validate skills
```

Data goes to `PLUGIN_DATA` when run by an installed plugin, `ESRA_DATA_DIR` when explicitly configured, or `~/.codex/esra` for direct local use. No Hermes installation or Hermes path is required.

## Operational guarantees

- Skills activate selectively; routine tasks do not automatically run a full ESRA cycle.
- A trigger recommendation never executes a review or modifies a skill.
- Experiments run only commands explicitly supplied by the user and never auto-promote results.
- Hooks store timestamps, event types, hashed task identifiers, and the workspace basename—not prompt or transcript content.
- Runtime records use private local permissions and reject symlinked state targets.
- Human review artifacts recommend a branch and verification plan but do not create issues, branches, commits, or pull requests.

## Development

Python 3.11+ is recommended.

```bash
python3 scripts/validate_skills.py
python3 scripts/esra_runtime.py --data-dir /tmp/esra-test validate skills
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py
```

CI runs the same validation on pushes and pull requests.

## Repository relationship

| Repository | Role |
|---|---|
| [rrpauls/esra](https://github.com/rrpauls/esra) | Architecture specification |
| [rrpauls/hermes-esra](https://github.com/rrpauls/hermes-esra) | Hermes-specific implementation and provenance source |
| **rrpauls/chatgpt-esra** | Shared ChatGPT/Codex implementation |
| [rrpauls/claude-esra](https://github.com/rrpauls/claude-esra) | Claude implementation |

A separate `codex-esra` fork is unnecessary while Codex-specific behavior fits cleanly behind this repository's plugin/runtime boundary. Fork only if the Codex runtime later needs an incompatible release cadence or architecture.

## License

MIT. The adapted material retains provenance notices in each skill.

OpenAI, ChatGPT, and the Blossom logo are trademarks of OpenAI. This independent project is not endorsed or sponsored by OpenAI. Logo use is subject to the [OpenAI brand guidelines](https://openai.com/brand/).
