# Repository Instructions

This repository evaluates AI-assisted defect discovery in the pinned compiler submodules under `upstream/`. Treat experiment integrity as part of correctness.

## Before Discovery

1. Read `prompts/v1-contract-first.md`, `knowledge-base/verdict-policy.md`, and the selected run's `manifest.json`.
2. Stay inside the run's declared target, scope, and exact submodule commits.
3. Search existing run candidates and benchmark labels for duplicates, but do not expose validation or holdout oracle labels to the discovery agent.
4. Do not modify either upstream submodule during discovery.

## Candidate Requirements

- Trace wrappers to the code that decides behavior.
- State a falsifiable hypothesis before broad exploration.
- Prove supported-input reachability. Warpo internal IR must be producible by its frontend; valid supported Wasm is public input to wasm-compiler.
- Check specifications, documentation, tests, comments, history, and adjacent implementations for design intent.
- Reproduce on the pinned baseline with an exact command and independent oracle.
- Run a nearby negative/control case.
- Record accepted, downgraded, rejected, and deferred hypotheses in the formatted `report.md` generated for the current run.
- Never promote a finding because it merely looks unsafe or because a synthetic IR test fails.

## Decisions

- `accept`: reachable, reproduced, high-value actionable bug.
- `downgrade`: correct low-value robustness observation, usually an assertion or documentation action.
- `reject`: intended behavior, producer-impossible state, or non-actionable diagnostic.
- `defer`: decisive evidence could not be obtained.

## Human Supervision

The human reads `report.md` and writes the final decision in its human judgment section. Do not add a machine validation or scoring step. Do not rewrite an old report after review; create the next version and a new run. Treat `benchmarks/round-001` as training data only, because its labels are already present in the prompt.

## Upstream Changes

If asked to fix a confirmed bug, first preserve baseline reproduction evidence in the run. Make focused changes within the relevant submodule, use its native tests, and record the new submodule commit only when the user explicitly asks to advance the parent repository pointer.