from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

from ._common import DownloadableFile, create_filesystem_safe_filename, natural_sort
from ._exceptions import SmartSchoolAttachmentUploadError
from ._session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["MyDocs", "MyDocsFile", "MyDocsFolder", "MyDocsItem"]


@dataclass
class MyDocsFile(DownloadableFile, SessionMixin):
    """A file in the personal "My Documents" (``/mydoc``) storage."""

    parent: MyDocsFolder = field(repr=False)
    id: str = ""
    name: str = ""
    revision_id: str = ""
    size: int = 0

    @cached_property
    def filename(self) -> str:
        return create_filesystem_safe_filename(self.name)

    def _real_download(self, target: Path | None) -> bytes | Path:
        # The download endpoint 302-redirects to a (short-lived) presigned URL; requests follows it.
        response = self.session.get(f"/mydoc/api/v1/files/{self.id}/revisions/{self.revision_id}/download")
        response.raise_for_status()

        if target:
            target.write_bytes(response.content)
            return target

        return response.content

    def delete(self) -> None:
        """Permanently delete this file."""
        self.session.delete(f"/mydoc/api/v1/files/{self.id}").raise_for_status()
        self.parent.refresh()


@dataclass
class MyDocsFolder(SessionMixin):
    """A folder in the personal "My Documents" storage."""

    parent: MyDocsFolder | None = field(repr=False, default=None)
    id: str = ""
    name: str = ""
    color: str = ""

    @property
    def _listing_url(self) -> str:
        # An empty id addresses the root folder.
        return "/mydoc/api/v1/directory-listing" + (f"/{self.id}" if self.id else "")

    @cached_property
    def items(self) -> list[MyDocsItem]:
        data = self.session.json(self._listing_url)

        result: list[MyDocsItem] = []

        for fo in data.get("folders", []):
            result.append(
                MyDocsFolder(
                    session=self.session,
                    parent=self,
                    id=str(fo["id"]),
                    name=fo["name"],
                    color=fo.get("color", ""),
                )
            )

        for fi in data.get("files", []):
            result.append(self._build_file(fi))

        return sorted(result, key=lambda x: (0 if isinstance(x, MyDocsFolder) else 1,) + natural_sort(x.name))

    def _build_file(self, fi: dict) -> MyDocsFile:
        revision = fi.get("currentRevision") or {}
        return MyDocsFile(
            session=self.session,
            parent=self,
            id=str(fi["id"]),
            name=fi["name"],
            revision_id=str(fi.get("currentRevisionId") or revision.get("id", "")),
            size=int(revision.get("fileSize", 0)),
        )

    def refresh(self) -> None:
        """Drop the cached listing so the next access re-fetches it."""
        self.__dict__.pop("items", None)

    def __iter__(self) -> Iterator[MyDocsItem]:
        yield from self.items

    def create_folder(self, name: str, *, color: str = "blue") -> MyDocsFolder:
        """Create a subfolder inside this folder and return it."""
        response = self.session.post("/mydoc/api/v1/folders/", json={"name": name, "color": color, "parentId": self.id})
        response.raise_for_status()
        data = response.json()

        self.refresh()
        return MyDocsFolder(session=self.session, parent=self, id=str(data["id"]), name=data["name"], color=data.get("color", color))

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
        return self._build_file(chosen)

    def delete(self) -> None:
        """Permanently delete this folder and everything in it."""
        self.session.delete(f"/mydoc/api/v1/folders/{self.id}").raise_for_status()
        if self.parent is not None:
            self.parent.refresh()


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
