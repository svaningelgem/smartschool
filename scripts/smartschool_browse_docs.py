from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from logprise import logger
from smartschool import Course, DocumentOrFolderItem


from smartschool import (
    Courses,
    FileItem,
    FolderItem,
    PathCredentials,
    Smartschool,
    SmartSchoolAuthenticationError,
    SmartSchoolException,
)
from smartschool.courses import CourseDocuments, TopNavCourses
from smartschool.objects import CourseCondensed

# from smartschool.file_fetch import browse_course_documents, download_document

DEFAULT_DOWNLOAD_DIR = Path.cwd().joinpath("course_downloads").resolve().absolute()



def get_user_choice(prompt: str, max_value: int, allow_up: bool = True) -> str | int | None:
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
    path_items: list[FolderItem] = field(init=False, repr=False, default_factory=list)

    def __post_init__(self):
        self.documents = CourseDocuments(self.session, course=self.course)

    @property
    def _current_folder_id(self):
        if self._is_at_root:
            return 0
        return self.path_items[-1].id

    @property
    def _path_as_str(self) -> str:
        if self._is_at_root:
            return "(Root)"
        return " / ".join(item.name for item in self.path_items)

    @property
    def _is_at_root(self) -> bool:
        return not self.path_items

    def display_items(self, items: list[DocumentOrFolderItem]) -> None:
        """Display folders and files with numbers."""
        if not items:
            logger.info("Folder is empty")
            return

        for i, item in enumerate(items, 1):
            item_type = "Folder" if isinstance(item, FolderItem) else "File"
            logger.info(f"[{i}] {item_type}: {item.name}")

    def _get_current_items(self) -> list[DocumentOrFolderItem]:
        """Fetch items for current folder."""
        try:
            items = self.documents.list_folder_contents(self._current_folder_id)
            return sorted(items, key=lambda x: (0 if isinstance(x, FolderItem) else 1, x.name))
        except SmartSchoolAuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise
        except SmartSchoolException as e:
            logger.error(f"Error fetching folder contents: {e}")
            return []

    def _navigate_up(self) -> None:
        """Navigate up one level in folder hierarchy."""
        if self.state.is_at_root:
            logger.warning("Already at root folder")
            return

        self.state.path_items.pop()
        self.state.folder_id = self.state.path_items[-1].id if self.state.path_items else None

    def _navigate_into_folder(self, folder: FolderItem) -> None:
        """Navigate into selected folder."""
        self.state.folder_id = folder.id
        self.state.path_items.append(folder)
        logger.debug(f"Navigated into folder: {folder.name}")

    def _create_safe_filename(self, filename: str) -> str:
        """Create filesystem-safe filename."""
        return "".join(c if c.isalnum() or c in (" ", ".", "_", "-") else "_" for c in filename)

    def _download_file(self, file: FileItem, course: Course) -> None:
        """Download selected file."""
        logger.info(f"Downloading file: {file.name}")
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        safe_filename = self._create_safe_filename(file.name)
        target_file = DOWNLOAD_DIR / safe_filename

        try:
            containing_folder_id = self.state.folder_id or 0
            download_document(
                course_id=course.id,
                doc_id=file.id,
                ss_id=containing_folder_id,
                target_path=target_file,
                overwrite=False,
                smartschool=self.session,
            )
            logger.info(f"Successfully downloaded '{file.name}' to {target_file}")
        except FileExistsError:
            logger.error(f"File already exists at '{target_file}'. Delete existing file or use overwrite=True")
        except SmartSchoolException as e:
            logger.error(f"Download failed: {e}")
        except Exception:
            logger.exception(f"Unexpected error during download of '{file.name}'")

    def browse(self) -> None:
        """Main browsing loop."""
        logger.info(f"Starting to browse course: {self.course.name}")

        while True:
            logger.info(f"Current Location: {self._path_as_str}")

            try:
                items = self._get_current_items()
            except SmartSchoolAuthenticationError:
                break

            self.display_items(items)

            if not items:
                if self.state.is_at_root:
                    choice = get_user_choice("Enter 'q' to quit: ", 0, allow_up=False)
                else:
                    choice = get_user_choice("Enter 'u' to go up, 'q' to quit: ", 0)
            else:
                prompt_parts = ["Enter number to open/download"]
                if not self.state.is_at_root:
                    prompt_parts.append("'u' to go up")
                prompt_parts.append("'q' to quit: ")
                prompt = ", ".join(prompt_parts)

                choice = get_user_choice(prompt, len(items), allow_up=not self.state.is_at_root)

            if choice == "q":
                break
            elif choice == "u" and not self.state.is_at_root:
                self._navigate_up()
            elif isinstance(choice, int):
                selected_item = items[choice - 1]
                if isinstance(selected_item, FolderItem):
                    self._navigate_into_folder(selected_item)
                elif isinstance(selected_item, FileItem):
                    self._download_file(selected_item, course)


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
            courses = sorted(TopNavCourses(session=self.session), key=lambda item: item.name.lower())
            self._display_courses(courses)

            choice = get_user_choice("Select a course number: ", len(courses), allow_up=False)

            if not isinstance(choice, int):
                return None

            selected_course = courses[choice - 1]
            logger.info(f"Selected Course: {selected_course}")
            return selected_course

        except SmartSchoolException as e:
            logger.error(f"Error fetching courses: {e}")
            return None


@dataclass
class AppConfig:
    """Application configuration."""
    download_dir: Path = DEFAULT_DOWNLOAD_DIR
    credentials_file: str = PathCredentials.CREDENTIALS_FILENAME


class SmartschoolBrowserApp:
    """Main application controller."""

    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig()
        self.download_dir = self.config.download_dir or DEFAULT_DOWNLOAD_DIR

    def _initialize_session(self) -> Smartschool:
        """Initialize Smartschool session with credentials."""
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

            DocumentBrowser(session, selected_course).browse()
        except FileNotFoundError as e:
            logger.error(f"Initialization failed: {e}")
            logger.error("Ensure credentials.yml exists and is configured correctly")
        except (SmartSchoolAuthenticationError, FileNotFoundError) as e:
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
