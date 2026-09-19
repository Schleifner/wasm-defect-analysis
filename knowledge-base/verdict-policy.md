# Verdict Policy

## Core Rule

A reportable compiler bug needs all three: supported-input reachability, a contract violation, and an observed failure with an independent oracle.

Reachability remains a mandatory admission check, but it is not a separate report field. A candidate enters the report only after a minimal supported input reproduces it on the pinned baseline.

## Report Filter

- Report only reproduced candidates recommended as `accept`, `downgrade`, or `defer`.
- Omit hypotheses the AI concludes are intended, unsupported, producer-impossible, falsified, duplicate, or otherwise non-actionable.
- Use `defer` only when the behavior is reproduced but a decisive contract or oracle check remains unresolved. State the missing evidence.
- If no candidate passes the gate, write `No findings` and summarize the areas searched.
- Give every reported candidate its own independently minimized source artifact. Do not combine multiple bugs in one source file or multi-export harness.

## Warpo Boundary

Warpo's source frontend is the producer for its internal optimization passes. A hand-written WAT or constructed Binaryen IR case is not sufficient when it violates a frontend invariant. First attempt to generate the shape from supported AssemblyScript. If that fails, inspect and cite the producer path before classifying the candidate.

## wasm-compiler Boundary

wasm-compiler accepts supported WebAssembly bytecode directly. A valid Wasm module assembled from WAT is therefore a legitimate reproducer. Check the documented feature matrix and build configuration before treating an unsupported proposal as a defect.

## Decision And Value

Decision and value are independent:

- **Accept:** a supported input reproducibly exposes an actionable compiler or standard-library defect.
- **Downgrade:** a reproduced robustness or documentation concern is real but does not warrant treatment as a user-visible compiler bug.
- **Defer:** behavior is reproduced, but decisive evidence about the contract, intent, or oracle is unavailable.
- **Reject internally:** expected behavior, unsupported input, a producer-impossible state, a falsified hypothesis, or a non-actionable diagnostic. Do not include it in Candidate Findings.

Rate each reported candidate separately:

- **High value:** ordinary semantically valid input crashes, miscompiles, emits invalid output, violates clear evaluation semantics, or breaks a realistic workflow.
- **Low value:** impact primarily requires extreme boundary values, conspicuously erroneous or nonsensical user code, narrow robustness behavior, or low-impact diagnostics.
- **Unknown value:** use only with `defer` when missing evidence prevents classification.

Prioritize high-value findings. An accepted bug can still be low value.

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

When evidence is incomplete, use `defer`. Confidence language never substitutes for a command result.