# Repository Instructions

This repository evaluates AI-assisted defect discovery in the pinned compiler submodules under `upstream/`. Treat experiment integrity as part of correctness.

## Before Discovery

1. Read the selected run's `manifest.json` and `prompt.md`, plus `knowledge-base/verdict-policy.md`.
2. Stay inside the run's declared target, scope, and exact submodule commits.
3. Search existing run candidates and supervision labels for duplicates, but do not expose validation or holdout oracle labels to the discovery agent.
4. Do not modify either upstream submodule during discovery.
5. For Warpo setup, compilation, execution, or candidate reproduction, read `.github/skills/warpo-defect-workflow/SKILL.md` and use its npm and Node.js workflow.

## Workflow Ownership

- These repository instructions own experiment isolation, baseline protection, and human-review preservation.
- `knowledge-base/verdict-policy.md` owns supported-input boundaries, exploration versus admission, artifact requirements, decisions, and value ratings.
- Target skills own setup, build, compile, execution, and operational evidence capture.
- The selected run's `prompt.md` owns the discovery loop, search priorities, report format, and contemporaneous Chinese analysis log.

Follow these references instead of maintaining separate copies of their rules here.

## Human Supervision

The human reads `report.md` and writes the final decision in its human judgment section. Do not add a machine validation or scoring step. Do not rewrite an old report after review; update the single source prompt only after preserving the current run snapshot, then create a new run. Treat supervision rounds referenced by the active prompt as training data only because their labels are already exposed.

## Upstream Changes

If asked to fix a confirmed bug, first preserve baseline reproduction evidence in the run. Make focused changes within the relevant submodule, use its native tests, and record the new submodule commit only when the user explicitly asks to advance the parent repository pointer.