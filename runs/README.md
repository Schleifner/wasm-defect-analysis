# Runs

The complete operating procedure, including where and how to write human feedback, is in [../docs/CN-workflow.md](../docs/CN-workflow.md).

Each directory is an immutable experiment envelope created with `scripts/new_run.py`:

```text
runs/<run-id>/
  manifest.json      Prompt hash, model, scope, and exact upstream commits
  prompt.md          Prompt snapshot used for this run
  report.md          AI's formatted report and the human's final judgment
  artifacts/         Local reproducers and focused logs (ignored by Git)
```

Never reuse a run ID or edit old prompt snapshots. If execution is retried, create a new run ID and reference the earlier run in the report or scope text.

Writing “no finding” is preferable to manufacturing weak candidates.

The AI writes candidate findings and the human writes the final decision in the same `report.md`. No separate machine validation or scoring step is required.