export UV_CACHE_DIR := ".local/uv-cache"

package-plan repo=".":
  uv run python skills/skill-package-maker/scripts/render_package_plan.py {{repo}}

lint-skills repo=".":
  uv run python skills/skill-package-maker/scripts/lint_skill_bundle.py {{repo}}

lint-json repo=".":
  uv run python skills/skill-package-maker/scripts/lint_skill_bundle.py --json {{repo}}

dependency-check repo="." dep_roots="":
  SKILL_PACKAGE_DEPENDENCY_PATHS="{{dep_roots}}" uv run python skills/skill-package-maker/scripts/lint_skill_bundle.py --check-skill-deps {{repo}}

install-test repo=".":
  uv run python skills/skill-package-maker/scripts/install_test_skill_bundle.py {{repo}}

self-host-lab: lint-skills install-test

verify: lint-skills package-plan install-test
