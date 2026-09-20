# Repository Instructions

This repository evaluates AI-assisted defect discovery in the pinned compiler submodules under `upstream/`. Treat experiment integrity as part of correctness.

## Before Discovery

1. Read the selected run's `manifest.json` and `prompt.md`, plus `knowledge-base/verdict-policy.md`.
2. Stay inside the run's declared target, scope, and exact submodule commits.
3. Search existing run candidates and supervision labels for duplicates, but do not expose validation or holdout oracle labels to the discovery agent.
4. Do not modify either upstream submodule during discovery.
5. For Warpo setup, compilation, execution, or candidate reproduction, read `.github/skills/warpo-defect-workflow/SKILL.md` and use its npm and Node.js workflow.

## Candidate Requirements

- Trace wrappers to the code that decides behavior.
- State a falsifiable hypothesis before broad exploration.
- Prove supported-input reachability. Warpo internal IR must be producible by its frontend; valid supported Wasm is public input to wasm-compiler.
- Check specifications, documentation, tests, comments, history, and adjacent implementations for design intent.
- Reproduce on the pinned baseline with an exact command and independent oracle.
- Run a nearby negative/control case.
- Give each reported candidate its own independently minimized source artifact; do not combine bugs in one source file or multi-export harness.
- Add concise comments to non-obvious reproducers that identify the triggering transition and expected observation.
- For subtle stateful bugs, explain the stored state, the transition that invalidates it, and how the stale state produces the observed failure.
- Record only reproduced `accept`, `downgrade`, and genuinely uncertain `defer` candidates in `report.md`. Omit hypotheses the AI rejects.
- Rate every reported candidate as `high`, `low`, or `unknown` value independently of its recommendation.
- Never promote a finding because it merely looks unsafe or because a synthetic IR test fails.

## Decisions

- `accept`: reachable, reproduced, actionable bug; it can be high or low value.
- `downgrade`: correct low-value robustness observation, usually an assertion or documentation action.
- `reject`: intended behavior, producer-impossible state, falsified hypothesis, or non-actionable diagnostic; omit it from Candidate Findings.
- `defer`: reproduced behavior whose contract or oracle remains genuinely unresolved.

Prioritize ordinary valid programs with surprising compiler behavior. Deprioritize extreme API arguments, conspicuously erroneous source, uncommon API behavior without a clear local contract or realistic workflow, and narrow robustness cases unless they expose a broader semantic failure. A differential mismatch can support the oracle but does not by itself make a candidate high value.

## Human Supervision

The human reads `report.md` and writes the final decision in its human judgment section. Do not add a machine validation or scoring step. Do not rewrite an old report after review; update the single source prompt only after preserving the current run snapshot, then create a new run. Treat supervision rounds referenced by the active prompt as training data only because their labels are already exposed.

## Public Chinese Analysis Log

During a discovery run, maintain `## 中文分析过程记录` in the report as a public, contemporaneous log. Write concise Chinese entries as the analysis proceeds, preserving the actual order of explored directions, hypotheses, checks, results, rejected leads, and pivots. Explain why each detection direction was selected. At the end, leave these entries in their original order instead of rewriting them into a polished audit or summary. Leave the human review section untouched.

## Upstream Changes

If asked to fix a confirmed bug, first preserve baseline reproduction evidence in the run. Make focused changes within the relevant submodule, use its native tests, and record the new submodule commit only when the user explicitly asks to advance the parent repository pointer.