# Codex runtime

`scripts/esra_runtime.py` is the dependency-free operational layer behind the five skills. It replaces Hermes-specific paths and integration code with explicit, inspectable local commands.

## State and privacy

State resolution order:

1. `--data-dir`
2. `ESRA_DATA_DIR`
3. `PLUGIN_DATA` supplied by Codex for an installed plugin
4. `~/.codex/esra`

State directories are private (`0700`) and generated files are private (`0600`) where the operating system supports POSIX permissions. The runtime refuses symlinked state files and directories. Lifecycle hooks discard prompts, transcript paths, tool input, and raw session/turn identifiers.

The event log rotates at 5 MiB by default and retains one prior segment. Set `ESRA_MAX_LOG_BYTES` to a positive byte count to change that bound. Named baselines retain up to 99 earlier snapshots.

## Commands

### Trigger recommendation

```bash
python3 scripts/esra_runtime.py trigger \
  --complexity 8 --major-change --new-skill --confidence 0.6
```

The result is only a recommendation. Rate limits default to one recommendation per supplied session and three per UTC day. `--explicit` models a direct user request; `--force` bypasses only the rate limit.

### Record a completed cycle

```bash
python3 scripts/esra_runtime.py record \
  --task plugin-port \
  --outcome success \
  --evidence "validator passed" \
  --change "use a plugin hook instead of a Hermes post-task hook" \
  --verification "unit tests and isolated hook test passed"
```

Store concise evidence pointers, never secrets, full transcripts, or hidden deliberation.

### Portable ESRA 1.2 export

```bash
python3 scripts/esra_export.py \
  --data-dir ~/.codex/esra --output /tmp/esra-events.jsonl
```

The read-only exporter maps legacy runtime records to one
`cycle-event@1.0.0` object per line. It exports an allowlisted payload and
omits prompts, transcripts, raw session identifiers, command output, and
hidden reasoning. Existing runtime files are not modified.

### Baseline metrics

```bash
python3 scripts/esra_runtime.py baseline \
  --name skill-footprint \
  --metric skills=5 \
  --metric words=1363
```

### Bounded command experiment

```bash
python3 scripts/esra_runtime.py experiment create validator-speed \
  --hypothesis "the candidate retains correctness with lower latency" \
  --baseline-command "python3 scripts/validate_skills.py" \
  --candidate-command "python3 scripts/esra_runtime.py validate skills" \
  --guardrail "both commands must exit zero" \
  --alignment-score 1.0 --minimum-alignment 0.6

python3 scripts/esra_runtime.py experiment run validator-speed --mode ab --timeout 30
python3 scripts/esra_runtime.py experiment report validator-speed
python3 scripts/esra_runtime.py experiment decide validator-speed \
  --decision more-evidence --notes "sample is too small for promotion"
```

Commands are parsed into argument arrays and run without a shell. Modes are `canary`, `staged`, `ab`, and `stress`. Runs below their declared value-alignment threshold are blocked. Canary/staged stop after a candidate failure. Captured output is truncated to 1,000 characters per stream. Reports are written under the private runtime data directory. A recommendation is evidence, not promotion.

Do not use experiment commands that may print secrets: the runtime stores the final output tail for debugging. A successful canary always returns `more-evidence`; it can reject an unsafe candidate but cannot justify adoption by itself.

### Validation, dashboard, audit, and oversight

```bash
python3 scripts/esra_runtime.py validate skills
python3 scripts/esra_runtime.py dashboard --json
python3 scripts/esra_runtime.py audit --limit 10
python3 scripts/esra_runtime.py oversight \
  --id review-001 --title "Refine ESRA trigger" \
  --summary "Raise the routine-task boundary" \
  --evidence "false activation in two fixtures" \
  --verification "run trigger fixtures; revert the skill edit if either fails"
```

Oversight writes a local Markdown proposal. It deliberately does not mutate GitHub or Git state.

## Codex lifecycle hook

The plugin's `hooks/hooks.json` records `UserPromptSubmit`, `Stop`, and `SessionEnd` lifecycle metadata through `scripts/esra_hook.py`. It emits no stdout, does not steer the model, and does not start an ESRA cycle. Codex requires review/trust for non-managed hooks; inspect it with `/hooks` before enabling.

To test the adapter without Codex:

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"demo","turn_id":"one","cwd":"/tmp/project"}' \
  | ESRA_DATA_DIR=/tmp/esra-hook python3 scripts/esra_hook.py
```
