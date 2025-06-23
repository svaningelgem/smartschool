from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from .objects import Course, CourseCondensed
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

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
