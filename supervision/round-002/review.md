# Round 002 Human Review

Source run: `runs/round-002-warpo`

## Workflow Feedback

- Omit hypotheses that the AI has already rejected. Preserve genuinely uncertain reproduced cases for human review as `defer`.
- Give every bug an independently minimized AssemblyScript source file instead of combining candidates in one multi-export harness.
- Rate candidate value independently from the technical recommendation.
- Treat supported-input reachability as an admission requirement instead of a separate report field.
- Combine the reproducer path, exact baseline command, exit code, and focused result into one reproduction entry.
- Prioritize ordinary semantically valid programs with surprising compiler behavior over bugs that require extreme arguments or conspicuously erroneous code.

## Decisions

| ID | Candidate | Decision | Value |
| --- | --- | --- | --- |
| R2-001 | Postfix property update evaluates its receiver twice | `accept` | `high` |
| R2-002 | TypedArray.copyWithin traps on an empty source range | `accept` | `low` |
| R2-003 | Typed-array bounds checks are bypassed by signed overflow | `accept` | `low` |
| R2-004 | Plain property assignment reverses receiver and RHS evaluation | `reject` | `none` |
| R2-005 | Uint16Array.reverse uses a mis-scaled front address | `reject` | `none` |

R2-001 is the preferred discovery pattern: ordinary supported source has unambiguous evaluation semantics and produces an observable miscompile. R2-002 and R2-003 are real defects, but their triggering inputs make them lower-value search targets. R2-004 and R2-005 were falsified by direct execution and should not have appeared in Candidate Findings under the revised report policy.