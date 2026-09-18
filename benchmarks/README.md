# Benchmarks

Benchmarks preserve human judgment independently from model output.

## Splits

- `training`: labels may be summarized in prompts. Use only to check that known lessons are retained.
- `validation`: frozen tasks used to select between prompt versions. Keep labels out of prompts.
- `holdout`: opened only after selecting a prompt. Use for the final generalization estimate.
- `exploration`: new discovery scope without exhaustive ground truth. Precision and yield are valid after review; recall is not.

`round-001` is a **training/supervision set**, not an unbiased evaluation. Its source is [../work.md](../work.md), and its eight human judgments are encoded in [round-001/oracle.json](round-001/oracle.json).

## New Cases

Each replayable case should record:

- stable ID, target repository, and exact baseline commit;
- public input level (`assemblyscript` or `wasm`);
- minimal reproducer and setup command;
- failure oracle and a nearby negative/control case;
- human decision, verdict, value, and rationale;
- focused baseline and post-fix commands.

Keep oracle labels inaccessible to the discovery agent for validation and holdout runs. When a case is promoted from exploration, freeze it before comparing another prompt.