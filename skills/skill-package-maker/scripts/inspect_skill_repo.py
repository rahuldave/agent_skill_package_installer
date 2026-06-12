#!/usr/bin/env python3
"""Inspect a skill repository and emit JSON lint metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lint_skill_bundle  # noqa: E402


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    result = lint_skill_bundle.build_result(Path(repo).expanduser().resolve(), run_checks=False)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

