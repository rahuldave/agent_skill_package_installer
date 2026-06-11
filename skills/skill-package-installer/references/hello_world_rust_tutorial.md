# Tutorial: Hello Rust Skill Package

This tutorial builds a deliberately tiny skill package that depends on:

- a Gest base skill family, either `rahuldave/agent_gest_git_skills` or
  `rahuldave/agent_gest_jj_skills`;
- a local Rust toolchain, represented by `cargo` and `rustc`;
- `uv`, so package linting can run with a managed Python runtime.

The skill is intentionally silly: it only prints a Rust hello-world program and
checks that Cargo is available. It is useful because the dependency behavior is
easy to see.

It does not need hooks. A hook-installing package should use the same install
flow, but include a second normal skill such as `hello_rust_installer` that the
user invokes after `npx skills add`.

## Install-Time Behavior

`npx skills add owner/repo -a codex --skill hello-rust` installs the skill
bundle. It should not be treated as a dependency gate because it installs skill
files; it does not install or validate the user's Rust toolchain for you.

For best user experience:

- declare workflow prerequisites in `skill-package.json`;
- run package lint before publishing so missing tools are visible to the
  packager;
- make runtime helper scripts re-check the tools they actually need and print
  clear install guidance.

## Repository Shape

Create this layout:

```text
hello-rust-skill/
  skill-package.json
  skills/
    hello-rust/
      SKILL.md
      scripts/
        hello_rust.py
```

## Skill File

Create `skills/hello-rust/SKILL.md`:

````markdown
---
name: hello-rust
description: Demonstrate a tiny installable skill package that requires a Gest base skill family and a local Rust toolchain with cargo and rustc.
compatibility: Requires cargo and rustc for the helper script; package lint uses uv.
---

# Hello Rust

Use this skill only as a packaging example. Before running its helper script,
confirm that declared package dependencies are satisfied:

```bash
uv run python .agents/skills/hello-rust/scripts/hello_rust.py
```
````

## Runtime Script

Create `skills/hello-rust/scripts/hello_rust.py`:

```python
#!/usr/bin/env python3
"""Show a Rust hello-world example after checking the local toolchain."""

from __future__ import annotations

import shutil
import subprocess
import sys


def require(name: str) -> None:
    if shutil.which(name) is None:
        print(f"missing required executable: {name}", file=sys.stderr)
        print("Install Rust from https://rustup.rs/ or use your system package manager.", file=sys.stderr)
        raise SystemExit(1)


def main() -> int:
    require("cargo")
    require("rustc")
    cargo_version = subprocess.check_output(["cargo", "--version"], text=True).strip()
    rustc_version = subprocess.check_output(["rustc", "--version"], text=True).strip()
    print(cargo_version)
    print(rustc_version)
    print('fn main() { println!("hello from a packaged skill"); }')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Package Manifest

Create `skill-package.json`:

```json
{
  "schema": "https://rahuldave.github.io/agent_skill_package_installer/schema/skill-package.v1.json",
  "version": 1,
  "repository": {
    "owner": "rahuldave",
    "name": "hello-rust-skill",
    "url": "https://github.com/rahuldave/hello-rust-skill"
  },
  "skills": [
    {
      "name": "hello-rust",
      "path": "skills/hello-rust"
    }
  ],
  "executables": {
    "required": [
      {"name": "uv", "check": "uv --version"},
      {"name": "npx", "check": "npx --version"},
      {"name": "cargo", "check": "cargo --version"},
      {"name": "rustc", "check": "rustc --version"}
    ],
    "optional": [
      {"name": "rsync", "check": "rsync --version"},
      {"name": "rustup", "check": "rustup --version"}
    ]
  },
  "skill_dependencies": [
    {
      "name": "gest-base-workflow",
      "required": true,
      "description": "The example delegates tracked repository work to whichever Gest base workflow is installed.",
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
    "install": "npx skills add rahuldave/hello-rust-skill -a codex --skill hello-rust"
  }
}
```

## Validate The Package

From the example repo root, run static package lint:

```bash
uv run python /path/to/agent_skill_package_installer/skills/skill-package-installer/scripts/lint_skill_bundle.py .
```

Check local executable prerequisites:

```bash
uv run python /path/to/agent_skill_package_installer/skills/skill-package-installer/scripts/lint_skill_bundle.py --run-prereqs .
```

Check Gest base skill dependencies using source checkouts or installed skill
roots:

```bash
SKILL_PACKAGE_DEPENDENCY_PATHS="/Users/rahul/Projects/agent_gest_git_skills/.agents/skills:/Users/rahul/Projects/agent_gest_jj_skills/.agents/skills" \
  uv run python /path/to/agent_skill_package_installer/skills/skill-package-installer/scripts/lint_skill_bundle.py --check-skill-deps .
```

Install with `npx skills`:

```bash
npx skills add rahuldave/hello-rust-skill -a codex --skill hello-rust
```

If `cargo` or `rustc` is missing, `npx skills add` may still install the skill.
That is fine. The lint step reports missing prerequisites for packagers, and the
runtime helper script prints missing-tool guidance when invoked.

## Optional Hook Installer Skill

If the package also needs hooks, add a second skill instead of relying on a
hidden install side effect:

```text
hello-rust-skill/
  skills/
    hello-rust/
      SKILL.md
      scripts/
        hello_rust.py
    hello_rust_installer/
      SKILL.md
      assets/
        hooks/
      scripts/
        install_hooks.py
```

The installer skill is installed by the same `npx skills add` command as the
main skill. Later, the user asks the agent to use `hello_rust_installer`; that
installer skill can then copy hook files from its own `assets/` directory, ask
before overwriting project files, and re-check any executables it needs.

Manifest fragment:

```json
{
  "skills": [
    {"name": "hello-rust", "path": "skills/hello-rust"},
    {"name": "hello_rust_installer", "path": "skills/hello_rust_installer"}
  ],
  "installer_skill": {
    "name": "hello_rust_installer",
    "description": "Optional post-install setup for hooks.",
    "installs": ["hooks"],
    "requires_approval": true
  }
}
```
