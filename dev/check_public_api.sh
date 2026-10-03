#!/bin/bash
# Type-check tests/public_api against the wheel as users install it: usage.py must pass ty, pyright
# and mypy, and private_access.py must fail on the private member it touches.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

uv build --quiet --wheel --out-dir "$work/dist" "$repo"
uv venv --quiet --python "${PYTHON:-3.10}" "$work/user"
uv pip install --quiet --python "$work/user" "$work"/dist/*.whl
cp "$repo"/tests/public_api/*.py "$work"
cd "$work"

checkers=(
    "uvx ty check --python user --output-format concise"
    "uvx pyright --pythonpath user/bin/python"
    "uvx mypy --python-executable user/bin/python"
)
for checker in "${checkers[@]}"; do
    $checker usage.py
    if $checker private_access.py >private.log 2>&1 || ! grep -q -E 'attribute .?_xpath' private.log; then
        cat private.log
        echo "::error::$checker does not reject the private member in private_access.py"
        exit 1
    fi
done
