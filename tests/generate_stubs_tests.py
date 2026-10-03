"""Tests for the public stub generator (``dev/generate_stubs.py``)."""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import smartschool
from dev import generate_stubs  # pylint: disable=import-error  # dev/ is a namespace package on pytest's pythonpath

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def _isolated_imports(mocker: MockerFixture) -> Iterator[None]:
    """sync_stubs imports the package it stubs; keep it and its sys.path entry out of the next test."""
    mocker.patch.object(sys, "path", list(sys.path))
    yield
    for name in [name for name in sys.modules if name.partition(".")[0] == "stubbed"]:
        del sys.modules[name]


def _stub_of(tmp_path: Path, source: str) -> ast.Module:
    """Run the generator over a one-module package and parse the stub it writes."""
    package = tmp_path / "stubbed"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "mod.py").write_text(textwrap.dedent(source))
    generate_stubs.sync_stubs(package, tmp_path / "stubs")
    return ast.parse((tmp_path / "stubs/mod.pyi").read_text())


def _class_bodies(stub: ast.Module) -> dict[str, list[str]]:
    return {node.name: [ast.unparse(member) for member in node.body] for node in stub.body if isinstance(node, ast.ClassDef)}


def test_every_module_ships_a_stub():
    """A new module gets a stub, and a removed module loses its stub."""
    sources = {path.stem for path in Path(smartschool.__file__).parent.glob("*.py")}
    stubs = {path.stem for path in (Path(__file__).parent.parent / "stubs/smartschool").glob("*.pyi")}
    assert sources == stubs


def test_stub_hides_private_members(tmp_path: Path):
    stub = _stub_of(
        tmp_path,
        """
        from abc import ABC, abstractmethod
        from dataclasses import dataclass, field

        class Query(ABC):
            @property
            @abstractmethod
            def _url(self) -> str: ...

            def fetch(self) -> bytes:
                return b""

        class Lessons(Query):
            _url = "/lessons"

            def _parse(self) -> None: ...

        @dataclass
        class Folder:
            items: list[int] = field(default_factory=list)
            cache: dict = field(init=False, default_factory=dict)
        """,
    )

    assert _class_bodies(stub) == {
        "Query": ["def fetch(self) -> bytes:\n    ..."],
        "Lessons": ["..."],
        "Folder": ["items: list[int] = ...", "cache: dict = field(init=False)"],
    }


def test_stub_keeps_pydantic_models_constructible(tmp_path: Path):
    stub = _stub_of(
        tmp_path,
        """
        from typing import Annotated

        from pydantic import StringConstraints
        from pydantic.dataclasses import dataclass

        Name = Annotated[str, StringConstraints(strip_whitespace=True)]

        @dataclass
        class Teacher:
            name: Name
            nickname: Annotated[Name, "shown as is"] = ""
        """,
    )

    assert "Name = str" in [ast.unparse(node) for node in stub.body]
    teacher = next(node for node in stub.body if isinstance(node, ast.ClassDef))
    assert [ast.unparse(decorator) for decorator in teacher.decorator_list] == ["dataclass"]
    assert [ast.unparse(member) for member in teacher.body] == ["name: Name", "nickname: Name = ''"]


def test_stub_keeps_a_typing_only_import_that_a_string_bound_refers_to(tmp_path: Path):
    stub = _stub_of(
        tmp_path,
        """
        from typing import TYPE_CHECKING, Generic, TypeVar

        if TYPE_CHECKING:
            from decimal import Decimal

        _AmountT = TypeVar("_AmountT", bound="Decimal")

        class Ledger(Generic[_AmountT]):
            def total(self) -> _AmountT: ...
        """,
    )

    assert "from decimal import Decimal" in [ast.unparse(node) for node in stub.body]


def test_stub_refuses_to_hide_a_private_init_argument(tmp_path: Path):
    """Hiding it would shift the positional arguments of the generated __init__."""
    with pytest.raises(ValueError, match=r"Account takes private __init__ arguments \['_token'\]"):
        _stub_of(
            tmp_path,
            """
            from dataclasses import dataclass

            @dataclass
            class Account:
                _token: str
                name: str
            """,
        )


def test_sync_stubs_prunes_orphans(tmp_path: Path):
    orphan = tmp_path / "stubs/gone.pyi"
    orphan.parent.mkdir()
    orphan.write_text("class Gone: ...\n")

    _stub_of(tmp_path, "VALUE = 1\n")

    assert not orphan.exists()
