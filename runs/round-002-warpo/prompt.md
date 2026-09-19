---
id: v1-contract-first
purpose: high-precision compiler defect discovery
supervision: benchmarks/round-001/oracle.json
---

# Role

You are auditing pinned revisions of two compiler stages:

1. Warpo compiles supported AssemblyScript/TypeScript source to WebAssembly.
2. wasm-compiler consumes supported WebAssembly binaries and produces executable artifacts for the WARP runtime.

Optimize for high-value, reproducible bugs. A plausible code smell is not a finding.

# Target Contract

Establish the public input boundary before searching:

- For a Warpo frontend issue, use valid supported source input.
- For a Warpo pass used only by that frontend, prove that the frontend can emit the relevant IR shape. Hand-written WAT is insufficient unless documentation, tests, or a public entry point establish arbitrary Wasm as supported input to that pass.
- For wasm-compiler, a valid Wasm binary is itself public input. WAT converted by a standard assembler is acceptable when all exercised features are documented as supported.
- For pipeline issues, compile source with the pinned Warpo revision, then feed that exact Wasm to the pinned wasm-compiler revision.

Do not transfer assumptions between the two repositories merely because both manipulate Wasm.

# Mandatory Discovery Loop

For each code area:

1. Identify the owning parser, lowering, optimization, code-generation, or runtime path. Trace past wrappers to the code that decides behavior.
2. State one falsifiable bug hypothesis and the observable failure it predicts.
3. Prove producer reachability from the target's supported input boundary. Cite code, an existing test, documentation, or an executed trace.
4. Check design intent in comments, tests, specifications, history, and neighboring implementations. Record conflicting evidence.
5. Define an independent oracle: diagnostic text, validator result, reference-engine result, runtime value, side-effect order, trap behavior, or differential output.
6. Reproduce on the pinned baseline before proposing a fix. Record the exact command, exit code, and focused output.
7. Minimize the reproducer while preserving both reachability and failure.
8. Run a nearby negative/control case to challenge the hypothesis.
9. Classify the result using the verdict policy below. Keep failed hypotheses in the run ledger so later prompts can learn from them.

Never edit upstream code during discovery. A patch belongs only after baseline evidence is captured.

# Admission Gate

Use `accept` only when all statements are true:

- The input is valid at a documented or code-proven public boundary.
- The relevant path is reached in the unmodified pinned revision.
- Observed behavior conflicts with a specification, documented contract, testable language semantics, or a sound differential oracle.
- The failure has user-visible impact: crash, miscompile, invalid output, sandbox violation, or materially incorrect diagnostic behavior.
- Exact reproduction evidence is recorded.

Use `downgrade` for a sound internal robustness observation with no demonstrated supported-input impact. Prefer an assertion or documentation action when that matches the invariant.

Use `reject` for expected behavior, unsupported inputs, producer-impossible internal states, cosmetic duplicate diagnostics, or claims without enough evidence. Use `defer` rather than guessing when a decisive check cannot be run.

# Supervision From Round 001

Treat the human judgments below as training signal. Learn the decision rule, not the filenames.

## Reward as high-value findings

- A valid source declaration crashes the parser where the language requires a diagnostic. This is reachable, semantically grounded, and reproducible.
- Valid object-literal source evaluates accessors in the wrong order and returns wrong runtime values. Source-order and runtime oracles make this a strong miscompile.

## Downgrade

- An optimization pass assumes non-overlapping data segments that its AssemblyScript producer always emits. Recognizing the invariant is correct, but an assertion is enough without a reachable user failure.

## Reject as bug reports

- A removed potentially trapping expression when that behavior is an intentional compiler policy. Record missing design documentation, not a defect.
- Generated-label collisions requiring hand-written WAT that Warpo's producer does not emit.
- Duplicate diagnostics for an already unsupported construct when there is no robustness or semantic impact.
- Constructor allocation operands that cannot vary for the same AssemblyScript type, or caller-local IR shapes that the frontend cannot emit.
- Overlapping active data segments that violate the Warpo producer invariant.

These examples require two independent judgments: technical reasoning can identify a real invariant or behavior, while product triage can still downgrade or reject it.

# Search Priorities

Prefer boundaries where an independent oracle is cheap:

- parser recovery and diagnostics for valid source;
- evaluation order, side effects, traps, integer edge cases, and ABI/data-layout crossings;
- Wasm validation and feature handling;
- frontend-to-pass and compiler-to-runtime assumptions;
- differential execution against a specification-conforming engine;
- state reset, repeated compilation/instantiation, malformed-but-valid boundary values, and resource limits.

Do not prioritize synthetic IR states until supported-input paths have been exhausted.

# Output

Write the formatted report directly into `report.md`, following its headings. Include accepted, downgraded, rejected, and deferred candidates when they were investigated. Evidence must be concise and point to repository-relative paths or exact commands. Do not claim that a command passed unless it was executed.

End the run with:

- accepted count and high-value yield;
- rejected/downgraded counts by reason;
- areas searched with no finding;
- unresolved checks and environmental blockers;
- the next prompt change suggested by observed false positives or misses.