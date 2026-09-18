#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

git -C "$repo_root" submodule update --init upstream/warpo upstream/wasm-compiler

update_submodule() {
  local name="$1"
  local path
  local branch

  path="$(git -C "$repo_root" config -f .gitmodules --get "submodule.${name}.path")"
  branch="$(git -C "$repo_root" config -f .gitmodules --get "submodule.${name}.branch")"

  if [[ -n "$(git -C "$repo_root/$path" status --porcelain)" ]]; then
    printf 'error: refusing to update dirty submodule %s\n' "$path" >&2
    return 1
  fi

  git -C "$repo_root/$path" fetch origin "$branch"
  if git -C "$repo_root/$path" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$repo_root/$path" switch "$branch"
    git -C "$repo_root/$path" merge --ff-only "origin/$branch"
  else
    git -C "$repo_root/$path" switch --create "$branch" --track "origin/$branch"
  fi

  if [[ "$(git -C "$repo_root/$path" rev-parse HEAD)" != "$(git -C "$repo_root/$path" rev-parse "origin/$branch")" ]]; then
    printf 'error: %s contains commits not present at origin/%s\n' "$path" "$branch" >&2
    return 1
  fi

  printf '%-24s %s (%s)\n' "$path" "$(git -C "$repo_root/$path" rev-parse HEAD)" "$branch"
}

update_submodule "upstream/warpo"
update_submodule "upstream/wasm-compiler"