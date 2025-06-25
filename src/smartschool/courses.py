from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, overload

from loguru import logger

from .common import bs4_html, convert_to_datetime, create_filesystem_safe_filename, parse_mime_type, parse_size
from .exceptions import SmartSchoolException, SmartSchoolParsingError
from .objects import Course, CourseCondensed
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bs4 import BeautifulSoup, Tag
    from requests import Response

__all__ = ["Courses", "TopNavCourses"]


@dataclass
class TopNavCourses(SessionMixin):
    """
    Retrieves a list of the courses which are available from the top navigation bar.

    This structure is different from the `Courses` results.

    Example:
    -------
    >>> for course in TopNavCourses(session):
    >>>     print(course.name)
    Aardrijkskunde_3_LOP_2023-2024
    bibliotheek

    """

    @cached_property
    def _list(self) -> list[CourseCondensed]:
        return [CourseCondensed(**course) for course in self.session.json("/Topnav/getCourseConfig", method="post")["own"]]

    def __iter__(self) -> Iterator[CourseCondensed]:
        yield from self._list


@dataclass
class Courses(SessionMixin):
    """
    Retrieves a list of the courses.

    This structure is different from the `TopNavCourses` results.

    To reproduce: go to "Results", one of the XHR calls is this one

    Example:
    -------
    >>> for course in Courses(session):
    >>>     print(course.name)
    Aardrijkskunde
    Biologie

    """

    @cached_property
    def _list(self) -> list[Course]:
        return [Course(**course) for course in self.session.json("/results/api/v1/courses/")]

    def __iter__(self) -> Iterator[Course]:
        yield from self._list


@dataclass
class FileItem(SessionMixin):
    """Represents a file within a course document folder."""

    id: int
    name: str
    mime_type: str
    size_kb: float
    last_modified: datetime
    download_url: str | None = None
    view_url: str | None = None

    @overload
    def download(self, to_file: Path | str) -> Path: ...

    @overload
    def download(self) -> bytes: ...

    def download(self, to_file: Path | str | None = None) -> bytes | Path:
        target = None
        if to_file:
            target = Path(to_file).resolve().absolute()
            target = target.with_name(create_filesystem_safe_filename(target.name))
            target.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Downloading file: {target.name}")

        response: Response = self.session.get(self.download_url)
        response.raise_for_status()

        if not to_file:
            return response.content

        target.write_bytes(response.content)
        return target


@dataclass
class FolderItem(SessionMixin):
    """Represents a subfolder within a course document folder."""

    course: CourseCondensed
    name: str
    browse_url: str | None = None

    def __post_init__(self):
        if self.browse_url is None:
            self.browse_url = f"/Documents/Index/Index/courseID/{self.course.id}/ssID/{self.course.platformId}"

    def _get_folder_html(self) -> BeautifulSoup:
        """Fetch HTML content for a specific folder."""
        try:
            response = self.session.get(
                self.browse_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": self.session.create_url("/"),
                },
            )
            response.raise_for_status()
            return bs4_html(response)
        except Exception as e:
            raise SmartSchoolException(f"Failed to fetch folder HTML: {e}") from e

    def _parse_document_row(self, row: Tag) -> FileItem:
        """Parse a single table row into a file item."""
        id_ = int(row.get("id")[6:])
        link_texts = {link_text for r in row.select("a") if (link_text := r.get_text(strip=True, separator="\n"))}
        assert len(link_texts) == 1, f"Expected exactly one link text, got {link_texts}"
        filename = link_texts.pop()
        mime_block = row.select_one("div.smsc_cm_body_row_block_mime").get_text(strip=True, separator="\n")
        filetype, size_kb, last_modified = mime_block.split(" - ")
        filetype = parse_mime_type(filetype)
        size_kb = parse_size(size_kb)
        last_modified = convert_to_datetime(last_modified)

        links = row.select("a")
        dl_link, view_link = None, None
        for link in links:
            classes = link.get("class") or []
            if "download-link" in classes:
                dl_link = link["href"]
            elif "smsc-download__link" in classes:
                view_link = link["href"]

        return FileItem(
            session=self.session,
            id=id_,
            name=filename,
            mime_type=filetype,
            size_kb=size_kb,
            last_modified=last_modified,
            download_url=dl_link,
            view_url=view_link,
        )

    def _parse_folder_row(self, row: Tag) -> FolderItem:
        """Parse a single table row into a folder item."""
        for link in row.select("a"):
            classes = link.get("class") or []
            if "smsc_cm_link" in classes:
                browse_url = link["href"]
                name = link.get_text(strip=True, separator="\n")
                return FolderItem(
                    session=self.session,
                    course=self.course,
                    name=name,
                    browse_url=browse_url,
                )

        raise SmartSchoolParsingError("No browse URL found")

    def _parse_row(self, row: Tag) -> DocumentOrFolderItem | None:
        """Parse a single table row into a file or folder item."""
        if row.get("id") and row.get("id").lower().startswith("docid_"):
            return self._parse_document_row(row)
        return self._parse_folder_row(row)

    def list_folder_contents(self) -> list[DocumentOrFolderItem]:
        """Fetch items from this folder."""
        soup = self._get_folder_html()
        rows = soup.select("div.smsc_cm_body_row", recursive=False)

        items = [item for row in rows if (item := self._parse_row(row))]
        return sorted(items, key=lambda x: (0 if isinstance(x, FolderItem) else 1, x.name))


DocumentOrFolderItem = FileItem | FolderItem
