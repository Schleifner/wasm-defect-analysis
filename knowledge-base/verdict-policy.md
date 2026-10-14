# Verdict Policy

## Core Rule

A confirmed compiler bug needs all three: supported-input reachability, a contract violation, and an observed failure with an independent oracle.

Reachability remains a mandatory admission check, but it is not a separate report field. A candidate enters the report only after a minimal supported input reproduces it on the pinned baseline.

This file is the authoritative source for supported-input boundaries, report admission,
artifact requirements, decisions, and value ratings. The discovery prompt owns search
strategy and report presentation; target skills own build and execution procedures.

## Exploration Versus Admission

Exploration may start with an unproved reachability hypothesis. Use a small, inexpensive
source probe to learn whether the frontend emits the suspected shape and whether the
predicted behavior occurs. Full reachability proof is not required before making that
probe; it is required before admitting a finding.

Hand-written WAT or internal IR may help isolate a mechanism, but a synthetic failure
alone does not establish a Warpo product defect. Resolve the supported-input boundary
and reproduce through it before promotion. Keep unconfirmed or falsified probes in the
analysis log, not Candidate Findings. Code inspection alone does not qualify for `defer`.

## Report Admission Gate

A candidate may enter Candidate Findings only when:

- A minimal, candidate-specific source artifact reproduces the behavior on the unmodified pinned baseline.
- The exact baseline command, exit code, and focused output are recorded together.
- The input is supported at a documented or code-proven public boundary, and reaches the relevant path.
- The expected behavior is grounded in specifications, documentation, tests, comments, history, or adjacent implementations; conflicting design evidence has been checked.
- An independent oracle is stated, or a reproduced `defer` case identifies the precise unresolved contract or oracle question.
- A nearby negative or control case has been executed.

- Report only reproduced candidates recommended as `accept`, `downgrade`, or `defer`.
- Omit hypotheses the AI concludes are intended, unsupported, producer-impossible, falsified, duplicate, or otherwise non-actionable.
- Use `defer` only when the behavior is reproduced but a decisive contract or oracle check remains unresolved. State the missing evidence.
- If no candidate passes the gate, write `No findings` and summarize the areas searched.

The shared runner and the compiler under test are not independent oracles. Appropriate
oracles include a contract-backed expected diagnostic, validator result, runtime value,
side-effect order, trap behavior, or differential result from an applicable reference.

## Artifact Requirements

- Give every reported candidate its own independently minimized source artifact under the run's `artifacts/`, using a stable candidate-specific name or directory. Do not combine multiple bugs in one source file or multi-export harness.
- A common execution runner is allowed; a shared multi-candidate reproducer is not.
- Keep only setup required to trigger the candidate and observe its oracle. A control may share the artifact when that keeps the contrast minimal and introduces no second candidate.
- Use descriptive names and concise comments for non-obvious triggers and expected observations.
- For stateful bugs, explain the stored state, the transition that invalidates it, and how the stale state produces the failure.
- Do not preserve an O0/O3 mismatch as a minimization requirement when a smaller source demonstrates the same root cause at both levels.

## Warpo Boundary

Warpo's source frontend is the producer for its internal optimization passes. A hand-written WAT or constructed Binaryen IR case is not sufficient when it violates a frontend invariant. First attempt to generate the shape from supported AssemblyScript. If that fails, inspect and cite the producer path before classifying the candidate.

Exclude bugs arising from direct memory load/store attacks based on knowledge of memory layout.
Source acceptance alone does not establish supported behavior. Check compiler-generated
object contracts and the intended backend's host-integration restrictions, including
nested Wasm re-entry, rather than assuming reference-runtime support applies locally.

## wasm-compiler Boundary

wasm-compiler accepts supported WebAssembly bytecode directly. A valid Wasm module assembled from WAT is therefore a legitimate reproducer. Check the documented feature matrix and build configuration before treating an unsupported proposal as a defect.

## Pipeline Boundary

Compile supported source with the pinned Warpo revision and feed that exact output to
the pinned wasm-compiler revision, without manual IR edits. Do not transfer assumptions
between the two targets merely because both manipulate Wasm.

## Decision And Value

Decision and value are independent:

- **Accept:** a supported input reproducibly exposes an actionable compiler or standard-library defect.
- **Downgrade:** a reproduced robustness or documentation concern is real but does not warrant treatment as a user-visible compiler bug.
- **Defer:** behavior is reproduced, but decisive evidence about the contract, intent, or oracle is unavailable.
- **Reject internally:** expected behavior, unsupported input, a producer-impossible state, a falsified hypothesis, or a non-actionable diagnostic. Do not include it in Candidate Findings.

Rate each reported candidate separately:

- **High value:** ordinary semantically valid input crashes, miscompiles, emits invalid output, violates clear evaluation semantics, or breaks a realistic workflow.
- **Low value:** impact primarily requires extreme boundary values, conspicuously erroneous or nonsensical user code, uncommon API behavior without a clear local contract or realistic workflow, narrow robustness behavior, or low-impact diagnostics.
- **Unknown value:** use only with `defer` when missing evidence prevents classification.

Prioritize high-value findings. An accepted bug can still be low value. A reference-language mismatch can establish expected behavior when the contract applies, but it does not by itself establish practical value. Prefer local invariants, documentation, existing test intent, and realistic workflows when rating value.

## Decision Examples From Round 001

- **Accept:** valid source crashes instead of producing a required diagnostic.
- **Accept:** valid source is miscompiled and an executed module returns the wrong value or evaluation order.
- **Downgrade:** a pass lacks an assertion for an invariant guaranteed by its only producer.
- **Reject:** behavior is an intentional optimization policy, even if the policy needs documentation.
- **Reject:** only synthetic IR or WAT can produce the state for a source-only pipeline.
- **Reject:** duplicate diagnostics for an already unsupported construct without semantic or robustness impact.

## Decision Examples From Round 002

- **Accept, high value:** an ordinary postfix property update evaluates a side-effecting receiver twice and can read one object while writing another.
- **Accept, low value:** typed-array range or overflow behavior requires reversed ranges, impossible-sized views, extreme offsets, or similarly conspicuous misuse.
- **Omit:** hypotheses disproved by direct baseline execution, even when the initially suspected code looked unsafe.

## Decision Examples From Round 003

- **Accept, high value:** an ordinary string replacement reaches a growth path whose new capacity is still smaller than the immediately required write. The local capacity invariant and baseline abort establish the defect without relying on a JavaScript comparison.
- **Accept, low value:** an empty string search with an explicit start differs from JavaScript semantics, but the uncommon usage has no explicit local documentation or demonstrated realistic workflow. The defect is real; its value was overrated.
- **Accept, high value:** map rehash compacts live entries while an active iterator retains a physical offset, causing it to skip an entry. For this kind of non-obvious runtime bug, explain the stored state, invalidating transition, and resulting behavior explicitly.

## Decision Examples From Round 004

- **Reject, high exploratory value:** an O0/O3 mismatch follows raw writes to `_index` or `_env` of an immutable compiler-generated static function object. The investigation can be useful while the mutation remains unsupported; do not count it as an accepted high-value bug.
- **Reject, no value:** an imported-call GC example requires nested Wasm re-entry that the intended backend explicitly disallows. Reference-runtime agreement does not override this integration contract; clarify undocumented restrictions separately.
- **Accept, high value:** a class-only global visitor omits managed function references, allowing a globally referenced closure and its captured environment to be collected. An optimization that removes a temporary root is an exposure condition, not the underlying root omission.
- **Accept, high value:** normal supported source produces a constant zero closure environment, and a load-only lowering assertion crashes the compiler. Distinguish an unhandled producer-reachable alternative from a producer-guaranteed invariant that only needs a low-value assertion.

An optimized/unoptimized mismatch is a useful discovery technique, not a required property of the final minimized reproducer. A smaller source failing at both levels can establish the same root cause more clearly. Human decision and value labels remain independent; accepted high-value yield must count only findings with both labels.

Use `defer` only for reproduced behavior with the unresolved evidence described above.
Without reproduction, record the missing check as an exploration blocker, not a candidate.
Confidence language never substitutes for a command result.