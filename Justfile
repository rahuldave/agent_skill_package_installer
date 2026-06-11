export UV_CACHE_DIR := ".local/uv-cache"

package-plan repo=".":
  uv run python skills/skill-package-installer/scripts/render_package_plan.py {{repo}}

lint-skills repo=".":
  uv run python skills/skill-package-installer/scripts/lint_skill_bundle.py {{repo}}

lint-json repo=".":
  uv run python skills/skill-package-installer/scripts/lint_skill_bundle.py --json {{repo}}

install-test repo=".":
  uv run python skills/skill-package-installer/scripts/install_test_skill_bundle.py {{repo}}

self-host-lab: lint-skills install-test

verify: lint-skills package-plan install-test

