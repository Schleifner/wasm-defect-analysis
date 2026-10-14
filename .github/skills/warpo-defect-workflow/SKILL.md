---
name: warpo-defect-workflow
description: 'Build and test the pinned Warpo compiler and reproduce defects from AssemblyScript source. Use when auditing Warpo, creating or minimizing AssemblyScript reproducers, compiling source to Wasm, invoking Wasm exports under Node.js, or validating a Warpo candidate.'
---

# Warpo Defect Workflow

Use the repository-supported path below instead of rediscovering Warpo's build and runtime setup for every run.

Repository instructions govern experiment isolation. Read the selected run's manifest
and prompt before using this skill. Candidate admission and artifact requirements are
defined in `knowledge-base/verdict-policy.md`; this skill defines operations only.

## Initialize And Build

Warpo requires Node.js 22.4 or newer. Initialize a missing submodule with
`git submodule update --init upstream/warpo` only before selecting the baseline and
creating the run. For an existing run, verify the actual HEAD against its manifest
before building; stop on a mismatch rather than silently switching revisions.
Confirm that `git -C upstream/warpo status --porcelain` is empty. Do not reset an
already selected checkout with `git submodule update`.
From the analysis repository root:

```bash
git -C upstream/warpo rev-parse HEAD
cd upstream/warpo
npm ci
npm run build
```

`npm run build` is the stable project entry point. It builds the TypeScript CLI and the C++ compiler, producing:

- `upstream/warpo/dist/warpo.js`
- `upstream/warpo/build/warpo/warpo_asc`

CMake is an implementation detail of this npm script. Do not replace the package workflow with hand-selected CMake targets unless diagnosing a failure in `npm run build` itself.

After a revision change, run `npm ci` and `npm run build` again instead of reusing old
build artifacts. For further builds at the same revision, use `npm run build`.
Use `npm test` only when broad validation is justified; prefer the smallest relevant upstream test while investigating a candidate.

## Compile A Reproducer

For the shared export-invocation runner, export the function that exposes the observable
result. For start-only assertions, see the instantiation instructions below. Compile
from the analysis repository root:

```bash
node upstream/warpo/dist/warpo.js \
  runs/<run-id>/artifacts/C-001.ts \
  -o runs/<run-id>/artifacts/C-001.wasm \
  --exportRuntime
```

The development CLI resolves the locally built `warpo_asc` automatically. `--exportRuntime`
exposes AssemblyScript runtime helpers when a reproducer needs them; it does not create
a test-function export.

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

For assertions in a module's start function, use a candidate-specific runner that
compiles and instantiates the module with its declared imports. No exported test
function is required; the shared runner above still expects an export. Record the
exact assertion location rather than treating any thrown exception as the expected failure.

To verify the standard path itself:

```bash
node upstream/warpo/dist/warpo.js \
  .github/skills/warpo-defect-workflow/assets/smoke.ts \
  -o /tmp/warpo-defect-workflow-smoke.wasm \
  --exportRuntime
node scripts/run_warpo_wasm.mjs /tmp/warpo-defect-workflow-smoke.wasm add 20 22
```

The expected output is `add=42`.

## Capture Compiler Failures

When the JavaScript wrapper may conceal a native crash, invoke
`upstream/warpo/build/warpo/warpo_asc` directly with the same compilation arguments.
Capture its exit status or signal, diagnostic, and output existence. Do not treat
wrapper exit zero as successful compilation without a fresh output artifact.
Compile to a new output path so a previous successful build cannot mask a failure.