# Skill Package Manifest

`skill-package.json` is the package-installer source of truth. Keep it small,
checked into the repository root, and update it whenever skills, installer
scripts, or executable prerequisites change.

Minimal shape:

```json
{
  "schema": "https://rahuldave.github.io/agent_skill_package_installer/schema/skill-package.v1.json",
  "version": 1,
  "repository": {
    "owner": "rahuldave",
    "name": "example_skill_repo",
    "url": "https://github.com/rahuldave/example_skill_repo"
  },
  "skills": [
    {"name": "example-skill", "path": "skills/example-skill"}
  ],
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
          "install": "scripts/install.sh from https://github.com/rahuldave/agent_gest_git_skills"
        },
        {
          "name": "agent-gest-jj-skills",
          "repository": "rahuldave/agent_gest_jj_skills",
          "skills": ["gtw", "gsu", "gcm", "gpa"],
          "markers": [{"skill": "gsu", "contains": "jj/Gest"}],
          "install": "scripts/install.sh from https://github.com/rahuldave/agent_gest_jj_skills"
        }
      ]
    }
  ],
  "npx": {
    "supported": true,
    "install": "npx skills add rahuldave/example_skill_repo -a codex --skill example-skill"
  }
}
```

Rules:

- `version` must be `1`.
- `repository.owner`, `repository.name`, and `repository.url` are required.
- Every `skills[].path` must contain a `SKILL.md`.
- `skills[].name` must match the `name` in that `SKILL.md` frontmatter.
- `npx skills` is the normal installer for pure skill packages, so
  `installers[]` is optional when `"npx": {"supported": true}`.
- At least one `installers[]` entry is required only for repos that set
  `npx.supported` to `false` or that intentionally copy hooks, docs, templates,
  extras, tools, or project-local skill bundles outside the `npx skills` path.
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
