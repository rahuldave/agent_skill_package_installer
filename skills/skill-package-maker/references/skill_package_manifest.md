# Skill Package Manifest

`skill-package.json` is the package-authoring source of truth. Keep it small,
checked into the repository root, and update it whenever skills, installer
skills, installer scripts, or executable prerequisites change.

Minimal shape:

```json
{
  "schema": "https://rahuldave.github.io/agent_skill_package_maker/schema/skill-package.v1.json",
  "version": 1,
  "repository": {
    "owner": "rahuldave",
    "name": "example_skill_repo",
    "url": "https://github.com/rahuldave/example_skill_repo"
  },
  "skills": [
    {"name": "example-skill", "path": "skills/example-skill"},
    {"name": "example_installer", "path": "skills/example_installer"}
  ],
  "installer_skill": {
    "name": "example_installer",
    "description": "Optional post-install installer skill for hooks, templates, or tools.",
    "installs": ["hooks", "templates"],
    "requires_approval": true
  },
  "executables": {
    "required": [
      {"name": "uv", "check": "uv --version"}
    ],
    "optional": [
      {"name": "cx", "check": "cx --help"}
    ]
  },
  "skill_dependencies": [
    {
      "name": "gest-base-workflow",
      "required": true,
      "any_of": [
        {
          "name": "agent-gest-git-skills",
          "repository": "rahuldave/agent_gest_git_skills",
          "skills": ["gtw", "gsu", "gcm", "gpa"],
          "markers": [{"skill": "gsu", "contains": "Git/GitButler"}],
          "install": "npx skills add rahuldave/agent_gest_git_skills -a codex --skill '*' -y, then invoke gest_git_installer for hooks/extras"
        },
        {
          "name": "agent-gest-jj-skills",
          "repository": "rahuldave/agent_gest_jj_skills",
          "skills": ["gtw", "gsu", "gcm", "gpa"],
          "markers": [{"skill": "gsu", "contains": "jj/Gest"}],
          "install": "npx skills add rahuldave/agent_gest_jj_skills -a codex --skill '*' -y, then invoke gest_jj_installer for hooks/extras"
        }
      ]
    }
  ],
  "npx": {
    "supported": true,
    "install": "npx skills add rahuldave/example_skill_repo -a codex --skill example-skill --skill example_installer"
  }
}
```

Rules:

- `version` must be `1`.
- `repository.owner`, `repository.name`, and `repository.url` are required.
- Every `skills[].path` must contain a `SKILL.md`.
- `skills[].name` must match the `name` in that `SKILL.md` frontmatter.
- `SKILL.md` frontmatter must parse as YAML as used by `npx skills`; quote or
  rewrite values containing `: `.
- `npx skills` is the normal installer for skill packages, so
  `installers[]` is optional when `"npx": {"supported": true}`.
- Hooks, docs, templates, tools, and other non-skill extras should be installed
  through the package's explicit installer skill after `npx skills add`, not as
  a hidden side effect of installing the skill set.
- Runtime support material required by a skill should live inside that skill.
  Copy the full reference closure each skill needs under its own
  `references/`, copy executable helpers under its own `scripts/`, and keep
  generated output resources under `assets/`. In `SKILL.md`, refer to those
  files as `references/foo.md`, `scripts/foo.sh`, or `assets/foo.ext`; do not
  point installed skills at repo-root `docs/`, `templates/`, or `tools/`.
- When a copied reference file links to another copied reference file, keep the
  files together and use sibling links such as `other_reference.md`. If a
  reference file needs to point at a bundled script, use a real relative path
  such as `../scripts/helper.sh`.
- Use `installer_skill` to name the one installed skill that performs that
  post-install setup. Prefer names like `blah_installer` for the `blah` package.
  If the installer skill installs hooks, AGENTS guidance, templates, or tools,
  set `requires_approval: true`.
- At least one `installers[]` entry is required only for repos that set
  `npx.supported` to `false` or that intentionally support source-checkout
  installation outside the `npx skills` path.
- Installers must set `checks_prerequisites: true` and report all required
  workflow executables. Missing workflow tools should produce clear guidance,
  not prevent the skill bundle itself from being installed.
- Executable entries use `name` plus a human-runnable `check` command.
- Optional executables should still be mentioned by a custom installer so users
  see what extra workflows will be unavailable.
- Include non-language installer tools such as `rsync` when installer scripts
  use them.
- Repos installed only by their own copy-based installer may set
  `"npx": {"supported": false, "reason": "copy-based installer"}`.

Installer skill:

- An installer skill is a normal skill installed by `npx skills add`.
- The user or agent invokes it after installation to copy hooks, templates,
  tools, AGENTS snippets, or other repo extras.
- The installer skill should keep scripts and templates under its own skill
  resources, such as `scripts/` and `assets/`, or clearly fetch the package
  repository before invoking repo-level installers. `npx skills` does not copy
  arbitrary root-level repository scripts into the installed skill folder.
- The installer skill should ask before overwriting user files and should
  re-check any executables it needs at use time.

Skill dependencies:

- Use `skill_dependencies` when a package requires other skills to be installed
  or available for its workflow.
- Each dependency has `name`, optional `description`, and `required`.
- Use `any_of` for alternatives. Each alternative can declare `name`,
  `repository`, `skills`, `markers`, and `install`.
- `skills` lists skill names that must be available under a skill root such as
  `.agents/skills`, `skills`, `$CODEX_HOME/skills`, or a path supplied through
  `SKILL_PACKAGE_DEPENDENCY_PATHS`.
- `markers` optionally prove the right base family by checking that a skill's
  `SKILL.md` contains expected text, such as `Git/GitButler` or `jj/Gest`.
- Static lint validates the declaration. Run with `--check-skill-deps` to verify
  installed/source dependencies on the current machine.
