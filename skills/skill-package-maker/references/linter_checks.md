# Linter Checks

`lint_skill_bundle.py` uses only the Python standard library. Run it through
`uv` so the user only needs `uv` installed:

```bash
uv run python skills/skill-package-maker/scripts/lint_skill_bundle.py .
```

Checks performed:

- repository root exists;
- `skill-package.json` is parseable JSON;
- manifest has version, repository, skills, executables, and npx install fields
  where appropriate;
- every declared skill path exists and contains `SKILL.md`;
- `SKILL.md` has YAML-parseable frontmatter with matching `name` and a
  non-placeholder `description`;
- unquoted frontmatter scalar values do not contain `: `, which would make
  `npx skills` skip the skill;
- duplicate skill names are rejected;
- hidden second-tier skill hierarchies under a skill folder are rejected;
- markdown links to local references/scripts/assets from `SKILL.md` resolve;
- copy installer scripts, when declared, exist and are executable or shell
  scripts;
- copy installer scripts, when declared, report required executable
  prerequisites and mention optional executable checks;
- installer scripts do not use known external executables without declaring
  them in the manifest;
- optional `--run-prereqs` verifies required commands on the current machine.
- `skill_dependencies` declarations are structurally valid;
- optional `--check-skill-deps` verifies required dependency alternatives are
  installed or available under skill roots.

Dependency check roots come from:

- the repository's own `skills/` and `.agents/skills/` directories;
- `SKILL_PACKAGE_DEPENDENCY_PATHS`, using the platform path separator;
- `$CODEX_HOME/skills`, `$HOME/.codex/skills`, and `$HOME/.agents/skills`.
