from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, TypeAlias, overload

from .common import create_filesystem_safe_filename, create_filesystem_safe_path, natural_sort
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

__all__ = ["Intradesk", "IntradeskFile", "IntradeskFolder", "IntradeskItem"]


@dataclass
class IntradeskFile(SessionMixin):
    """Represents a file in the intradesk."""

    parent: IntradeskFolder = field(repr=False)
    id: str = ""
    name: str = ""
    platform_id: str = field(repr=False, default="")

    @cached_property
    def filename(self) -> str:
        return create_filesystem_safe_filename(self.name)

    @overload
    def download(self, to_file: Path | str, *, overwrite: bool) -> Path: ...

    @overload
    def download(self) -> bytes: ...

    def download(self, to_file: Path | str | None = None, *, overwrite: bool = False) -> bytes | Path:
        target = None
        if to_file:
            target = create_filesystem_safe_path(to_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not overwrite and target.exists():
                return target

        response = self.session.get(f"/intradesk/api/v1/{self.platform_id}/files/{self.id}/download")
        response.raise_for_status()

        if target:
            target.write_bytes(response.content)
            return target

        return response.content

    def download_to_dir(self, target_directory: Path, *, overwrite: bool = False) -> Path:
        return self.download(target_directory / self.filename, overwrite=overwrite)


@dataclass
class IntradeskFolder(SessionMixin):
    """Represents a folder in the intradesk."""

    parent: IntradeskFolder | None = field(repr=False, default=None)
    id: str = ""
    name: str = ""
    platform_id: str = field(repr=False, default="")

    @cached_property
    def items(self) -> list[IntradeskItem]:
        data = self.session.json(f"/intradesk/api/v1/{self.platform_id}/directory-listing/forTreeOnlyFolders/{self.id}")

        result: list[IntradeskItem] = []

        for fo in data.get("folders", []):
            result.append(
                IntradeskFolder(
                    session=self.session,
                    parent=self,
                    id=str(fo["id"]),
                    name=fo["name"],
                    platform_id=str(fo["platform"]["id"]),
                )
            )

        for fi in data.get("files", []):
            result.append(
                IntradeskFile(
                    session=self.session,
                    parent=self,
                    id=str(fi["id"]),
                    name=fi["name"],
                    platform_id=str(fi["platform"]["id"]),
                )
            )

        return sorted(result, key=lambda x: (0 if isinstance(x, IntradeskFolder) else 1,) + natural_sort(x.name))

    def __iter__(self) -> Iterator[IntradeskItem]:
        yield from self.items


@dataclass
class Intradesk(IntradeskFolder):
    """
    Root folder of the intradesk.

    The platform ID is derived from the authenticated user's ID.

    Example:
    -------
    >>> intradesk = Intradesk(session)
    >>> for item in intradesk:
    ...     print(item.name)

    """

    def __post_init__(self):
        user_id = str(self.session.authenticated_user["id"])
        self.platform_id = user_id.split("_")[0]
        self.name = "intradesk"


IntradeskItem: TypeAlias = IntradeskFile | IntradeskFolder
