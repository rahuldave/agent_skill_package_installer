#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/install.sh /path/to/target/repo

Install the skill-package-installer skill into a target repository's
.agents/skills directory. Existing non-package-installer skills are preserved.
USAGE
}

check_required() {
  local missing=()
  if ! command -v uv >/dev/null 2>&1; then
    missing+=("uv")
  fi
  if ! command -v npx >/dev/null 2>&1; then
    missing+=("npx")
  fi
  if ! command -v rsync >/dev/null 2>&1; then
    missing+=("rsync")
  fi
  if [ "${#missing[@]}" -gt 0 ]; then
    printf 'Missing required executable(s): %s\n' "${missing[*]}" >&2
    printf 'Install uv and npx before installing this skill. uv supplies Python for the linter.\n' >&2
    exit 69
  fi
}

warn_optional() {
  if ! command -v git >/dev/null 2>&1; then
    printf 'Optional executable not found: git\n' >&2
  fi
  if ! command -v gh >/dev/null 2>&1; then
    printf 'Optional executable not found: gh\n' >&2
  fi
  if ! command -v gest >/dev/null 2>&1; then
    printf 'Optional executable not found: gest\n' >&2
  fi
  if ! command -v just >/dev/null 2>&1; then
    printf 'Optional executable not found: just\n' >&2
  fi
  if ! command -v cx >/dev/null 2>&1; then
    printf 'Optional executable not found: cx\n' >&2
  fi
}

if [ "$#" -ne 1 ]; then
  usage
  exit 64
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$1"

if [ ! -d "$target" ]; then
  echo "Target does not exist: $target" >&2
  exit 66
fi

check_required
warn_optional

mkdir -p "$target/.agents/skills"
rsync -a --delete "$repo_root/skills/skill-package-installer/" "$target/.agents/skills/skill-package-installer/"

echo "Installed skill-package-installer into $target/.agents/skills/skill-package-installer"
echo "Run: uv run python .agents/skills/skill-package-installer/scripts/lint_skill_bundle.py ."
