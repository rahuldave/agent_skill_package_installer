# Agent Skill Package Installer

Standalone repository for the `skill-package-installer` agent skill. The skill
validates installable skill repositories, checks their package manifests,
confirms installer scripts declare prerequisite executable checks, and emits a
package plan before publication.

The only assumed runtime for the bundled linter is `uv`; `uv run python ...`
pulls or selects Python from this repository's `.python-version` and uses only
the Python standard library.

Install with `npx skills` after publication:

```bash
npx skills add rahuldave/agent_skill_package_installer -a codex --skill skill-package-installer
```

Local verification:

```bash
just verify
```

