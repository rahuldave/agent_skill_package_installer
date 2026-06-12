---
name: skill-package-maker
description: Validate and package installable agent skill repositories. Use when Codex is creating, updating, publishing, or reviewing a skill repo with skills/*/SKILL.md or .agents/skills/*/SKILL.md, a skill-package.json manifest, installer scripts, optional extras, npx skills installation, or executable prerequisite checks.
---

# Skill Package Maker

Use this authoring skill to make a skill repository installable and auditable
before it is committed, pushed, or installed with `npx skills`. This skill is
for package maintainers, and it is reasonable to install it globally in Codex.
End users of a finished package install that package directly and then invoke
the package's own installer skill for hooks, templates, docs, tools, or other
non-skill extras.

For a package author, the friendly path is:

1. Add or update `skill-package.json`.
2. Run the linter and package plan from this skill.
3. Fix manifest, installer-skill, dependency, or prerequisite messages.
4. Run the scratch install test before publishing.

## Workflow

1. Inspect the target repo for `skill-package.json`, `skills/*/SKILL.md`,
   `.agents/skills/*/SKILL.md`, installer skills, docs, references, assets, and
   Just targets.
2. Require `uv` for the linter runtime. The linter is Python-only and uses the
   standard library, so `uv run python ...` can supply Python without an
   additional language install.
3. Run the bundled linter from the installed skill or source checkout:

   ```bash
   uv run python .agents/skills/skill-package-maker/scripts/lint_skill_bundle.py .
   ```

   If working from this repo, use:

   ```bash
   uv run python skills/skill-package-maker/scripts/lint_skill_bundle.py .
   ```

4. Fix blocking errors before publication. Warnings should be resolved or
   recorded in Gest/review notes.
5. Emit a package plan when handing off or preparing a PR:

   ```bash
   uv run python .agents/skills/skill-package-maker/scripts/render_package_plan.py .
   ```

## Manifest Contract

Every packageable skill repo should have `skill-package.json` at its root. Read
`references/skill_package_manifest.md` before creating or changing the manifest.

The linter checks that the manifest declares:

- repository owner/name/url;
- discoverable skills and their folders;
- the package-specific installer skill users invoke after `npx skills add` to
  install hooks, templates, docs, or tools;
- installer scripts when a repository installs non-skill extras;
- required and optional executables with command checks;
- required skill dependencies and alternatives, when the package delegates to
  other skills;
- an `npx skills add ...` install command when the repo is GitHub-installable.
- skill-local runtime references: `SKILL.md` should point to bundled
  `references/`, `scripts/`, or `assets/` files, not repo-root `docs/`,
  `templates/`, or `tools/` paths. Copy the full reference closure into each
  skill that needs it.

For ordinary `skills/<name>/SKILL.md` or `.agents/skills/<name>/SKILL.md`
packages, `npx skills` is the skill installer. Do not add an implicit hook
postinstall. Instead, include one explicit installer skill in the skill set,
such as `blah_installer` for a `blah` package; after `npx skills add` installs
the skills, the user can ask that installer skill to install hooks, docs,
templates, tools, or other extras.
Because `npx skills` installs only selected skill folders, any post-npx
installer skill must carry its own scripts/assets or intentionally fetch the
package repository before running repo-level installers.
Installer scripts, when present for source-checkout or non-npx setup, should
report every required workflow executable and mention optional executables. For
example, Gest git skills declare `git`, `gest`, `just`, and `uv` as required,
with `cx` optional for incremental build/pipeline support.
Use `--check-skill-deps` when you need to verify that declared skill
dependencies are actually installed or available in a source checkout.

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

## Skill Dependencies

Read `references/skill_package_manifest.md` before adding dependencies. Use
`skill_dependencies` for package-level dependencies on other skills. Prefer
`any_of` when a package can work with one of several base skill families. This
skill itself is standalone and does not require the Gest git/GitButler or jj
skill family; use those only as optional development workflow helpers.

For a small end-to-end example with both skill dependencies and executable
prerequisites, read `references/hello_world_rust_tutorial.md`.

## Install Testing

Run `scripts/install_test_skill_bundle.py` or `just install-test` when a repo
has an installer. The install test creates a scratch target, runs the installer,
then verifies the installed skills are present. It does not mutate user project
files.
