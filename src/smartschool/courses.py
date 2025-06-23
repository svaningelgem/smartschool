from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from bs4 import Tag, BeautifulSoup

from .common import bs4_html
from .exceptions import SmartSchoolException
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
    description: str | None
    mime_type: str
    size_kb: float
    last_modified: datetime
    download_url: str  # URL to download the file directly
    view_url: str | None  # URL to view the file online (e.g., WOPI)


@dataclass
class FolderItem:
    """Represents a subfolder within a course document folder."""

    id: int
    name: str
    description: str | None
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
            if (item := self._parse_row(row, folder_id))
        ]

    def _parse_document_row(self, row: Tag) -> FileItem:
        """Parse a single table row into a file item."""
        id_ = int(row.get("id")[6:])
        link_texts = {link_text for r in row.select("a") if (link_text := r.get_text(strip=True, separator="\n"))}
        assert len(link_texts) == 1, f"Expected exactly one link text, got {link_texts}"
        filename = link_texts.pop()
        mime_block = row.select_one("div.smsc_cm_body_row_block_mime").get_text(strip=True, separator="\n")
        filetype, size_kb, last_modified = mime_block.split(" - ")

        # <div id="docID_493426" class="smsc_cm_body_row  first">
        # 	<div class="smsc_cm_body_row_block" style="background-image:url('/smsc/img/mime_pdf/mime_pdf_32x32.png');">
        # 		<div class="name">
        # 			<!-- BEGIN realurl --><a target="_blank" href="/Documents/Wopi/Index/docID/493426/courseID/2733/mode/view/ssID/49" title="2025 leerstofoverzicht Engels 4 juni.pdf" index="0" class="smsc_cm_link smsc-download__link ">2025 leerstofoverzicht Engels 4 juni.pdf&nbsp;</a><a href="/Documents/Download/Index/htm/0/courseID/2733/docID/493426/ssID/49" title="Download" class="js-download-link download-link smsc-linkbutton smsc-linkbutton--icon smsc-linkbutton--svg--arrow_download_green" download=""></a><!-- END realurl -->
        #
        #
        # 		</div>
        #
        # 		<div class="spacer"></div>
        # 	</div>
        # 	<div class="smsc_cm_body_row_block_desc"></div>
        #
        # 	<div class="smsc_cm_body_row_block_mime">PDF file - 76.38 KiB - 2025-05-22 13:08</div>
        # </div>
        if len(cells) < 5:
            return None

    def _parse_row(self, row: Tag, parent_id: int) -> DocumentOrFolderItem | None:
        """Parse a single table row into a file or folder item."""
        if row.get("id") and row.get("id").lower().startswith("docid_"):
            return self._parse_document_row(row)
        cells = row.find_all("td", recursive=False)
        if len(cells) < 5:
            return None

        link = cells[1].find("a", href=True)
        if not link:
            return None

        href = link["href"]
        name = link.get_text(strip=True)
        if not name:
            return None

        description = cells[2].get_text(strip=True) or None
        size_kb = self._parse_size(cells[3].get_text(strip=True))
        last_modified = self._parse_date(cells[4].get_text(strip=True))

        # Determine if folder or file
        is_folder = link.find("i", class_="fa-folder") is not None or "/Documents/Index/Index/" in href

        if is_folder:
            folder_match = re.search(r"/ssID/(\d+)", href)
            if folder_match:
                return FolderItem(
                    name=name,
                    ss_id=int(folder_match.group(1)),
                    parent_id=parent_id,
                    description=description,
                )
        else:
            file_match = re.search(r"/docID/(\d+)", href)
            if file_match:
                download_path = href if "/Documents/Download/download/" in href else None
                mime_type = self._extract_mime_type(link)

                return FileItem(
                    name=name,
                    doc_id=int(file_match.group(1)),
                    parent_id=parent_id,
                    description=description,
                    download_url_path=download_path,
                    mime_type=mime_type,
                    size_kb=size_kb,
                    last_modified=last_modified,
                )

        return None

    def _parse_size(self, size_str: str) -> float | None:
        """Parse size string to KB value."""
        if not size_str or size_str.strip() in ("-", ""):
            return None

        match = re.search(r"([\d,.]+)\s*(KB|MB|GB)", size_str, re.IGNORECASE)
        if not match:
            return None

        try:
            value = float(match.group(1).replace(",", "."))
            unit = match.group(2).upper()

            if unit == "MB":
                value *= 1024
            elif unit == "GB":
                value *= 1024 * 1024

            return value
        except ValueError:
            return None

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string to datetime object."""
        if not date_str or date_str.strip() == "-":
            return None

        for fmt in ("%d.%m.%Y %H:%M", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _extract_mime_type(self, link: Tag) -> str | None:
        """Extract MIME type from icon class."""
        icon = link.find("i", class_=re.compile(r"fa-file-"))
        if not icon:
            return None

        icon_class = next((cls for cls in icon.get("class", []) if cls.startswith("fa-file-")), None)
        if not icon_class:
            return None

        mime_map = {
            "pdf": "application/pdf",
            "word": "application/msword",
            "excel": "application/vnd.ms-excel",
            "powerpoint": "application/vnd.ms-powerpoint",
            "image": "image/*",
            "archive": "application/zip",
            "text": "text/plain",
        }

        for key, mime_type in mime_map.items():
            if key in icon_class:
                return mime_type

        return None
