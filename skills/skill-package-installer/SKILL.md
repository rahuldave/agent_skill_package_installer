---
name: skill-package-installer
description: Validate and package installable agent skill repositories. Use when Codex is creating, updating, publishing, or reviewing a skill repo with skills/*/SKILL.md or .agents/skills/*/SKILL.md, a skill-package.json manifest, installer scripts, optional extras, npx skills installation, or executable prerequisite checks.
---

# Skill Package Installer

Use this skill to make a skill repository installable and auditable before it
is committed, pushed, or installed with `npx skills`.

## Workflow

1. Inspect the target repo for `skill-package.json`, `skills/*/SKILL.md`,
   `.agents/skills/*/SKILL.md`, `scripts/install.sh`, docs, references,
   assets, and Just targets.
2. Require `uv` for the linter runtime. The linter is Python-only and uses the
   standard library, so `uv run python ...` can supply Python without an
   additional language install.
3. Run the bundled linter from the installed skill or source checkout:

   ```bash
   uv run python .agents/skills/skill-package-installer/scripts/lint_skill_bundle.py .
   ```

   If working from this repo, use:

   ```bash
   uv run python skills/skill-package-installer/scripts/lint_skill_bundle.py .
   ```

4. Fix blocking errors before publication. Warnings should be resolved or
   recorded in Gest/review notes.
5. Emit a package plan when handing off or preparing a PR:

   ```bash
   uv run python .agents/skills/skill-package-installer/scripts/render_package_plan.py .
   ```

## Manifest Contract

Every packageable skill repo should have `skill-package.json` at its root. Read
`references/skill_package_manifest.md` before creating or changing the manifest.

The linter checks that the manifest declares:

- repository owner/name/url;
- discoverable skills and their folders;
- at least one installer script;
- required and optional executables with command checks;
- an `npx skills add ...` install command when the repo is GitHub-installable.

Installer scripts must check every required executable and mention optional
executables. For example, Gest git skills declare `git`, `gest`, `just`, and
`uv` as required, with `cx` optional for incremental build/pipeline support.

## Linter Output

The linter prints a delimited block for agent re-entry:

```text
<<<SKILL_BUNDLE_LINT v1>>>
status: pass
errors: []
warnings: []
<<<END_SKILL_BUNDLE_LINT>>>
```

Use `--json` when another script needs structured output.

## Install Testing

Run `scripts/install_test_skill_bundle.py` or `just install-test` when a repo
has an installer. The install test creates a scratch target, runs the installer,
then verifies the installed skills are present. It does not mutate user project
files.
