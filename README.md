# WASM Defect Analysis

This repository is an evidence-first laboratory for improving AI-assisted bug discovery in two adjacent compiler projects:

| Target | Role | Tracked branch | Local path |
| --- | --- | --- | --- |
| [Warpo](https://github.com/wasm-ecosystem/warpo) | AssemblyScript to WebAssembly frontend and optimization pipeline | `main` | `upstream/warpo/` |
| [wasm-compiler](https://github.com/wasm-ecosystem/wasm-compiler) | WebAssembly to native artifact compiler and runtime | `develop` | `upstream/wasm-compiler/` |

The goal is not to maximize the number of plausible findings. AI writes a formatted Markdown report, and a human reads the evidence and makes the final judgment.

## Start Here

```bash
git clone <this-repository-url>
cd wasm-defect-analysis
git submodule update --init upstream/warpo upstream/wasm-compiler
python3 scripts/new_run.py \
	--model <provider/model> \
	--agent <agent-or-harness> \
	--target warpo \
	--scope "frontend parser and object literal lowering" \
	--temperature 0 \
	--budget "60 minutes"
```

If the repository was cloned without submodules:

```bash
git submodule update --init upstream/warpo upstream/wasm-compiler
```

Do not initialize recursively from the parent repository: Warpo vendors Binaryen as a subtree, and Binaryen retains nested gitlinks whose metadata is not owned by Warpo's root. Initialize any dependencies required by an upstream build from that upstream's documented setup instead.

To advance both tracked branches deliberately:

```bash
./scripts/update_upstreams.sh
```

Review the resulting submodule commit changes before committing them. Every discovery run records exact commit hashes, so a later upstream update does not change old experimental context.

## Iteration Loop

1. **Freeze the experiment.** `scripts/new_run.py` snapshots the selected prompt and records model, scope, branch, and exact target commits.
2. **Discover without editing upstream.** Give the agent the run's `prompt.md`; it reports only reproduced candidates that survive its admission gate. Reproduction artifacts remain local under `artifacts/` and are not committed.
3. **Review directly.** Read `report.md`, check the evidence and reproduction, and fill its human judgment and summary sections. No extra Python validation or scoring step is required.
4. **Learn.** Compare human decisions across reports, add reusable lessons to `knowledge-base/`, and create a new prompt file. Never overwrite an old prompt or run.
5. **Protect generalization.** Use `round-001` as training/regression supervision only. Compare prompt versions on frozen validation or holdout scopes whose labels were not included in the prompt.

See [docs/CN-workflow.md](docs/CN-workflow.md) for the current step-by-step operating procedure, [docs/methodology.md](docs/methodology.md) for its design rationale, and [supervision/README.md](supervision/README.md) for split and leakage rules.

## VS Code Copilot Agent Interaction

The repository does not call an LLM from Python. `scripts/new_run.py` only prepares the experiment context:

1. It records the model name, agent name, scope, sampling settings, and exact upstream commits in `manifest.json`.
2. It copies the selected prompt to `prompt.md`.
3. It creates the `report.md` template and an `artifacts/` directory.

The actual model interaction happens when you open the workspace in VS Code and use Copilot in Agent mode. Start a new Agent task with the selected run directory as context and ask it to:

```text
Read runs/<run-id>/manifest.json and runs/<run-id>/prompt.md. Analyze only the declared target and scope. Write the complete result to runs/<run-id>/report.md, following its headings. Do not modify upstream source during discovery.
```

The Agent uses its normal VS Code tools, such as file search, file reading, terminal commands, and tests. It is not launched by `new_run.py`. After the Agent finishes, open `report.md`, verify the evidence and commands, and fill the `Human Review` section yourself.

By default, the run generator selects the latest prompt version. Use `--prompt` explicitly only when replaying or comparing a particular immutable prompt version.

## First-Round Supervision

[supervision/round-001/review.md](supervision/round-001/review.md) is the human-readable source of truth. [supervision/round-001/oracle.json](supervision/round-001/oracle.json) preserves its eight judgments in machine-readable form:

- `accept`: findings 1 and 5, both high-value and reachable from valid source;
- `downgrade`: finding 2, a correct but low-value internal robustness invariant;
- `reject`: findings 3, 4, 6, 7, and 8 because behavior is intended, impact is cosmetic, or the proposed input violates the producer contract.

This yields a 25% high-value baseline and a 50% producer-unreachable candidate rate. The first prompt therefore focuses on reachability, design intent, and executable oracles.

## Second-Round Supervision

[Round 002](supervision/round-002/oracle.json) adds output and value calibration to the reachability discipline:

- omit hypotheses the AI has already rejected instead of spending human review space on them;
- use one independently minimized source file per reported bug;
- treat supported-input reachability as an admission gate rather than a repeated report field;
- combine artifact, exact command, exit code, and focused output into one reproduction entry;
- distinguish technical acceptance from value, and prioritize ordinary valid programs with surprising compiler behavior over extreme or conspicuously erroneous inputs.

## Repository Layout

```text
docs/             Methodology and research provenance
knowledge-base/   Reusable compiler-specific lessons and report templates
prompts/          Immutable, versioned discovery prompts
runs/             Per-run manifests, prompt snapshots, and reviewed reports
scripts/          Run creation and upstream updates
supervision/      Human reviews, labels, and evaluation splits
upstream/         Pinned compiler submodules
```

## Upstream Build References

Use each project's own instructions and keep build output inside its submodule:

```bash
# Warpo
cd upstream/warpo
npm ci
cmake -S . -B build
cmake --build build --parallel
npm test

# wasm-compiler: see its platform and feature-specific setup
cd ../wasm-compiler
python3 scripts/test.py --no-color
```

Prefer the smallest focused upstream test that falsifies a candidate before running a full suite.
