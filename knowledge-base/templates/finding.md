# <Candidate ID>: <Title>

## Target

- Repository:
- Commit:
- Component / symbol:
- Public input boundary:

## Hypothesis

State the predicted externally observable failure in one falsifiable sentence.

## Design Contract

- Expected behavior:
- Source: specification / documentation / test / code / history
- Conflicting evidence checked:

## Reproduction

- Candidate-specific artifact:
- Non-obvious trigger comments:
- Baseline command:
- Exit code:
- Focused output:

## Independent Oracle

- Oracle type:
- Expected:
- Observed:

## Root Cause

Name the deciding code path and explain the mechanism. For stateful bugs, identify the stored state, the transition that invalidates it, and how the stale or inconsistent state produces the observed result.

## Impact

Describe the externally observable consequence and the kind of input required.

## AI Assessment

- Recommendation: `accept` / `downgrade` / `defer`
- Value: `high` / `low` / `unknown`
- Rationale:

## Human Review

- Decision: `accept` / `downgrade` / `reject` / `defer`
- Verdict:
- Value: `high` / `low` / `none` / `unknown`
- Rationale:

## Regression Proof

- Focused test:
- Negative/control test:
- Broader validation: