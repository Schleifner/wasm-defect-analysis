# Round 003 Human Review

Source run: `runs/round-003-warpo`

## Workflow Feedback

- Remove `Key evidence` from future human-review templates; `Review` is sufficient.
- A bug can be established directly from the implementation invariant and baseline failure. An external JavaScript comparison is useful corroboration, but it is not required when the local contract violation is already clear.
- Do not infer high value merely from a JavaScript semantic difference. Uncommon behavior with no explicit local documentation or specification can be an accepted low-value defect.
- Reward non-obvious runtime state bugs such as iterator invalidation across internal compaction.
- For subtle stateful bugs, explain the old implementation in enough detail to show the stored state, the transition that invalidates it, and the resulting wrong behavior.
- Add concise comments to non-obvious reproducers so the triggering transition and expected observation are clear.

## Decisions

| ID | Candidate | Decision | Value |
| --- | --- | --- | --- |
| R3-001 | String.replaceAll underallocates for a long replacement | `accept` | `high` |
| R3-002 | String.indexOf ignores start for an empty search string | `accept` | `low` |
| R3-003 | Map rehash makes an active iterator skip a live entry | `accept` | `high` |

R3-001 is a preferred finding because the required capacity and the single-growth implementation make the defect self-evident, and ordinary input reproduces the failure. R3-002 is real but low value because the uncommon empty-search usage is not explicitly documented locally and practical use is limited. R3-003 is a preferred non-obvious runtime finding: rehash compacts physical entry positions while an active iterator retains its stale offset, causing a live entry to be skipped.