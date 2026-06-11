# Agent Skill Package Installer

Standalone repository for the `skill-package-installer` agent skill. The skill
validates installable skill repositories, checks their package manifests,
confirms installer scripts declare prerequisite executable checks, checks
declared skill dependencies when asked, and emits a package plan before
publication.

The only assumed runtime for the bundled linter is `uv`; `uv run python ...`
pulls or selects Python from this repository's `.python-version` and uses only
the Python standard library.

The copy-based installer does not fail just because workflow prerequisites are
missing. It installs the skill and prints missing-tool guidance; commands that
actually need `uv`, `npx`, Gest, or another tool should re-check at use time.

Install with `npx skills`:

```bash
npx skills add rahuldave/agent_skill_package_installer -a codex --skill skill-package-installer
```

Local verification:

```bash
just verify
```

`npx skills` performs the skill copy. This repository does not need a custom
copy installer because it does not install hooks, project templates, or other
non-skill extras. The manifest still declares executables so the linter can
report missing tools before someone tries a workflow that needs them.

To verify required skill dependencies against local source or installed skill
roots, pass a path-list to `dependency-check`:

```bash
just dependency-check . "/Users/rahul/Projects/agent_gest_git_skills/.agents/skills:/Users/rahul/Projects/agent_gest_jj_skills/.agents/skills"
```

For a concrete dependency example, see
`skills/skill-package-installer/references/hello_world_rust_tutorial.md`. It
walks through a tiny `hello-rust` skill that depends on a Gest base skill family
and a local Rust toolchain.
