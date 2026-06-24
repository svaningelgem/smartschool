from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, TypeAlias, TypeVar

from ._common import DownloadableFile, create_filesystem_safe_filename, natural_sort
from ._exceptions import SmartSchoolAttachmentUploadError
from ._session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ._session import Smartschool

__all__ = ["MyDocs", "MyDocsFile", "MyDocsFolder", "MyDocsItem"]

_ItemT = TypeVar("_ItemT", bound="_MyDocsItem")


def _refresh(folder: MyDocsFolder | None) -> None:
    if folder is not None:
        folder.refresh()


class _MyDocsItem:
    """Operations shared by files and folders in My Documents (see MyDocsFile / MyDocsFolder)."""

    _endpoint: ClassVar[str]  # "files" or "folders"

    if TYPE_CHECKING:
        session: Smartschool
        id: str
        name: str
        is_favourite: bool
        parent: MyDocsFolder | None

    def _post(self, action: str, **kwargs) -> dict:
        response = self.session.post(f"/mydoc/api/v1/{self._endpoint}/{self.id}/{action}", **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def rename(self: _ItemT, new_name: str) -> _ItemT:
        """Rename this item (the server may adjust the name on a clash)."""
        data = self._post("rename", json={"newName": new_name})
        self.name = data.get("name", new_name)
        self.__dict__.pop("filename", None)
        _refresh(self.parent)
        return self

    def move(self: _ItemT, target: MyDocsFolder) -> _ItemT:
        """Move this item into ``target``."""
        old_parent = self.parent
        data = self._post("move", json={"parentId": target.id})
        self.parent = target
        self.name = data.get("name", self.name)
        self.__dict__.pop("filename", None)
        _refresh(old_parent)
        target.refresh()
        return self

    def copy(self, target: MyDocsFolder) -> MyDocsItem:
        """Copy this item into ``target`` and return the new copy."""
        data = self._post("copy", json={"parentId": target.id})
        target.refresh()
        return target._make_item(data)

    def trash(self) -> None:
        """Move this item to the recycle bin (reversible with :meth:`restore`)."""
        self._post("trash")
        _refresh(self.parent)

    def restore(self: _ItemT, into: MyDocsFolder | None = None) -> _ItemT:
        """Restore this item from the recycle bin, into ``into`` or its original folder."""
        target = into if into is not None else self.parent
        data = self._post("restore", json={"parentId": target.id if target is not None else ""})
        if into is not None:
            self.parent = into
        self.name = data.get("name", self.name)
        self.__dict__.pop("filename", None)
        _refresh(self.parent)
        return self

    def mark_favourite(self: _ItemT) -> _ItemT:
        """Add this item to your favourites."""
        data = self._post("mark-as-favourite")
        self.is_favourite = bool(data.get("isFavourite", True))
        return self

    def unmark_favourite(self: _ItemT) -> _ItemT:
        """Remove this item from your favourites."""
        data = self._post("unmark-as-favourite")
        self.is_favourite = bool(data.get("isFavourite", False))
        return self


@dataclass
class MyDocsFile(_MyDocsItem, DownloadableFile, SessionMixin):
    """A file in the personal "My Documents" (``/mydoc``) storage."""

    _endpoint: ClassVar[str] = "files"

    parent: MyDocsFolder = field(repr=False)
    id: str = ""
    name: str = ""
    revision_id: str = ""
    size: int = 0
    is_favourite: bool = False

    @cached_property
    def filename(self) -> str:
        return create_filesystem_safe_filename(self.name)

    def is_dir(self) -> bool:
        return False

    def is_file(self) -> bool:
        return True

    def _real_download(self, target: Path | None) -> bytes | Path:
        # The download endpoint 302-redirects to a (short-lived) presigned URL; requests follows it.
        response = self.session.get(f"/mydoc/api/v1/files/{self.id}/revisions/{self.revision_id}/download")
        response.raise_for_status()

        if target:
            target.write_bytes(response.content)
            return target

        return response.content

    def delete(self) -> None:
        """Permanently delete this file (use :meth:`trash` for a reversible delete)."""
        self.session.delete(f"/mydoc/api/v1/files/{self.id}").raise_for_status()
        self.parent.refresh()


@dataclass
class MyDocsFolder(_MyDocsItem, SessionMixin):
    """A folder in the personal "My Documents" storage."""

    _endpoint: ClassVar[str] = "folders"

    parent: MyDocsFolder | None = field(repr=False, default=None)
    id: str = ""
    name: str = ""
    color: str = ""
    is_favourite: bool = False

    def is_dir(self) -> bool:
        return True

    def is_file(self) -> bool:
        return False

    @property
    def _listing_url(self) -> str:
        # An empty id addresses the root folder.
        return "/mydoc/api/v1/directory-listing" + (f"/{self.id}" if self.id else "")

    @cached_property
    def items(self) -> list[MyDocsItem]:
        data = self.session.json(self._listing_url)

        result: list[MyDocsItem] = [self._make_folder(fo) for fo in data.get("folders", [])]
        result += [self._make_file(fi) for fi in data.get("files", [])]

        return sorted(result, key=lambda x: (0 if isinstance(x, MyDocsFolder) else 1,) + natural_sort(x.name))

    def _make_folder(self, fo: dict) -> MyDocsFolder:
        return MyDocsFolder(
            session=self.session,
            parent=self,
            id=str(fo["id"]),
            name=fo["name"],
            color=fo.get("color", ""),
            is_favourite=bool(fo.get("isFavourite", False)),
        )

    def _make_file(self, fi: dict) -> MyDocsFile:
        revision = fi.get("currentRevision") or {}
        return MyDocsFile(
            session=self.session,
            parent=self,
            id=str(fi["id"]),
            name=fi["name"],
            revision_id=str(fi.get("currentRevisionId") or revision.get("id", "")),
            size=int(revision.get("fileSize", 0)),
            is_favourite=bool(fi.get("isFavourite", False)),
        )

    def _make_item(self, data: dict) -> MyDocsItem:
        if data.get("currentRevisionId") or data.get("currentRevision"):
            return self._make_file(data)
        return self._make_folder(data)

    def refresh(self) -> None:
        """Drop the cached listing so the next access re-fetches it."""
        self.__dict__.pop("items", None)

    def __iter__(self) -> Iterator[MyDocsItem]:
        yield from self.items

    def create_folder(self, name: str, *, color: str = "blue") -> MyDocsFolder:
        """Create a subfolder inside this folder and return it."""
        response = self.session.post("/mydoc/api/v1/folders/", json={"name": name, "color": color, "parentId": self.id})
        response.raise_for_status()

        self.refresh()
        return self._make_folder(response.json())

    def upload(self, file_path: str | Path) -> MyDocsFile:
        """Upload a local file into this folder and return the created file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File to upload does not exist: {path}")

        # 1. Reserve a scratch upload directory.
        upload_dir = self.session.json("/upload/api/v1/get-upload-directory")["uploadDir"]

        # 2. Stream the bytes into it (the classic uploader, shared with message attachments).
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        upload = self.session.post(
            "/Upload/Upload/Index",
            files={"file": (path.name, path.read_bytes(), mime_type), "uploadDir": (None, upload_dir)},
        )
        upload.raise_for_status()
        if upload.text.strip().lower() != "true":
            raise SmartSchoolAttachmentUploadError(f"Upload failed for '{path.name}': server returned {upload.text!r}")

        # 3. Register the uploaded bytes as a file in this folder.
        response = self.session.post("/mydoc/api/v1/files/upload", json={"parentId": self.id, "uploadDir": upload_dir})
        response.raise_for_status()

        files = response.json().get("files") or {}
        registered = list(files.values()) if isinstance(files, dict) else files
        if not registered:
            raise SmartSchoolAttachmentUploadError(f"Upload of '{path.name}' was not registered by the server")

        self.refresh()
        chosen = next((fi for fi in registered if fi.get("name") == path.name), registered[0])
        return self._make_file(chosen)

    def delete(self) -> None:
        """Permanently delete this folder and everything in it (use :meth:`trash` to make it reversible)."""
        self.session.delete(f"/mydoc/api/v1/folders/{self.id}").raise_for_status()
        _refresh(self.parent)


@dataclass
class MyDocs(MyDocsFolder):
    """
    Root of the personal "My Documents" storage.

    Example:
    -------
    >>> mydocs = MyDocs(session)
    >>> for item in mydocs:
    ...     print(item.name)
    >>> new_folder = mydocs.create_folder("Homework")
    >>> uploaded = new_folder.upload("essay.docx")
    >>> uploaded.download_to_dir(Path("./backup"))

    """

    name: str = "mydocs"


MyDocsItem: TypeAlias = MyDocsFile | MyDocsFolder
