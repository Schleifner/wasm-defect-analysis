---
name: warpo-defect-workflow
description: 'Build and test the pinned Warpo compiler and reproduce defects from AssemblyScript source. Use when auditing Warpo, creating or minimizing AssemblyScript reproducers, compiling source to Wasm, invoking Wasm exports under Node.js, or validating a Warpo candidate.'
---

# Warpo Defect Workflow

Use the repository-supported path below instead of rediscovering Warpo's build and runtime setup for every run.

## Guardrails

1. Read the selected run's `manifest.json`, `prompt.md`, and `knowledge-base/verdict-policy.md` first.
2. Confirm that `git -C upstream/warpo rev-parse HEAD` equals the manifest commit.
3. Keep discovery artifacts under `runs/<run-id>/artifacts/` and do not edit `upstream/warpo` during discovery.
4. Use one minimal AssemblyScript source file per candidate. A shared runner is allowed; a shared multi-candidate source module is not.

## Initialize And Build

Warpo requires Node.js 22.4 or newer. From the analysis repository root:

```bash
git submodule update --init upstream/warpo
cd upstream/warpo
npm ci
npm run build
```

`npm run build` is the stable project entry point. It builds the TypeScript CLI and the C++ compiler, producing:

- `upstream/warpo/dist/warpo.js`
- `upstream/warpo/build/warpo/warpo_asc`

CMake is an implementation detail of this npm script. Do not replace the package workflow with hand-selected CMake targets unless diagnosing a failure in `npm run build` itself.

After the first setup, use `npm run build` to rebuild. Use `npm test` only when broad validation is justified; prefer the smallest relevant upstream test while investigating a candidate.

## Compile A Reproducer

Export the function that exposes the observable result. From the analysis repository root:

```bash
node upstream/warpo/dist/warpo.js \
  runs/<run-id>/artifacts/C-001.ts \
  -o runs/<run-id>/artifacts/C-001.wasm \
  --exportRuntime
```

The development CLI resolves the locally built `warpo_asc` automatically. `--exportRuntime` exposes AssemblyScript runtime helpers when a reproducer needs them; an explicitly exported test function is still required.

## Execute A Reproducer

Use the repository runner for modules whose only host dependency is AssemblyScript's standard `env.abort` import:

```bash
node scripts/run_warpo_wasm.mjs \
  runs/<run-id>/artifacts/C-001.wasm \
  exportedFunction \
  42 7n
```

Arguments are numeric. Append `n` to an integer for an `i64` parameter. Output is stable and line-oriented, for example `exportedFunction=49`. The runner preserves `-0`, prints `i64` results with an `n` suffix, and reports AssemblyScript abort locations.

The runner deliberately rejects unknown imports. If a reproducer needs WASI or project-specific host functions, add a candidate-specific runner beside that candidate instead of silently stubbing behavior in the shared runner.

To verify the standard path itself:

```bash
node upstream/warpo/dist/warpo.js \
  .github/skills/warpo-defect-workflow/assets/smoke.ts \
  -o /tmp/warpo-defect-workflow-smoke.wasm \
  --exportRuntime
node scripts/run_warpo_wasm.mjs /tmp/warpo-defect-workflow-smoke.wasm add 20 22
```

The expected output is `add=42`.

## Candidate Evidence

For each hypothesis:

1. Name the source-reachable code path and predict one observable failure.
2. Compile the candidate-specific source on the manifest's pinned baseline.
3. Execute it with this runner or a narrowly justified candidate-specific runtime.
4. Compare against an independent oracle. The runner and the compiler under test are not independent oracles.
5. Run a nearby control that could falsify the hypothesis.
6. Record the artifact, exact commands, exit codes, and focused output in one reproduction entry.

During the run, maintain the public Chinese analysis log required by the run prompt. Add entries when choosing a detection direction, testing a hypothesis, rejecting a lead, or changing direction. Preserve their original order in the final report rather than reconstructing a polished audit after the work is complete.