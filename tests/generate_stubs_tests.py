"""Tests for the self-maintaining stub generator (``dev/generate_stubs.py``)."""

from __future__ import annotations

import ast
import importlib
import textwrap
from pathlib import Path

import smartschool
from dev import generate_stubs  # pylint: disable=import-error  # dev/ is a namespace package on pytest's pythonpath


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
        if generate_stubs._warrants_stub(module):  # pylint: disable=protected-access  # white-box test
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


def test_stub_keeps_the_private_overrides_of_abstract_members(tmp_path):
    """Without them a type checker reads the stubbed class as abstract and refuses to instantiate it."""
    source = tmp_path / "queries.py"
    source.write_text(
        textwrap.dedent(
            """
            from abc import ABC, abstractmethod

            class Base(ABC):
                @property
                @abstractmethod
                def _url(self) -> str: ...

                @abstractmethod
                def _fetch(self) -> bytes: ...

            class _Endpoint:
                _url = "/endpoint"

            class Query(_Endpoint, Base):
                def _fetch(self) -> bytes:
                    return b""

                def _helper(self) -> None: ...
            """
        )
    )

    stub = ast.parse(generate_stubs.generate_stub_file(source))

    bodies = {node.name: [ast.unparse(member) for member in node.body] for node in stub.body if isinstance(node, ast.ClassDef)}
    assert bodies["_Endpoint"] == ["_url: str"]
    assert bodies["Query"] == ["def _fetch(self) -> bytes:\n    ..."]
