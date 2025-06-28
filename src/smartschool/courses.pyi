# Auto-generated stub file
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import overload

from . import objects
from .objects import Course
from .session import SessionMixin, Smartschool

class CourseCondensed(objects.CourseCondensed, SessionMixin):
    session: Smartschool
    name: str
    teacher: str
    url: str
    id: int | None
    platformId: int | None
    descr: str
    icon: str
    def __init__(
        self,
        session: Smartschool,
        name: str,
        teacher: str,
        url: str,
        id: int | None = None,
        platformId: int | None = None,
        descr: str = "",
        icon: str = "",
    ): ...
    def __str__(
        self,
    ): ...

class TopNavCourses(SessionMixin):
    session: Smartschool
    def __init__(
        self,
        session: Smartschool,
    ): ...
    def __iter__(
        self,
    ) -> Iterator[CourseCondensed]: ...

class Courses(SessionMixin):
    session: Smartschool
    def __init__(
        self,
        session: Smartschool,
    ): ...
    def __iter__(
        self,
    ) -> Iterator[Course]: ...

class FileItem(SessionMixin):
    session: Smartschool
    parent: FolderItem
    id: int
    name: str
    mime_type: str
    size_kb: float | str
    last_modified: datetime | str
    download_url: str | None
    view_url: str | None
    def __init__(
        self,
        session: Smartschool,
        parent: FolderItem,
        id: int,
        name: str,
        mime_type: str,
        size_kb: float | str,
        last_modified: datetime | str,
        download_url: str | None = None,
        view_url: str | None = None,
    ): ...
    def download_to_dir(
        self,
        target_directory: Path,
        overwrite: bool = False,
    ) -> Path: ...
    @overload
    def download(self, to_file: Path | str, *, overwrite: bool) -> Path: ...
    @overload
    def download(self) -> bytes: ...
    def download(self, to_file: Path | str | None = None, *, overwrite: bool = False) -> bytes | Path: ...

class InternetShortcut(FileItem):
    session: Smartschool
    parent: FolderItem
    id: int
    name: str
    mime_type: str
    size_kb: float | str
    last_modified: datetime | str
    download_url: str | None
    view_url: str | None
    link: str
    def __init__(
        self,
        session: Smartschool,
        parent: FolderItem,
        id: int,
        name: str,
        mime_type: str,
        size_kb: float | str,
        last_modified: datetime | str,
        download_url: str | None = None,
        view_url: str | None = None,
        link: str = "",
    ): ...

class FolderItem(SessionMixin):
    session: Smartschool
    parent: FolderItem | None
    course: CourseCondensed
    name: str
    browse_url: str | None
    def __init__(
        self,
        session: Smartschool,
        parent: FolderItem | None,
        course: CourseCondensed,
        name: str,
        browse_url: str | None = None,
    ): ...
