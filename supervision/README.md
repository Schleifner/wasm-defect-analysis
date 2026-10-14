# Human Supervision

This directory preserves reviewed labels independently from model output. It is intentionally compact: reproduction artifacts remain in the corresponding local run and are not copied here.

## Splits

- `training`: labels may be summarized in prompts. Use only to check that known lessons are retained.
- `validation`: frozen tasks used to select between revisions of the discovery prompt. Keep labels out of the prompt.
- `holdout`: opened only after selecting a prompt. Use for the final generalization estimate.
- `exploration`: new discovery scope without exhaustive ground truth. Precision and yield are valid after review; recall is not.

Each completed round contains only:

- `review.md`: the human-readable decisions and workflow feedback;
- `oracle.json`: structured labels consumed by prompt iteration and evaluation tooling.

`round-001` is a **training set**, not an unbiased evaluation. Its eight reviewed judgments are stored in [round-001](round-001).

`round-002` is also a **training set** because its reviewed lessons are included in the current prompt. Its five reviewed judgments are stored in [round-002](round-002).

`round-003` is a **training set** because its reviewed lessons are included in the current prompt. Its three reviewed judgments are stored in [round-003](round-003).

`round-004` is a **training set** because its reviewed lessons are included in the current prompt. Its four retained judgments are stored in [round-004](round-004): two accepted high-value defects and two rejected candidates. One rejection retains a high exploratory-value rating, so the oracle records both all high-value ratings and the accepted high-value count separately. Stable candidate IDs need not be contiguous.

## Adding A Round

After human review, add one round directory containing `review.md` and `oracle.json`. The oracle records stable IDs, target commit, decision, value, and concise supervision rationale. The review explains the decisions and reusable workflow feedback.

Promote retained candidate judgments from the human review, not stale summary counts. Preserve human decision and value labels independently, along with any issue links. Do not rewrite a reviewed run or its prompt snapshot while incorporating lessons into the current source prompt.

Keep oracle labels inaccessible to the discovery agent for validation and holdout runs. When a case is promoted from exploration, freeze it before comparing another prompt.