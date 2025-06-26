#!/usr/bin/env python
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

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
from smartschool.common import natural_sort

if TYPE_CHECKING:
    from smartschool import (
        CourseCondensed,
        DocumentOrFolderItem,
    )

DEFAULT_DOWNLOAD_DIR = Path.cwd().joinpath("course_downloads").resolve().absolute()


def get_user_choice(prompt: str, max_value: int, allow_up: bool = True) -> str | int | None:  # noqa: FBT001
    """Get validated user input (number, 'u', 'q')."""
    while True:
        choice = ""

        try:
            choice = input(prompt).strip().lower()
            if choice == "q":
                return choice
            if choice == "u":
                if not allow_up:
                    logger.warning("Cannot go up from root folder")
                    continue
                return choice
            if choice.isdigit():
                num_choice = int(choice)
                if 1 <= num_choice <= max_value:
                    return num_choice
                logger.warning(f"Invalid number. Please enter a number between 1 and {max_value}")
            else:
                up_text = ", 'u'" if allow_up else ""
                logger.warning(f"Invalid input. Please enter a number{up_text}, or 'q'")
        except (ValueError, EOFError):
            if choice == "":
                logger.info("Exiting")
                return "q"
            logger.warning("Invalid input")


@dataclass
class DocumentBrowser:
    """Interactive browser for Smartschool course documents."""

    session: Smartschool
    course: CourseCondensed
    config: AppConfig
    _path_items: list[FolderItem] = field(init=False, repr=False, default_factory=list)

    def __post_init__(self):
        self._path_items = [FolderItem(self.session, self.course, "(Root)")]

    @cached_property
    def _download_dir(self) -> Path:
        if self.config.download_dir:
            return Path(self.config.download_dir)
        return DEFAULT_DOWNLOAD_DIR

    @property
    def _current_location(self) -> str:
        return " / ".join(item.name for item in self._path_items)

    @property
    def _is_at_root(self) -> bool:
        return len(self._path_items) == 1

    @property
    def _current_folder(self) -> FolderItem:
        return self._path_items[-1]

    def _display_items(self, items: list[DocumentOrFolderItem]) -> None:
        """Display folders and files with numbers."""
        if not items:
            logger.info("Folder is empty")
            return

        for i, item in enumerate(items, 1):
            item_type = "Folder" if isinstance(item, FolderItem) else "File"
            logger.info(f"[{i}] {item_type}: {item.name}")

    def _navigate_up(self) -> None:
        """Navigate up one level in the folder hierarchy."""
        if self._is_at_root:
            logger.warning("Already at root folder")
            return

        self._path_items.pop()

    def browse(self) -> None:
        """Main browsing loop."""
        logger.info(f"Starting to browse course: {self.course.name}")

        while True:
            logger.info(f"Current Location: {self._current_location}")

            self._display_items(self._current_folder.items)

            if not self._current_folder.items:
                if self._is_at_root:
                    logger.info("No documents found in course")
                    break

                choice = get_user_choice("Enter 'u' to go up, 'q' to quit: ", 0)
            else:
                prompt_parts = ["Enter number to open/download"]
                if not self._is_at_root:
                    prompt_parts.append("'u' to go up")
                prompt_parts.append("'q' to quit: ")
                prompt = ", ".join(prompt_parts)

                choice = get_user_choice(prompt, len(self._current_folder.items), allow_up=not self._is_at_root)

            if choice == "q":
                break
            elif choice == "u" and not self._is_at_root:
                self._navigate_up()
            elif isinstance(choice, int):
                selected_item = self._current_folder.items[choice - 1]
                if isinstance(selected_item, FolderItem):
                    self._path_items.append(selected_item)
                elif isinstance(selected_item, FileItem):
                    target = self._download_dir / self.course.name
                    for item in self._path_items[1:]:
                        target /= item.name
                    selected_item.download_to_dir(target)


@dataclass
class CourseSelector:
    """Handles course selection interface."""

    session: Smartschool

    def _display_courses(self, courses: list[CourseCondensed]) -> None:
        """Display available courses."""
        logger.info("Available Courses:")

        for i, course in enumerate(courses, start=1):
            logger.info(f"[{i}] {course}")

    def select_course(self) -> CourseCondensed | None:
        """Select a course from available options."""
        logger.info("Fetching courses...")
        try:
            courses = sorted(TopNavCourses(session=self.session), key=lambda item: natural_sort(item.name))
            self._display_courses(courses)

            choice = get_user_choice("Select a course number: ", len(courses), allow_up=False)

            if not isinstance(choice, int):
                return None

            selected_course = courses[choice - 1]
            logger.info(f"Selected Course: {selected_course}")
            return selected_course  # noqa: TRY300

        except SmartSchoolException as e:
            logger.error(f"Error fetching courses: {e}")
            return None


@dataclass
class AppConfig:
    """Application configuration."""

    download_dir: Path = DEFAULT_DOWNLOAD_DIR
    credentials_file: str = PathCredentials.CREDENTIALS_FILENAME


@dataclass
class SmartschoolBrowserApp:
    """Main application controller."""

    config: AppConfig = field(default_factory=AppConfig)

    def _initialize_session(self) -> Smartschool:
        """Initialize a Smartschool session with credentials."""
        logger.debug("Initializing session")
        creds = PathCredentials()
        session = Smartschool(creds=creds)
        logger.debug("Authentication successful")
        return session

    def run(self) -> None:
        """Run the main application."""
        logger.info("Starting Smartschool Course Document Browser")

        try:
            session = self._initialize_session()

            course_selector = CourseSelector(session)
            selected_course = course_selector.select_course()

            if not selected_course:
                logger.info("No course selected, exiting")
                return

            DocumentBrowser(session, selected_course, self.config).browse()
        except FileNotFoundError as e:
            logger.error(f"Initialization failed: {e}")
            logger.error("Ensure credentials.yml exists and is configured correctly")
        except SmartSchoolAuthenticationError as e:
            logger.error(f"Initialization failed: {e}")
        except SmartSchoolException:
            logger.exception("A Smartschool API error occurred")
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception:
            logger.exception("An unexpected critical error occurred")
        finally:
            logger.info("Smartschool Course Document Browser finished")


if __name__ == "__main__":
    SmartschoolBrowserApp().run()
