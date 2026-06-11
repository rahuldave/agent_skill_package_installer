#!/usr/bin/env python3
"""Run a scratch installer test for a skill repository."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lint_skill_bundle  # noqa: E402


def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").expanduser().resolve()
    result = lint_skill_bundle.build_result(repo, run_checks=False)
    if result["status"] != "pass":
        lint_skill_bundle.emit_text(result)
        return 1
    manifest = result["manifest"]
    installers = manifest.get("installers", [])
    if not installers:
        print("no installers declared")
        return 1
    installer = repo / installers[0]["path"]
    with tempfile.TemporaryDirectory(prefix="skill-package-install-test-") as tmp:
        target = Path(tmp) / "target"
        target.mkdir()
        subprocess.run([str(installer), str(target)], cwd=repo, check=True)
        missing: list[str] = []
        for skill in manifest.get("skills", []):
            installed = target / ".agents" / "skills" / skill["name"] / "SKILL.md"
            if not installed.exists():
                missing.append(str(installed))
        output = {"status": "fail" if missing else "pass", "missing": missing, "target": str(target)}
        print(json.dumps(output, indent=2, sort_keys=True))
        return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

