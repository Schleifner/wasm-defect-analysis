#!/usr/bin/env python3
"""Create an immutable envelope for one AI defect-discovery experiment.

The script snapshots the selected prompt and records the model configuration,
scope, and exact compiler submodule commits so the run can be reproduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGET_PATHS = {
    "warpo": Path("upstream/warpo"),
    "wasm-compiler": Path("upstream/wasm-compiler"),
}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def git_output(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def target_metadata(repo_root: Path, name: str) -> dict[str, str]:
    relative_path = TARGET_PATHS[name]
    repository = repo_root / relative_path
    if not repository.is_dir():
        raise ValueError(f"submodule is not initialized: {relative_path}")

    declared_branch = git_output(
        repo_root,
        "config",
        "-f",
        ".gitmodules",
        "--get",
        f"submodule.upstream/{name}.branch",
    )
    return {
        "path": relative_path.as_posix(),
        "remote": git_output(repository, "remote", "get-url", "origin"),
        "declared_branch": declared_branch,
        "commit": git_output(repository, "rev-parse", "HEAD"),
    }


def parse_args() -> argparse.Namespace:
    default_run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="model/provider identifier")
    parser.add_argument("--agent", default="unspecified", help="agent or harness identifier")
    parser.add_argument("--scope", required=True, help="code area or hypothesis budget")
    parser.add_argument(
        "--target",
        choices=("warpo", "wasm-compiler", "pipeline", "both"),
        default="both",
    )
    parser.add_argument("--prompt", type=Path, default=Path("prompts/v2-value-filtered.md"))
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--budget", help="time, token, or cost budget")
    parser.add_argument("--run-id", default=default_run_id)
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        print("error: run id may contain only letters, digits, '.', '_' and '-'", file=sys.stderr)
        return 2
    if args.temperature is not None and args.temperature < 0:
        print("error: temperature cannot be negative", file=sys.stderr)
        return 2
    if args.max_tokens is not None and args.max_tokens <= 0:
        print("error: max-tokens must be positive", file=sys.stderr)
        return 2

    prompt_path = args.prompt if args.prompt.is_absolute() else repo_root / args.prompt
    if not prompt_path.is_file():
        print(f"error: prompt does not exist: {prompt_path}", file=sys.stderr)
        return 2

    selected_targets = (
        ("warpo", "wasm-compiler")
        if args.target in {"both", "pipeline"}
        else (args.target,)
    )

    try:
        targets = {name: target_metadata(repo_root, name) for name in selected_targets}
    except (subprocess.CalledProcessError, ValueError) as error:
        print(f"error: cannot inspect target revisions: {error}", file=sys.stderr)
        return 1

    prompt_bytes = prompt_path.read_bytes()
    prompt_version = prompt_path.stem
    run_dir = args.runs_dir / args.run_id
    if not run_dir.is_absolute():
        run_dir = repo_root / run_dir
    if run_dir.exists():
        print(f"error: run already exists: {run_dir}", file=sys.stderr)
        return 2

    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    shutil.copyfile(prompt_path, run_dir / "prompt.md")

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": args.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "prompt": {
            "source": prompt_path.relative_to(repo_root).as_posix(),
            "snapshot": "prompt.md",
            "version": prompt_version,
            "sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        },
        "model": args.model,
        "execution": {
            "agent": args.agent,
            "temperature": args.temperature,
            "seed": args.seed,
            "max_tokens": args.max_tokens,
            "budget": args.budget,
        },
        "scope": args.scope,
        "target_mode": args.target,
        "targets": targets,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (run_dir / "report.md").write_text(
        f"""# AI Defect Analysis Report: {args.scope}

## Run Metadata

- Run ID: `{args.run_id}`
- Prompt: `{prompt_version}`
- Model: `{args.model}`
- Target: `{args.target}`
- Baseline commits: Warpo `{targets.get('warpo', {}).get('commit', 'N/A')}`, wasm-compiler `{targets.get('wasm-compiler', {}).get('commit', 'N/A')}`

## Analysis Scope

<!-- Record directories, modules, functions, and areas that were not checked. -->

## Candidate Findings

<!-- Include only reproduced accept, downgrade, or defer candidates. Omit hypotheses
the AI rejects. Use one independently minimized source artifact per candidate. Write
"No findings" when no candidate passes the report admission gate. -->

### C-001: <Short title>

- Location:
- Hypothesis:
- Root cause:
- Impact:
- Reproduction: `<artifact>`; `<exact command>`; exit `<code>`; `<focused output>`
- Independent oracle:
- Negative/control case:
- AI recommendation: `accept` / `downgrade` / `defer`
- AI value: `high` / `low` / `unknown`

## Human Review

<!-- Review each candidate here. No additional Python checker is required. -->

### C-001

- Final decision: `accept` / `downgrade` / `reject` / `defer`
- Value: `high` / `low` / `none` / `unknown`
- Review:
- Key evidence:

## Summary

- Reported candidates:
- AI recommendations:
- AI value ratings:
- Areas searched with no findings:
- Unresolved checks and environmental blockers:
- Suggested prompt change for the next round:
""",
        encoding="utf-8",
    )

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
