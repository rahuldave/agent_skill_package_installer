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
    {"name": "example-skill", "path": "skills/example-skill", "installer": "scripts/install.sh"}
  ],
  "installers": [
    {"path": "scripts/install.sh", "checks_prerequisites": true}
  ],
  "executables": {
    "required": [
      {"name": "uv", "check": "uv --version"},
      {"name": "rsync", "check": "rsync --version"}
    ],
    "optional": [
      {"name": "cx", "check": "cx --help"}
    ]
  },
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
- At least one `installers[]` entry is required for reusable skill repos that
  copy hooks, docs, templates, extras, or project-local skills.
- Installers must set `checks_prerequisites: true` and check all required
  executables before copying files.
- Executable entries use `name` plus a human-runnable `check` command.
- Optional executables should still be mentioned by the installer so users see
  what extra workflows will be unavailable.
- Include non-language installer tools such as `rsync` when installer scripts
  use them.
- Repos installed only by their own copy-based installer may set
  `"npx": {"supported": false, "reason": "copy-based installer"}`.
