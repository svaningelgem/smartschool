from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, TypeAlias

from .common import (
    bs4_html,
    natural_sort,
    save_test_response,
)
from .courses import FileItem, InternetShortcut
from .exceptions import SmartSchoolException, SmartSchoolParsingError
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bs4 import BeautifulSoup, Tag

__all__ = ["Intradesk", "IntradeskFolder"]


@dataclass
class IntradeskFolder(SessionMixin):
    """Represents a folder in the student's personal intradesk."""

    parent: IntradeskFolder | None = field(repr=False)
    platform_id: int = field(repr=False)
    name: str
    browse_url: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.browse_url is None:
            self.browse_url = f"/Intradesk/Index/Index/ssID/{self.platform_id}"

    def _get_folder_html(self) -> BeautifulSoup:
        """Fetch HTML content for this folder."""
        try:
            response = self.session.get(
                self.browse_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": self.session.create_url("/"),
                },
            )
            response.raise_for_status()
            save_test_response(response)
            return bs4_html(response)
        except Exception as e:
            raise SmartSchoolException(f"Failed to fetch folder HTML: {e}") from e

    def _get_mime_from_row_image(self, row: Tag) -> str | None:
        for entry in row.select_one("div.smsc_cm_body_row_block").get("style").split(";"):
            if not entry.strip():
                continue
            first, second = entry.split(":", 1)
            if first.strip() == "background-image":
                return re.search("/mime_[^_]+_([^/_]+)", second).group(1)
        return None

    def _extract_url_from_onclick(self, onclick: str) -> str | None:
        """Extract URL from window.open onclick JavaScript."""
        match = re.search(r'window\.open\(["\']([^"\']+)["\']', onclick)
        return match.group(1) if match else None

    def _figure_out_item_links(self, row: Tag) -> tuple[str | None, str | None, str | None]:
        """Extract download and view links from row elements."""
        links = row.select("a")
        dl_link, view_link, onclick_link = None, None, None

        for link in links:
            classes = link.get("class") or []
            href = link.get("href")
            onclick = link.get("onclick")

            if any(
                dlclass in classes
                for dlclass in [
                    "download-link",
                    "smsc-download__icon",
                    "smsc-download__icon--large-margin",
                    "smsc-download__icon--download",
                ]
            ):
                dl_link = href
            elif "smsc-download__link" in classes:
                view_link = href
            elif "smsc_cm_link" in classes and onclick:
                onclick_link = self._extract_url_from_onclick(onclick)

        return dl_link, view_link, onclick_link

    def _parse_document_row(self, row: Tag) -> FileItem | InternetShortcut:
        """Parse a single table row into a file item."""
        id_ = int(row.get("id")[6:])
        mime_block = row.select_one("div.smsc_cm_body_row_block_mime").get_text(strip=True, separator="\n")
        _, size_kb, last_modified = mime_block.split(" - ")
        mime_style = self._get_mime_from_row_image(row)

        link_texts = [link_text for r in row.select("a") if (link_text := r.get_text(strip=True, separator="\n"))]
        if len(link_texts) == 0:
            raise AssertionError("Expected exactly one link text, got None")

        filename = link_texts[0]

        inline_links = row.select("div.smsc_cm_body_row_block_inline a,div.smsc_cm_body_row_block_inline iframe")
        if inline_links:
            inline_link = inline_links[0]
            if inline_link.name == "iframe":
                final_link = inline_link["src"]
            elif inline_link.name == "a":
                final_link = inline_link["href"]
            else:
                raise AssertionError(f"Unknown inline link type: {inline_link.name}")

            return InternetShortcut(
                session=self.session,
                parent=self,
                id=0,
                name=link_texts[0],
                mime_type=mime_style,
                size_kb=size_kb,
                last_modified=last_modified,
                link=final_link,
            )

        dl_link, view_link, onclick_link = self._figure_out_item_links(row)
        if onclick_link is not None:
            return InternetShortcut(
                session=self.session,
                parent=self,
                id=id_,
                name=link_texts[0],
                mime_type=mime_style,
                size_kb=size_kb,
                last_modified=last_modified,
                link=onclick_link,
            )

        return FileItem(
            session=self.session,
            parent=self,
            id=id_,
            name=filename,
            mime_type=mime_style,
            size_kb=size_kb,
            last_modified=last_modified,
            download_url=dl_link,
            view_url=view_link,
        )

    def _parse_folder_row(self, row: Tag) -> IntradeskFolder:
        """Parse a single table row into a subfolder item."""
        for link in row.select("a"):
            classes = link.get("class") or []
            if "smsc_cm_link" in classes:
                return IntradeskFolder(
                    session=self.session,
                    parent=self,
                    platform_id=self.platform_id,
                    name=link.get_text(strip=True, separator="\n"),
                    browse_url=link["href"],
                )
        raise SmartSchoolParsingError("No browse URL found")

    def _parse_row(self, row: Tag) -> IntradeskDocumentOrFolder | None:
        """Parse a single table row into a file or folder item."""
        if row.get("id") and row.get("id").lower().startswith("docid_"):
            return self._parse_document_row(row)
        return self._parse_folder_row(row)

    @cached_property
    def items(self) -> list[IntradeskDocumentOrFolder]:
        """Fetch items from this folder."""
        soup = self._get_folder_html()
        rows = soup.select("div.smsc_cm_body_row", recursive=False)
        items = [item for row in rows if (item := self._parse_row(row))]
        return sorted(items, key=lambda x: (0 if isinstance(x, IntradeskFolder) else 1,) + natural_sort(x.name))


IntradeskDocumentOrFolder: TypeAlias = FileItem | IntradeskFolder | InternetShortcut


@dataclass
class Intradesk(SessionMixin):
    """
    Provides access to the student's personal intradesk (file repository).

    Example:
    -------
    >>> intradesk = Intradesk(session)
    >>> for item in intradesk:
    >>>     print(item.name)
    My Folder
    My Document.pdf

    """

    @cached_property
    def _platform_id(self) -> int:
        """Get the platform ID from the session's authenticated user."""
        return int(str(self.session.authenticated_user["id"]).split("_")[0])

    @property
    def root(self) -> IntradeskFolder:
        """Get the root intradesk folder."""
        return IntradeskFolder(
            session=self.session,
            parent=None,
            platform_id=self._platform_id,
            name="(Root)",
        )

    def __iter__(self) -> Iterator[IntradeskDocumentOrFolder]:
        yield from self.root.items
