# Contributing

Keep changes small, evidence-backed, and compatible with progressive skill loading.

1. Preserve each skill's narrow trigger and routine-task bypass.
2. Avoid mandatory chains between skills.
3. Do not introduce host-specific paths unless the skill targets that host explicitly.
4. Add or update validation tests for structural or policy changes.
5. Distinguish measured behavior from estimates and proposals.

Before opening a pull request, run:

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
```

By submitting a contribution, you agree that it is licensed under the
Apache License, Version 2.0, without additional terms or conditions.
