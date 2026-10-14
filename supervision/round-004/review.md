# Round 004 Human Review

Source run: `runs/round-004-warpo`

## Workflow Feedback

- Check source, object-layout, and backend contracts before interpreting an O0/O3 or reference-runtime mismatch as a defect.
- Compiler-generated static function objects are immutable. Raw writes to `_index` or `_env` are unsupported, even when the source compiles and different optimization levels produce different results.
- Imported-call analysis must account for the intended backend's host-integration restrictions. Node's support for synchronous re-entry does not override Warpo's no-nested-Wasm-call assumption.
- Reward missing GC roots caused by a mismatch between frontend type representation and runtime tracing. A managed function reference need not have a class reference.
- Separate the root cause from a masking temporary root or optimization trigger. A smaller global-closure/collection test can expose the root omission at both optimization levels.
- Supported ordinary source reaching an internal assertion is an actionable high-value defect when the frontend legitimately emits the unhandled operand, including a constant zero environment.
- Use native compiler exit status and output existence when investigating compiler crashes; the JavaScript wrapper can conceal a native assertion failure.
- Preserve explanatory names and concise comments in minimized reproducers. Explain the global root, captured state, collection, and replacement transition rather than retaining scaffolding only to create an O0/O3 distinction.

## Decisions

| ID | Candidate | Decision | Value | Issue |
| --- | --- | --- | --- | --- |
| R4-001 | Immutable-load elimination after raw writes to static function objects | `reject` | `high` | [#656](https://github.com/wasm-ecosystem/warpo/issues/656) |
| R4-002 | Imported-call GC leaf filtering under unsupported nested Wasm re-entry | `reject` | `none` | |
| R4-003 | Global GC root scanning omits managed function references | `accept` | `high` | |
| R4-005 | Set-only closure lowering rejects a frontend-produced zero environment | `accept` | `high` | [#671](https://github.com/wasm-ecosystem/warpo/issues/671) |

R4-001 retains the human's high exploratory-value rating despite being rejected: the differential investigation was useful, but its unsupported memory mutation does not require changing the optimization. R4-002 is rejected because the host workflow violates an intentional backend restriction. R4-003 and R4-005 are accepted high-value defects reached by supported closure source.

The oracle contains the four retained candidate judgments. Promotion follows the Candidate Findings and Human Review sections, not the report's historical five-candidate summary. Stable candidate IDs are preserved rather than renumbered. The reviewed report, chronological analysis log, manifest, and prompt snapshot remain unchanged.
