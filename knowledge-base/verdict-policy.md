# Verdict Policy

## Core Rule

A reportable compiler bug needs all three: supported-input reachability, a contract violation, and an observed failure with an independent oracle.

## Warpo Boundary

Warpo's source frontend is the producer for its internal optimization passes. A hand-written WAT or constructed Binaryen IR case is not sufficient when it violates a frontend invariant. First attempt to generate the shape from supported AssemblyScript. If that fails, inspect and cite the producer path before classifying the candidate.

## wasm-compiler Boundary

wasm-compiler accepts supported WebAssembly bytecode directly. A valid Wasm module assembled from WAT is therefore a legitimate reproducer. Check the documented feature matrix and build configuration before treating an unsupported proposal as a defect.

## Decision Examples From Round 001

- **Accept:** valid source crashes instead of producing a required diagnostic.
- **Accept:** valid source is miscompiled and an executed module returns the wrong value or evaluation order.
- **Downgrade:** a pass lacks an assertion for an invariant guaranteed by its only producer.
- **Reject:** behavior is an intentional optimization policy, even if the policy needs documentation.
- **Reject:** only synthetic IR or WAT can produce the state for a source-only pipeline.
- **Reject:** duplicate diagnostics for an already unsupported construct without semantic or robustness impact.

When evidence is incomplete, use `defer`. Confidence language never substitutes for a command result.