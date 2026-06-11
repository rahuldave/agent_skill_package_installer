#!/usr/bin/env python3
"""Validate an installable agent skill repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


BLOCK_START = "<<<SKILL_BUNDLE_LINT v1>>>"
BLOCK_END = "<<<END_SKILL_BUNDLE_LINT>>>"
KNOWN_EXECUTABLES = {
    "ast-grep",
    "but",
    "cx",
    "gh",
    "git",
    "gest",
    "jj",
    "jst",
    "just",
    "node",
    "npm",
    "npx",
    "rsync",
    "uv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="skill repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--plan", action="store_true", help="emit package plan instead of lint block")
    parser.add_argument("--run-prereqs", action="store_true", help="run required executable checks")
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_manifest(root: Path, errors: list[str]) -> dict[str, Any]:
    manifest_path = root / "skill-package.json"
    if not manifest_path.exists():
        errors.append("missing root skill-package.json manifest")
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"skill-package.json is invalid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append("skill-package.json must contain a JSON object")
        return {}
    return data


def parse_frontmatter(skill_md: Path, errors: list[str]) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append(f"{skill_md}: missing YAML frontmatter")
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{skill_md}: unterminated YAML frontmatter")
        return {}
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"{skill_md}: unsupported frontmatter line: {line}")
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        fields[key.strip()] = value
    return fields


def discover_skills(root: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for base in (root / "skills", root / ".agents" / "skills"):
        if not base.is_dir():
            continue
        for skill_md in sorted(base.glob("*/SKILL.md")):
            found.append((skill_md.parent.name, skill_md.parent))
    return found


def local_markdown_links(text: str) -> list[str]:
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    result: list[str] = []
    for link in links:
        target = link.split("#", 1)[0].strip()
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        result.append(target)
    return result


def command_mentions(script_text: str, name: str) -> bool:
    escaped = re.escape(name)
    patterns = [
        rf"command\s+-v\s+['\"]?{escaped}['\"]?",
        rf"\b{escaped}\s+--(?:version|help)\b",
        rf"\b{escaped}\s+version\b",
    ]
    return any(re.search(pattern, script_text) for pattern in patterns)


def script_uses_executable(script_text: str, name: str) -> bool:
    escaped = re.escape(name)
    return bool(re.search(rf"(?m)^\s*(?:if\s+!\s+)?{escaped}\b", script_text))


def validate_manifest(root: Path, manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if not manifest:
        return
    if manifest.get("version") != 1:
        errors.append("skill-package.json version must be 1")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        errors.append("manifest.repository must be an object")
    else:
        for key in ("owner", "name", "url"):
            if not repository.get(key):
                errors.append(f"manifest.repository.{key} is required")

    skills = manifest.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("manifest.skills must be a non-empty list")
    else:
        names: set[str] = set()
        for index, skill in enumerate(skills):
            if not isinstance(skill, dict):
                errors.append(f"manifest.skills[{index}] must be an object")
                continue
            name = skill.get("name")
            path_value = skill.get("path")
            if not name or not isinstance(name, str):
                errors.append(f"manifest.skills[{index}].name is required")
                continue
            if name in names:
                errors.append(f"duplicate manifest skill name: {name}")
            names.add(name)
            if not path_value or not isinstance(path_value, str):
                errors.append(f"manifest.skills[{index}].path is required")
                continue
            skill_dir = root / path_value
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                errors.append(f"declared skill {name} missing {path_value}/SKILL.md")
                continue
            frontmatter = parse_frontmatter(skill_md, errors)
            if frontmatter.get("name") != name:
                errors.append(f"{rel(skill_md, root)} frontmatter name does not match manifest skill {name}")
            description = frontmatter.get("description", "")
            if not description or "TODO" in description or "[TODO" in description:
                errors.append(f"{rel(skill_md, root)} has missing or placeholder description")
            elif len(description) < 40:
                warnings.append(f"{name}: description is very short")
            elif len(description) > 600:
                warnings.append(f"{name}: description is long; keep trigger metadata concise")
            for nested in skill_dir.glob("**/SKILL.md"):
                if nested == skill_md:
                    continue
                errors.append(f"{name}: hidden nested skill hierarchy at {rel(nested, root)}")
            text = skill_md.read_text(encoding="utf-8")
            for link in local_markdown_links(text):
                if not (skill_dir / link).exists():
                    errors.append(f"{name}: SKILL.md link does not resolve: {link}")

    discovered = {name for name, _ in discover_skills(root)}
    declared = {skill.get("name") for skill in skills if isinstance(skill, dict)} if isinstance(skills, list) else set()
    missing_from_manifest = sorted(name for name in discovered if name not in declared)
    if missing_from_manifest:
        warnings.append(f"discovered skills not declared in manifest: {', '.join(missing_from_manifest)}")
    npx = manifest.get("npx") if isinstance(manifest, dict) else None
    npx_supported = isinstance(npx, dict) and npx.get("supported") is not False
    if npx_supported and not (root / "skills").is_dir():
        warnings.append("repo has no top-level skills/ directory; npx skills may not discover .agents/skills-only repos")

    installers = manifest.get("installers")
    if not isinstance(installers, list) or not installers:
        errors.append("manifest.installers must be a non-empty list")
        installers = []
    executables = manifest.get("executables")
    required_execs = executable_entries(executables, "required", errors)
    optional_execs = executable_entries(executables, "optional", errors)
    declared_execs = {entry["name"] for entry in required_execs + optional_execs}
    for installer_index, installer in enumerate(installers):
        if not isinstance(installer, dict):
            errors.append(f"manifest.installers[{installer_index}] must be an object")
            continue
        path_value = installer.get("path")
        if not path_value or not isinstance(path_value, str):
            errors.append(f"manifest.installers[{installer_index}].path is required")
            continue
        installer_path = root / path_value
        if not installer_path.exists():
            errors.append(f"installer missing: {path_value}")
            continue
        if not os.access(installer_path, os.X_OK) and installer_path.suffix != ".sh":
            warnings.append(f"installer is not executable and not a .sh script: {path_value}")
        if installer.get("checks_prerequisites") is not True:
            errors.append(f"installer must set checks_prerequisites true: {path_value}")
        script_text = installer_path.read_text(encoding="utf-8", errors="replace")
        if "set -euo pipefail" not in script_text and installer_path.suffix == ".sh":
            warnings.append(f"shell installer should use set -euo pipefail: {path_value}")
        for entry in required_execs:
            if not command_mentions(script_text, entry["name"]):
                errors.append(f"installer {path_value} does not check required executable: {entry['name']}")
        for entry in optional_execs:
            if not command_mentions(script_text, entry["name"]):
                warnings.append(f"installer {path_value} does not mention optional executable: {entry['name']}")
        for name in sorted(KNOWN_EXECUTABLES - declared_execs):
            if script_uses_executable(script_text, name):
                warnings.append(f"installer {path_value} uses undeclared executable: {name}")

    if isinstance(npx, dict):
        install = npx.get("install")
        if npx.get("supported") is False:
            pass
        elif install and "npx skills add" not in install:
            warnings.append("manifest.npx.install should contain an npx skills add command")
        elif not install:
            warnings.append("manifest.npx.install command is missing")
    else:
        warnings.append("manifest.npx install command is missing")


def executable_entries(executables: Any, key: str, errors: list[str]) -> list[dict[str, str]]:
    if not isinstance(executables, dict):
        errors.append("manifest.executables must be an object")
        return []
    value = executables.get(key, [])
    if not isinstance(value, list):
        errors.append(f"manifest.executables.{key} must be a list")
        return []
    entries: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"manifest.executables.{key}[{index}] must be an object")
            continue
        name = item.get("name")
        check = item.get("check")
        if not name or not isinstance(name, str):
            errors.append(f"manifest.executables.{key}[{index}].name is required")
            continue
        if not check or not isinstance(check, str):
            errors.append(f"manifest.executables.{key}[{index}].check is required")
            continue
        entries.append({"name": name, "check": check})
    return entries


def run_prereqs(manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    executables = manifest.get("executables") if isinstance(manifest, dict) else {}
    for kind in ("required", "optional"):
        for entry in executable_entries(executables, kind, errors):
            name = entry["name"]
            check = entry["check"]
            if shutil.which(name) is None:
                results[name] = "missing"
                if kind == "required":
                    errors.append(f"required executable not found on PATH: {name}")
                else:
                    warnings.append(f"optional executable not found on PATH: {name}")
                continue
            try:
                subprocess.run(shlex.split(check), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=20)
            except Exception as exc:  # noqa: BLE001 - report any failed check compactly
                results[name] = "check-failed"
                if kind == "required":
                    errors.append(f"required executable check failed for {name}: {exc}")
                else:
                    warnings.append(f"optional executable check failed for {name}: {exc}")
            else:
                results[name] = "pass"
    return results


def build_result(root: Path, run_checks: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        errors.append(f"repo root does not exist: {root}")
        return {"status": "fail", "errors": errors, "warnings": warnings}
    manifest = load_manifest(root, errors)
    validate_manifest(root, manifest, errors, warnings)
    prereq_results = run_prereqs(manifest, errors, warnings) if run_checks and manifest else {}
    return {
        "status": "fail" if errors else "pass",
        "repo_root": str(root),
        "manifest": manifest,
        "skills": [name for name, _ in discover_skills(root)],
        "errors": errors,
        "warnings": warnings,
        "prereqs": prereq_results,
    }


def emit_text(result: dict[str, Any]) -> None:
    print(BLOCK_START)
    print(f"status: {result['status']}")
    print(f"repo_root: {result.get('repo_root', '')}")
    print("skills:")
    for skill in result.get("skills", []):
        print(f"  - {skill}")
    print("errors:")
    for error in result["errors"]:
        print(f"  - {error}")
    if not result["errors"]:
        print("  []")
    print("warnings:")
    for warning in result["warnings"]:
        print(f"  - {warning}")
    if not result["warnings"]:
        print("  []")
    if result.get("prereqs"):
        print("prereqs:")
        for name, status in result["prereqs"].items():
            print(f"  {name}: {status}")
    print(BLOCK_END)


def emit_plan(result: dict[str, Any]) -> None:
    manifest = result.get("manifest", {})
    print("<<<SKILL_PACKAGE_PLAN v1>>>")
    print(f"repo_root: {result.get('repo_root', '')}")
    repository = manifest.get("repository", {}) if isinstance(manifest, dict) else {}
    print("repository:")
    print(f"  owner: {repository.get('owner', '')}")
    print(f"  name: {repository.get('name', '')}")
    print(f"  url: {repository.get('url', '')}")
    print("skills:")
    for skill in manifest.get("skills", []) if isinstance(manifest, dict) else []:
        print(f"  - name: {skill.get('name', '')}")
        print(f"    path: {skill.get('path', '')}")
    print("installers:")
    for installer in manifest.get("installers", []) if isinstance(manifest, dict) else []:
        print(f"  - path: {installer.get('path', '')}")
        print(f"    checks_prerequisites: {str(installer.get('checks_prerequisites') is True).lower()}")
    npx = manifest.get("npx", {}) if isinstance(manifest, dict) else {}
    print("npx:")
    print(f"  command: {npx.get('install', '')}")
    print("lint:")
    print(f"  status: {result['status']}")
    print(f"  error_count: {len(result['errors'])}")
    print(f"  warning_count: {len(result['warnings'])}")
    print("<<<END_SKILL_PACKAGE_PLAN>>>")


def main() -> int:
    args = parse_args()
    root = Path(args.repo).expanduser().resolve()
    result = build_result(root, args.run_prereqs)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.plan:
        emit_plan(result)
    else:
        emit_text(result)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
