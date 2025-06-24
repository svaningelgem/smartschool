from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from bs4 import Tag, BeautifulSoup

from .common import bs4_html, parse_size, convert_to_datetime, parse_mime_type
from .exceptions import SmartSchoolException, SmartSchoolParsingError
from .objects import Course, CourseCondensed
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["CourseDocuments", "Courses", "TopNavCourses"]

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
class FileItem:
    """Represents a file within a course document folder."""

    id: int
    name: str
    mime_type: str
    size_kb: float
    last_modified: datetime
    download_url: str | None = None
    view_url: str | None = None


@dataclass
class FolderItem:
    """Represents a subfolder within a course document folder."""

    id: int
    name: str
    browse_url: str  # URL to browse the contents of this folder


# Define the Union type for items found in document folders
DocumentOrFolderItem = FileItem | FolderItem


@dataclass
class CourseDocuments(SessionMixin):
    """Parse course document folder structure from HTML tables."""

    course: CourseCondensed

    @cached_property
    def course_id(self) -> int:
        return self.course.id

    def _get_folder_html(self, folder_id: int | None = None) -> BeautifulSoup:
        """Fetch HTML content for a specific folder."""
        path = f"/Documents/Index/Index/courseID/{self.course.id}"
        path += f"/ssID/{self.course.platformId}"

        try:
            response = self.session.get(
                path,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": self.session.create_url("/"),
                },
            )
            response.raise_for_status()
            return bs4_html(response)
        except Exception as e:
            raise SmartSchoolException(f"Failed to fetch folder HTML: {e}") from e

    def list_folder_contents(self, folder_id: int | None = None) -> list[DocumentOrFolderItem]:
        """Parse HTML table to extract files and folders."""
        soup = self._get_folder_html(folder_id)
        rows = soup.select("div.smsc_cm_body_row", recursive=False)

        return [
            item
            for row in rows
            if (item := self._parse_row(row))
        ]

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
                id_ = re.search("/parentID/(\d+)/", browse_url).group(1)
                return FolderItem(
                    id=int(id_),
                    name=name,
                    browse_url=browse_url,
                )

        raise SmartSchoolParsingError("No browse URL found")

    def _parse_row(self, row: Tag) -> DocumentOrFolderItem | None:
        """Parse a single table row into a file or folder item."""
        if row.get("id") and row.get("id").lower().startswith("docid_"):
            return self._parse_document_row(row)
        return self._parse_folder_row(row)
