# Agent Skill Package Maker

Standalone repository for the `skill-package-maker` authoring skill. This
is for package maintainers, not for end users of a published skill package. The
skill validates installable skill repositories, checks their package manifests,
confirms package-specific installer skills and installer scripts are declared
correctly, checks declared skill dependencies when asked, and emits a package
plan before publication.

The only assumed runtime for the bundled linter is `uv`; `uv run python ...`
pulls or selects Python from this repository's `.python-version` and uses only
the Python standard library.

This skill has no required dependency on the Gest git/GitButler or jj skill
families. If those skills are installed, use them for tracked development,
commits, and PR review; the package linter itself remains standalone.

Package authors can install this builder skill globally for Codex with
`npx skills`:

```bash
npx skills add rahuldave/agent_skill_package_installer -g -a codex --skill skill-package-maker -y
```

Local verification:

```bash
just verify
```

End users of a finished package should not install this repository first. They
install the finished package directly, for example with
`npx skills add owner/package -a codex --skill '*' -y`, and then ask that
package's own installer skill to install hooks, templates, docs, tools, or other
non-skill extras.

`npx skills` performs the skill copy. This repository does not need a custom
copy installer because it does not install hooks, project templates, or other
non-skill extras. The manifest still declares executables so the linter can
report missing tools before a package author tries a workflow that needs them.

For packages that do install hooks or repo templates, publish an explicit
installer skill in the same skill set, such as `blah_installer` for a `blah`
package. Users first run `npx skills add ...`, then invoke that installer skill
to install hooks with clear approval and missing-tool guidance. Keep general
setup skills separate unless the whole skill exists only to install that
package's extras.

To verify required skill dependencies against local source or installed skill
roots, pass a path-list to `dependency-check`:

```bash
just dependency-check . "/Users/rahul/Projects/agent_gest_git_skills/.agents/skills:/Users/rahul/Projects/agent_gest_jj_skills/.agents/skills"
```

For concrete examples, see
`skills/skill-package-maker/references/hello_world_rust_tutorial.md`. It
walks through a tiny `hello-rust` skill that depends on a Gest base skill family
and a local Rust toolchain, plus an installer-skill pattern for hooks.
