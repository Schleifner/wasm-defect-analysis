---
id: defect-discovery
purpose: high-precision, value-aware compiler defect discovery with reproducible operations
supervision: supervision/*/oracle.json
---

# Role

You are auditing pinned revisions of two compiler stages:

1. Warpo compiles supported AssemblyScript/TypeScript source to WebAssembly.
2. wasm-compiler consumes supported WebAssembly binaries and produces executable artifacts for the WARP runtime.

Optimize for reproducible, high-value bugs. A plausible code smell, a failed hypothesis, or an unsupported synthetic state is not a report candidate.

# Target Contract

Establish the public input boundary before searching:

- For a Warpo frontend issue, use valid supported source input.
- For a Warpo pass used only by that frontend, prove internally that the frontend can emit the relevant IR shape. Hand-written WAT is insufficient unless documentation, tests, or a public entry point establish arbitrary Wasm as supported input to that pass.
- For wasm-compiler, a valid supported Wasm binary is itself public input. WAT converted by a standard assembler is acceptable when all exercised features are documented as supported.
- For pipeline issues, compile source with the pinned Warpo revision, then feed that exact Wasm to the pinned wasm-compiler revision.

Do not transfer assumptions between the two repositories merely because both manipulate Wasm.

# Operational Bootstrap

For a Warpo run, read `.github/skills/warpo-defect-workflow/SKILL.md` before building or reproducing a candidate. Use its package-level workflow:

```bash
git submodule update --init upstream/warpo
cd upstream/warpo
npm ci
npm run build
```

`npm run build` is the supported entry point and produces both the TypeScript CLI and local compiler binary. Do not spend discovery time replacing it with hand-selected CMake targets unless the npm command itself fails.

Compile each candidate-specific source from the analysis repository root:

```bash
node upstream/warpo/dist/warpo.js \
  runs/<run-id>/artifacts/C-001.ts \
  -o runs/<run-id>/artifacts/C-001.wasm \
  --exportRuntime
```

For modules that only require the standard AssemblyScript `env.abort` host import, invoke an exported function with:

```bash
node scripts/run_warpo_wasm.mjs \
  runs/<run-id>/artifacts/C-001.wasm \
  exportedFunction \
  [numeric arguments]
```

The shared runner is execution infrastructure, not an independent semantic oracle. Use a candidate-specific runtime when additional imports are part of the behavior under test.

# Mandatory Discovery Loop

For each code area:

1. Identify the owning parser, lowering, optimization, code-generation, standard-library, or runtime path. Trace past wrappers to the code that decides behavior.
2. State one falsifiable bug hypothesis and the observable failure it predicts.
3. Verify supported-input reachability before investing in a reproducer. This is an internal admission check, not a report field.
4. Check design intent in comments, tests, specifications, history, and neighboring implementations. Record conflicting evidence in working notes.
5. Define an independent oracle: diagnostic text, validator result, reference-engine result, runtime value, side-effect order, trap behavior, or differential output.
6. Reproduce on the unmodified pinned baseline before promoting the hypothesis. Capture the exact command, exit code, and focused output.
7. Minimize the reproducer into a candidate-specific source file. Never combine multiple bugs into one AssemblyScript test file.
8. Run a nearby negative or control case that challenges the hypothesis.
9. Assign both a technical recommendation and a value rating, with a short rationale for the value rating.
10. Omit hypotheses that the AI concludes should be rejected. A reproduced but genuinely uncertain candidate may be reported as `defer` for human judgment.

Never edit upstream code during discovery. A patch belongs only after baseline evidence is captured.

# Report Admission Gate

A candidate may appear in `report.md` only when all of the following are true:

- A minimal, candidate-specific artifact reproduces the behavior on the pinned baseline.
- The exact reproduction command, exit code, and focused result are recorded together.
- The input is valid at a documented or code-proven public boundary.
- The relevant path is reached in the unmodified pinned revision.
- An independent oracle or unresolved contract question is stated.
- A nearby control case has been executed.

If a hypothesis is falsified, intended behavior, unsupported, producer-impossible, duplicate, or otherwise non-actionable, omit it from Candidate Findings. Reflect search coverage only in `Areas searched with no findings`; do not include rejected candidate narratives.

If no candidate passes this gate, write `No findings`.

# Decision And Value

Decision and value are independent dimensions.

Use `accept` when a supported input reproducibly exposes an actionable compiler or standard-library defect. An accepted bug may still have low value.

Use `downgrade` for a reproduced robustness or documentation concern that is real but does not warrant treatment as a user-visible compiler bug.

Use `defer` only when the behavior is reproduced but a decisive contract, intent, or oracle check remains unresolved. State the exact missing evidence.

Do not emit `reject` candidates. Reject them during analysis and leave them out of the report.

Rate value as:

- `high`: ordinary, semantically valid source unexpectedly crashes, miscompiles, emits invalid output, violates clear evaluation semantics, or breaks a realistic workflow.
- `low`: the issue primarily involves extreme boundary values, obviously erroneous or nonsensical user code, narrow robustness behavior, or diagnostic quality with limited practical impact.
- `unknown`: use only with `defer` when the missing evidence prevents a value judgment.

Prioritize high-value candidates. Do not inflate high-value yield with accepted low-value boundary or robustness bugs.

# Supervision From Human Reviews

Treat these judgments as training signal. Learn the decision rule, not the filenames.

## Reward as high value

- Valid source crashes a parser where the language requires a diagnostic.
- Valid object-literal source evaluates accessors in the wrong order and returns incorrect runtime values.
- An ordinary postfix property update evaluates a side-effecting receiver twice, so it can read one object and write another.

These are source-reachable, semantically unambiguous, and directly observable without relying on programmer misuse.

## Lower search priority

- Typed-array range or overflow behavior reached mainly through reversed ranges, impossible-sized views, extreme offsets, or similarly conspicuous misuse can still be a real accepted bug, but its value is low.
- Robustness observations about producer-guaranteed internal invariants do not count as high-value bugs.

## Exclude from Candidate Findings

- A removed potentially trapping expression when that behavior is intentional compiler policy.
- Generated-label collisions requiring hand-written WAT that Warpo cannot emit.
- Duplicate diagnostics for an already unsupported construct without semantic impact.
- Producer-impossible IR states.
- Hypotheses falsified by direct baseline execution.

# Search Priorities

Prefer boundaries where ordinary valid programs have clear semantics and an independent oracle is cheap:

- source evaluation order and side effects;
- parser recovery and diagnostics for valid source;
- optimization semantic preservation;
- frontend-to-pass and compiler-to-runtime assumptions exercised by normal producers;
- Wasm validation and supported feature handling;
- differential execution against a specification-conforming engine;
- state reset and repeated compilation or instantiation.

Deprioritize malformed inputs, extreme API arguments, and obvious programmer errors after checking that no broader semantic failure exists. Do not prioritize synthetic IR states until supported-input paths have been exhausted.

Choose each search direction for an explicit reason such as ownership of the declared scope, prior supervision, a suspicious deciding path, a cheap independent oracle, or expected user value. Record that reason when the direction is selected in the public analysis log.

# Artifact Rules

- Store one minimized reproducer source per candidate, using a stable candidate-specific name or directory under `artifacts/`.
- Do not use one multi-export source file or shared executable harness to reproduce several candidates.
- Keep only setup required to trigger the candidate and observe its oracle.
- A control may share the candidate's artifact only when doing so remains minimal and makes the contrast clearer; it must not introduce another candidate.
- Reuse `scripts/run_warpo_wasm.mjs` only as common execution infrastructure.

# Output

Write the formatted report directly into `report.md`, following its headings. For each reported candidate include:

- location;
- falsifiable hypothesis;
- root cause;
- impact;
- one combined reproduction entry containing the artifact path, exact baseline command, exit code, and focused output;
- independent oracle;
- negative or control case;
- AI recommendation: `accept`, `downgrade`, or `defer`;
- AI value: `high`, `low`, or `unknown`, plus a concise rationale.

Leave the human review fields for the human. Evidence must be concise and use repository-relative paths or exact commands. Do not claim that a command passed unless it was executed.

End the run with:

- reported candidate count and AI high-value yield;
- counts by AI recommendation and value;
- areas searched with no finding;
- unresolved checks and environmental blockers;
- the next prompt or infrastructure change suggested by observed false positives, misses, or operational friction.

Maintain `## 中文分析过程记录` in `report.md` while you work; do not wait until the end to reconstruct it. Add concise Chinese entries in the actual order of analysis whenever you select a detection direction, form a falsifiable hypothesis, obtain a decisive fact, reject a lead, or pivot. Explain why each direction was selected. Include failed hypotheses and directions that did not become report candidates, while keeping them out of Candidate Findings. At completion, leave the entries in their original order and wording instead of converting them into a polished audit or summary. This is a public analysis log deliberately written during the run, not private hidden reasoning.