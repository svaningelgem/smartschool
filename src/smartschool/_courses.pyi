# Auto-generated stub file
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from functools import cached_property
from typing import TypeAlias

from . import _objects as objects
from ._common import DownloadableFile
from ._session import SessionMixin, Smartschool

class CourseCondensed(objects.CourseCondensed, SessionMixin):
    session: Smartschool
    name: str
    teacher: str
    url: str
    id: int | None
    platform_id: int | None
    descr: str
    icon: str
    def __init__(
        self,
        session: Smartschool,
        name: str,
        teacher: str,
        url: str,
        id: int | None = None,
        platform_id: int | None = None,
        descr: str = "",
        icon: str = "",
    ): ...
    def __str__(self): ...
    @property
    def items(self) -> list[DocumentOrFolderItem]: ...

class TopNavCourses(SessionMixin):
    session: Smartschool
    def __init__(self, session: Smartschool): ...
    def __iter__(self) -> Iterator[CourseCondensed]: ...

class Courses(SessionMixin):
    session: Smartschool
    def __init__(self, session: Smartschool): ...
    def __iter__(self) -> Iterator[objects.Course]: ...

class CourseList(SessionMixin):
    session: Smartschool
    def __init__(self, session: Smartschool): ...
    def __iter__(self) -> Iterator[objects.PlannedElementCourse]: ...

class FileItem(DownloadableFile, SessionMixin):
    session: Smartschool
    parent: FolderItem
    id: int
    name: str
    mime_type: str
    size_kb: float | str | None
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
        size_kb: float | str | None,
        last_modified: datetime | str,
        download_url: str | None = None,
        view_url: str | None = None,
    ): ...
    @cached_property
    def filename(self) -> str: ...

class InternetShortcut(FileItem):
    session: Smartschool
    parent: FolderItem
    id: int
    name: str
    mime_type: str
    size_kb: float | str | None
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
        size_kb: float | str | None,
        last_modified: datetime | str,
        download_url: str | None = None,
        view_url: str | None = None,
        link: str = "",
    ): ...
    @cached_property
    def filename(self) -> str: ...

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
    @cached_property
    def items(self) -> list[DocumentOrFolderItem]: ...

DocumentOrFolderItem: TypeAlias = FileItem | FolderItem | InternetShortcut
