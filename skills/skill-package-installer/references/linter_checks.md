# Linter Checks

`lint_skill_bundle.py` uses only the Python standard library. Run it through
`uv` so the user only needs `uv` installed:

```bash
uv run python skills/skill-package-installer/scripts/lint_skill_bundle.py .
```

Checks performed:

- repository root exists;
- `skill-package.json` is parseable JSON;
- manifest has version, repository, skills, installers, executables, and npx
  install fields where appropriate;
- every declared skill path exists and contains `SKILL.md`;
- `SKILL.md` has frontmatter with matching `name` and a non-placeholder
  `description`;
- duplicate skill names are rejected;
- hidden second-tier skill hierarchies under a skill folder are rejected;
- markdown links to local references/scripts/assets from `SKILL.md` resolve;
- installer scripts exist and are executable or shell scripts;
- installer scripts check required executable prerequisites and mention optional
  executable checks;
- installer scripts do not use known external executables without declaring
  them in the manifest;
- optional `--run-prereqs` verifies required commands on the current machine.
