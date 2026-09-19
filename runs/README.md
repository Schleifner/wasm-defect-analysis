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

The repository has one mutable prompt source, `prompts/defect-discovery.md`. Each run's copied `prompt.md` and manifest hash preserve the exact revision used, so prompt iteration never rewrites historical experiment inputs.

Writing “no finding” is preferable to manufacturing weak candidates.

The AI writes candidate findings and a contemporaneous public Chinese analysis log in the same `report.md`; the human writes the final decision there without the AI editing those fields. The log preserves explored directions, hypotheses, rejected leads, and pivots in their original order. No separate machine validation or scoring step is required.