#!/usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import requests_cache
from logprise import logger

from smartschool import (
    FileItem,
    FolderItem,
    PathCredentials,
    Smartschool,
    SmartSchoolAuthenticationError,
    SmartSchoolException,
    TopNavCourses,
)
from smartschool.common import create_filesystem_safe_filename

if TYPE_CHECKING:
    from smartschool import CourseCondensed

DEFAULT_DOWNLOAD_DIR = Path.cwd().joinpath("course_downloads").resolve().absolute()


@dataclass
class BulkDownloader:
    """Downloads all documents from all courses automatically."""

    session: Smartschool
    download_dir: Path = DEFAULT_DOWNLOAD_DIR
    _downloaded_count: int = field(init=False, default=0)

    def _download_folder_contents(self, folder: FolderItem, base_path: Path) -> None:
        """Recursively download all files in a folder."""
        for item in folder.items:
            if isinstance(item, FileItem):
                try:
                    item.download_to_dir(base_path)
                    self._downloaded_count += 1
                except Exception as e:
                    logger.exception(f"Failed to download {item.name}: {e}")

            elif isinstance(item, FolderItem):
                folder_path = base_path / create_filesystem_safe_filename(item.name)
                folder_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Processing folder: {folder_path}")
                self._download_folder_contents(item, folder_path)

    def _download_course(self, course: CourseCondensed) -> None:
        """Download all documents from a single course."""
        logger.info(f"Processing course: {course.name}")

        course_path = self.download_dir / create_filesystem_safe_filename(course.name)
        root_folder = FolderItem(self.session, None, course, "(Root)")

        if not root_folder.items:
            logger.info(f"No documents found in course: {course.name}")
            return

        self._download_folder_contents(root_folder, course_path)

    def download_all(self) -> None:
        """Download all documents from all courses."""
        logger.info("Fetching all courses...")

        amount_of_courses = 0
        try:
            for course in TopNavCourses(session=self.session):
                amount_of_courses += 1

                self._download_course(course)

        except SmartSchoolException as e:
            logger.exception(f"Failed to process courses: {e}")

        logger.info(f"Download complete: {self._downloaded_count} files downloaded from {amount_of_courses} courses")


@dataclass
class SmartschoolBulkDownloadApp:
    """Main application for bulk downloading."""

    download_dir: Path = DEFAULT_DOWNLOAD_DIR
    cache_name: str = "smartschool_cache"
    cache_expire_hours: int = 24

    def _setup_cache(self) -> None:
        """Setup requests cache."""
        requests_cache.install_cache(cache_name=self.cache_name, expire_after=self.cache_expire_hours * 3600, backend="sqlite")
        logger.debug(f"Cache setup: {self.cache_name}.sqlite, expires after {self.cache_expire_hours}h")

    def _initialize_session(self) -> Smartschool:
        """Initialize Smartschool session."""
        logger.debug("Initializing session")
        creds = PathCredentials()
        session = Smartschool(creds=creds)
        logger.debug("Authentication successful")
        return session

    def run(self) -> None:
        """Run the bulk download."""
        logger.info("Starting Smartschool Bulk Document Downloader")

        try:
            self._setup_cache()
            session = self._initialize_session()

            BulkDownloader(session, self.download_dir).download_all()

        except FileNotFoundError as e:
            logger.error(f"Initialization failed: {e}")
            logger.error("Ensure credentials.yml exists and is configured correctly")
        except SmartSchoolAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
        except SmartSchoolException:
            logger.exception("Smartschool API error occurred")
        except KeyboardInterrupt:
            logger.info("Download interrupted by user")
        except Exception:
            logger.exception("Unexpected error occurred")
        finally:
            logger.info("Bulk download finished")


if __name__ == "__main__":
    SmartschoolBulkDownloadApp().run()
