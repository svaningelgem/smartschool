"""Tests for the self-maintaining stub generator (``dev/generate_stubs.py``)."""

from __future__ import annotations

import importlib
from pathlib import Path

import smartschool
from dev import generate_stubs


def test_pyi_set_matches_warranting_modules():
    """
    The committed ``.pyi`` set must equal exactly the modules that warrant one.

    Guards both acceptance criteria at once: a new warranting module with no
    stub, or an orphaned stub for a module that no longer qualifies, fails here.
    """
    package_dir = Path(smartschool.__file__).parent

    warranting = set()
    for python_file in package_dir.glob("*.py"):
        if python_file.stem == "__init__":
            continue
        module = importlib.import_module(f"smartschool.{python_file.stem}")
        if generate_stubs._warrants_stub(module):
            warranting.add(python_file.stem)

    on_disk = {pyi.stem for pyi in package_dir.glob("*.pyi")}
    assert warranting == on_disk


def test_sync_stubs_prunes_orphans_and_leaves_py_typed(tmp_path):
    """An orphaned stub is deleted; ``py.typed`` (a PEP 561 marker) is not."""
    (tmp_path / "plain.py").write_text("VALUE = 1\n")  # warrants no stub
    orphan = tmp_path / "stale.pyi"
    orphan.write_text("class Gone: ...\n")
    marker = tmp_path / "py.typed"
    marker.write_text("")

    generate_stubs.sync_stubs(tmp_path)

    assert not orphan.exists()
    assert marker.exists()
