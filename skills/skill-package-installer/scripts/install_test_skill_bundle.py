#!/usr/bin/env python3
"""Run a scratch installer test for a skill repository."""

from __future__ import annotations

import json
import os
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
    npx = manifest.get("npx", {})
    npx_supported = isinstance(npx, dict) and npx.get("supported") is not False
    with tempfile.TemporaryDirectory(prefix="skill-package-install-test-") as tmp:
        target = Path(tmp) / "target"
        target.mkdir()
        if npx_supported:
            if shutil.which("npx") is None:
                print(json.dumps({"status": "fail", "error": "npx not found on PATH"}, indent=2, sort_keys=True))
                return 1
            command = ["npx", "skills", "add", str(repo), "-a", "codex", "--copy", "-y"]
            for skill in manifest.get("skills", []):
                command.extend(["--skill", skill["name"]])
            env = os.environ.copy()
            env["NPM_CONFIG_CACHE"] = str(Path(tmp) / "npm-cache")
            env["DISABLE_TELEMETRY"] = "1"
            completed = subprocess.run(command, cwd=target, env=env, text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                output = {
                    "status": "fail",
                    "mode": "npx",
                    "command": command,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "target": str(target),
                }
                print(json.dumps(output, indent=2, sort_keys=True))
                return 1
        else:
            if not installers:
                print(json.dumps({"status": "fail", "error": "no npx support or copy-based installer declared"}, indent=2, sort_keys=True))
                return 1
            installer = repo / installers[0]["path"]
            subprocess.run([str(installer), str(target)], cwd=repo, check=True)
        missing: list[str] = []
        for skill in manifest.get("skills", []):
            installed = target / ".agents" / "skills" / skill["name"] / "SKILL.md"
            if not installed.exists():
                missing.append(str(installed))
        output = {
            "status": "fail" if missing else "pass",
            "mode": "npx" if npx_supported else "copy-installer",
            "missing": missing,
            "target": str(target),
        }
        print(json.dumps(output, indent=2, sort_keys=True))
        return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
