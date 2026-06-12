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
    "cargo",
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
    "rustc",
    "rustup",
    "uv",
}
SKILL_LOCAL_PREFIXES = ("assets/", "references/", "scripts/")
REPO_ROOT_RUNTIME_PREFIXES = ("docs/", "templates/", "tools/")
INLINE_PATH_RE = re.compile(
    r"`((?:assets|docs|references|scripts|templates|tools)/[A-Za-z0-9_./-]+)`"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="skill repository root")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--plan", action="store_true", help="emit package plan instead of lint block")
    parser.add_argument("--run-prereqs", action="store_true", help="run required executable checks")
    parser.add_argument("--check-skill-deps", action="store_true", help="verify declared skill dependencies are installed or available")
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
        raw_value = value.strip()
        if raw_value and not raw_value.startswith(("'", '"', "|", ">")) and ": " in raw_value:
            errors.append(f"{skill_md}: frontmatter value for {key.strip()} contains ': ' and must be quoted or rewritten")
        value = raw_value.strip('"').strip("'")
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


def inline_local_paths(text: str) -> list[str]:
    return [match.group(1) for match in INLINE_PATH_RE.finditer(text)]


def validate_skill_file_references(
    skill_name: str,
    skill_dir: Path,
    text: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    for link in local_markdown_links(text):
        if not (skill_dir / link).exists():
            errors.append(f"{skill_name}: SKILL.md link does not resolve: {link}")
    for path_value in inline_local_paths(text):
        if path_value.startswith(REPO_ROOT_RUNTIME_PREFIXES):
            errors.append(
                f"{skill_name}: SKILL.md references repo-root runtime file {path_value}; "
                "bundle installed-skill support material under references/, scripts/, or assets/"
            )
        if path_value.startswith(SKILL_LOCAL_PREFIXES) and not (skill_dir / path_value).exists():
            errors.append(f"{skill_name}: SKILL.md bundled resource does not resolve: {path_value}")

    references_dir = skill_dir / "references"
    if references_dir.is_dir():
        for reference in sorted(references_dir.glob("*.md")):
            validate_reference_file(skill_name, skill_dir, reference, errors, warnings)

    for nested_reference in sorted(skill_dir.glob("references/**/*.md")):
        if nested_reference.parent == references_dir:
            continue
        warnings.append(
            f"{skill_name}: nested reference file is deeper than one level from SKILL.md: "
            f"{nested_reference.relative_to(skill_dir).as_posix()}"
        )


def validate_reference_file(
    skill_name: str,
    skill_dir: Path,
    reference: Path,
    errors: list[str],
    warnings: list[str],
) -> None:
    text = reference.read_text(encoding="utf-8")
    rel_reference = reference.relative_to(skill_dir).as_posix()
    for link in local_markdown_links(text):
        if not (reference.parent / link).exists():
            errors.append(f"{skill_name}: {rel_reference} link does not resolve: {link}")
    for path_value in inline_local_paths(text):
        if path_value.startswith("docs/"):
            errors.append(
                f"{skill_name}: {rel_reference} references repo-root docs path {path_value}; "
                "copy the reference closure under this skill's references/ and use sibling links"
            )
        elif path_value.startswith(("templates/", "tools/")):
            warnings.append(
                f"{skill_name}: {rel_reference} mentions repo-root path {path_value}; "
                "move installed runtime material under the skill when it is required"
            )
        elif path_value.startswith("scripts/") and (skill_dir / path_value).exists():
            warnings.append(
                f"{skill_name}: {rel_reference} mentions bundled script as {path_value}; "
                f"use ../{path_value} for a Markdown-relative path from references/"
            )


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


def skill_dependency_roots(root: Path) -> list[Path]:
    roots: list[Path] = []
    for candidate in (root / "skills", root / ".agents" / "skills"):
        roots.append(candidate)
    env_paths = os.environ.get("SKILL_PACKAGE_DEPENDENCY_PATHS", "")
    for value in env_paths.split(os.pathsep):
        if value:
            roots.append(Path(value).expanduser())
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    home = Path.home()
    roots.extend([home / ".codex" / "skills", home / ".agents" / "skills"])

    normalized: list[Path] = []
    seen: set[Path] = set()
    for candidate in roots:
        resolved = candidate.expanduser().resolve()
        if resolved not in seen:
            seen.add(resolved)
            normalized.append(resolved)
    return normalized


def find_skill(skill_name: str, roots: list[Path]) -> Path | None:
    for root in roots:
        if (root / "SKILL.md").exists() and root.name == skill_name:
            return root / "SKILL.md"
        candidate = root / skill_name / "SKILL.md"
        if candidate.exists():
            return candidate
    return None


def validate_skill_dependencies(
    root: Path,
    manifest: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    check_installed: bool,
) -> list[dict[str, Any]]:
    dependencies = manifest.get("skill_dependencies", []) if isinstance(manifest, dict) else []
    if dependencies in (None, []):
        return []
    if not isinstance(dependencies, list):
        errors.append("manifest.skill_dependencies must be a list")
        return []

    roots = skill_dependency_roots(root)
    statuses: list[dict[str, Any]] = []
    for dep_index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            errors.append(f"manifest.skill_dependencies[{dep_index}] must be an object")
            continue
        dep_name = dependency.get("name")
        if not dep_name or not isinstance(dep_name, str):
            errors.append(f"manifest.skill_dependencies[{dep_index}].name is required")
            dep_name = f"dependency[{dep_index}]"
        required = dependency.get("required", True) is not False
        alternatives = dependency.get("any_of")
        direct_skills = dependency.get("skills")
        if alternatives is None and direct_skills is not None:
            alternatives = [{"name": dep_name, "skills": direct_skills, "markers": dependency.get("markers", [])}]
        if not isinstance(alternatives, list) or not alternatives:
            errors.append(f"manifest.skill_dependencies[{dep_index}].any_of must be a non-empty list")
            continue

        dep_status: dict[str, Any] = {
            "name": dep_name,
            "required": required,
            "status": "not-run" if not check_installed else "missing",
            "alternatives": [],
        }
        matched = False
        for alt_index, alternative in enumerate(alternatives):
            alt_status = validate_dependency_alternative(
                alternative,
                dep_index,
                alt_index,
                roots,
                errors,
                check_installed,
            )
            dep_status["alternatives"].append(alt_status)
            if alt_status["status"] == "pass":
                matched = True
        if check_installed:
            dep_status["status"] = "pass" if matched else "missing"
            if required and not matched:
                errors.append(f"required skill dependency not satisfied: {dep_name}")
            elif not required and not matched:
                warnings.append(f"optional skill dependency not satisfied: {dep_name}")
        statuses.append(dep_status)
    return statuses


def validate_dependency_alternative(
    alternative: Any,
    dep_index: int,
    alt_index: int,
    roots: list[Path],
    errors: list[str],
    check_installed: bool,
) -> dict[str, Any]:
    if not isinstance(alternative, dict):
        errors.append(f"manifest.skill_dependencies[{dep_index}].any_of[{alt_index}] must be an object")
        return {"name": f"alternative[{alt_index}]", "status": "invalid", "missing": []}
    alt_name = alternative.get("name") or alternative.get("repository") or f"alternative[{alt_index}]"
    skills = alternative.get("skills")
    if not isinstance(skills, list) or not skills or not all(isinstance(skill, str) for skill in skills):
        errors.append(f"manifest.skill_dependencies[{dep_index}].any_of[{alt_index}].skills must be a non-empty string list")
        return {"name": alt_name, "status": "invalid", "missing": []}
    markers = alternative.get("markers", [])
    if not isinstance(markers, list):
        errors.append(f"manifest.skill_dependencies[{dep_index}].any_of[{alt_index}].markers must be a list")
        markers = []
    for marker_index, marker in enumerate(markers):
        if not isinstance(marker, dict) or not marker.get("skill") or not marker.get("contains"):
            errors.append(
                f"manifest.skill_dependencies[{dep_index}].any_of[{alt_index}].markers[{marker_index}] "
                "must contain skill and contains"
            )

    status: dict[str, Any] = {"name": alt_name, "status": "not-run", "missing": [], "markers": []}
    if not check_installed:
        return status

    missing: list[str] = []
    skill_paths: dict[str, Path] = {}
    for skill in skills:
        found = find_skill(skill, roots)
        if found is None:
            missing.append(skill)
        else:
            skill_paths[skill] = found
    marker_failures: list[str] = []
    for marker in markers:
        if not isinstance(marker, dict):
            continue
        skill = marker.get("skill")
        contains = marker.get("contains")
        if not isinstance(skill, str) or not isinstance(contains, str):
            continue
        skill_path = skill_paths.get(skill) or find_skill(skill, roots)
        if skill_path is None:
            marker_failures.append(f"{skill}: missing for marker {contains}")
            continue
        text = skill_path.read_text(encoding="utf-8", errors="replace")
        if contains not in text:
            marker_failures.append(f"{skill}: missing marker {contains}")
    status["missing"] = missing
    status["markers"] = marker_failures
    status["status"] = "pass" if not missing and not marker_failures else "missing"
    return status


def validate_manifest(root: Path, manifest: dict[str, Any], errors: list[str], warnings: list[str], check_skill_deps: bool) -> list[dict[str, Any]]:
    if not manifest:
        return []
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
    skill_paths: dict[str, Path] = {}
    if not isinstance(skills, list) or not skills:
        errors.append("manifest.skills must be a non-empty list")
        declared: set[str] = set()
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
            skill_paths[name] = skill_dir
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
            validate_skill_file_references(name, skill_dir, text, errors, warnings)
        declared = names

    discovered = {name for name, _ in discover_skills(root)}
    missing_from_manifest = sorted(name for name in discovered if name not in declared)
    if missing_from_manifest:
        warnings.append(f"discovered skills not declared in manifest: {', '.join(missing_from_manifest)}")
    npx = manifest.get("npx") if isinstance(manifest, dict) else None
    npx_supported = isinstance(npx, dict) and npx.get("supported") is not False
    if npx_supported and not ((root / "skills").is_dir() or (root / ".agents" / "skills").is_dir() or (root / "SKILL.md").exists()):
        errors.append("npx.supported is true but no npx-discoverable skill path exists")

    installers = manifest.get("installers", [])
    if installers is None:
        installers = []
    if not isinstance(installers, list):
        errors.append("manifest.installers must be a list when present")
        installers = []
    if not installers and not npx_supported:
        errors.append("manifest.installers must be non-empty when npx.supported is false")
    validate_installer_skill(manifest, declared, skill_paths, errors, warnings)
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
                errors.append(f"installer {path_value} does not report required executable: {entry['name']}")
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
    return validate_skill_dependencies(root, manifest, errors, warnings, check_skill_deps)


def validate_installer_skill(
    manifest: dict[str, Any],
    declared_skills: set[str],
    skill_paths: dict[str, Path],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    installer_skill = manifest.get("installer_skill") if isinstance(manifest, dict) else None
    if installer_skill in (None, {}):
        return {}
    if not isinstance(installer_skill, dict):
        errors.append("manifest.installer_skill must be an object when present")
        return {}
    name = installer_skill.get("name")
    if not isinstance(name, str) or not name:
        errors.append("manifest.installer_skill.name is required")
        return {}
    if name not in declared_skills:
        errors.append(f"manifest.installer_skill.name is not a declared skill: {name}")
    installs = installer_skill.get("installs", [])
    if not isinstance(installs, list) or not all(isinstance(item, str) for item in installs):
        errors.append("manifest.installer_skill.installs must be a string list when present")
        installs = []
    requires_approval = installer_skill.get("requires_approval")
    if requires_approval is not None and not isinstance(requires_approval, bool):
        errors.append("manifest.installer_skill.requires_approval must be boolean when present")
    risky = {"agents", "agents-md", "hooks", "templates", "tools"}
    if risky.intersection(installs) and requires_approval is not True:
        warnings.append(f"installer skill {name} installs repo files; set requires_approval true")
    skill_dir = skill_paths.get(name)
    if installs and skill_dir is not None:
        support_files = [path for path in skill_dir.rglob("*") if path.is_file() and path.name != "SKILL.md"]
        if not support_files:
            errors.append(
                f"installer skill {name} declares installs but has no bundled support files; "
                "npx skills installs only the skill folder"
            )
    return {"name": name, "installs": installs, "requires_approval": requires_approval}


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


def build_result(root: Path, run_checks: bool, check_skill_deps: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        errors.append(f"repo root does not exist: {root}")
        return {"status": "fail", "errors": errors, "warnings": warnings}
    manifest = load_manifest(root, errors)
    skill_dependency_status = validate_manifest(root, manifest, errors, warnings, check_skill_deps)
    prereq_results = run_prereqs(manifest, errors, warnings) if run_checks and manifest else {}
    return {
        "status": "fail" if errors else "pass",
        "repo_root": str(root),
        "manifest": manifest,
        "skills": [name for name, _ in discover_skills(root)],
        "errors": errors,
        "warnings": warnings,
        "prereqs": prereq_results,
        "skill_dependencies": skill_dependency_status,
        "installer_skill": manifest.get("installer_skill", {}) if isinstance(manifest, dict) else {},
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
    if result.get("skill_dependencies"):
        print("skill_dependencies:")
        for dependency in result["skill_dependencies"]:
            print(f"  - {dependency['name']}: {dependency['status']}")
    if result.get("installer_skill"):
        print("installer_skill:")
        print(f"  name: {result['installer_skill'].get('name', '')}")
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
    installers = manifest.get("installers", []) if isinstance(manifest, dict) else []
    for installer in installers:
        print(f"  - path: {installer.get('path', '')}")
        print(f"    checks_prerequisites: {str(installer.get('checks_prerequisites') is True).lower()}")
    if not installers:
        print("  []")
    npx = manifest.get("npx", {}) if isinstance(manifest, dict) else {}
    print("npx:")
    print(f"  command: {npx.get('install', '')}")
    print("installer_skill:")
    installer_skill = manifest.get("installer_skill", {}) if isinstance(manifest, dict) else {}
    if installer_skill:
        print(f"  name: {installer_skill.get('name', '')}")
        installs = ", ".join(installer_skill.get("installs", []))
        print(f"  installs: {installs}")
    else:
        print("  []")
    print("skill_dependencies:")
    skill_dependencies = result.get("skill_dependencies", [])
    for dependency in skill_dependencies:
        print(f"  - name: {dependency['name']}")
        print(f"    status: {dependency['status']}")
    if not skill_dependencies:
        print("  []")
    print("lint:")
    print(f"  status: {result['status']}")
    print(f"  error_count: {len(result['errors'])}")
    print(f"  warning_count: {len(result['warnings'])}")
    print("<<<END_SKILL_PACKAGE_PLAN>>>")


def main() -> int:
    args = parse_args()
    root = Path(args.repo).expanduser().resolve()
    result = build_result(root, args.run_prereqs, args.check_skill_deps)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.plan:
        emit_plan(result)
    else:
        emit_text(result)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
