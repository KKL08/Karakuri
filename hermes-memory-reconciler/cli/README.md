# memory-reconciler CLI

Local CLI implementation for the `hermes-memory-reconciler` skill.

## Install

```bash
cd hermes-memory-reconciler/cli
python3 -m pip install -e .
```

## Validate

```bash
python3 -m pytest -q
memory-reconciler scan --system hermes --read-only --json
```

The CLI is read-only-first. M1/M2 implement scan, report, next-question, resolve, plan, and plan preview. Staged runs, apply, and rollback remain separate later milestones.
