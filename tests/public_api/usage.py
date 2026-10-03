"""The public API as a user's type checker sees it: dev/check_public_api.sh runs ty, pyright and mypy on this against the built wheel."""

from datetime import date, datetime
from pathlib import Path

from typing_extensions import assert_type

from smartschool import (
    AgendaHour,
    AgendaLesson,
    Component,
    MessageHeaders,
    Results,
    ShortMessage,
    Smartschool,
    SmartschoolHours,
    SmartschoolLessons,
    create_filesystem_safe_path,
)


def query_classes_can_be_instantiated(session: Smartschool) -> None:
    SmartschoolLessons(session)
    SmartschoolHours(session)
    MessageHeaders(session)


def models_keep_their_constructor_and_field_types(lesson: AgendaLesson) -> None:
    assert_type(Component(id=1, name="Wiskunde", abbreviation="WIS").name, str)
    assert_type(lesson.course, str)
    assert_type(lesson.date, date)


def iteration_yields_typed_items(session: Smartschool) -> None:
    for lesson in SmartschoolLessons(session):
        assert_type(lesson, AgendaLesson)
    for header in MessageHeaders(session):
        assert_type(header, ShortMessage)
    assert_type(SmartschoolHours(session).get(), AgendaHour)
    for result in Results(session):
        assert_type(result.name, str)
        assert_type(result.date, datetime)


def functions_keep_their_signature() -> None:
    assert_type(create_filesystem_safe_path("a/b.txt"), Path)
