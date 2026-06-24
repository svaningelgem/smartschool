# Auto-generated stub file
from __future__ import annotations

from abc import ABC
from datetime import date, datetime

from . import _objects as objects
from ._session import SessionMixin, Smartschool
from ._xml_interface import SmartschoolXmlWeeklyCache

class AgendaPoster(SmartschoolXmlWeeklyCache, ABC):
    session: Smartschool
    cache: dict
    timestamp_to_use: datetime | date | None
    def __init__(
        self,
        session: Smartschool,
        cache: dict = ...,
        timestamp_to_use: datetime | date | None = None,
    ): ...

class AgendaLesson(SessionMixin, objects.AgendaLesson):
    moment_id: str
    lesson_id: str
    hour_id: str
    date: date
    subject: str | None
    course: str
    course_title: str
    classroom: str
    classroom_title: str
    teacher: str
    teacher_title: str
    klassen: str
    klassen_title: str
    class_ids: str
    both_start_status: str
    assignment_end_status: str
    test_deadline_status: str
    note_status: str
    note: str | None
    date_listview: str
    hour: str
    activity: str
    activity_id: str | None
    color: str
    hour_value: str
    components_hidden: object
    freeday_icon: str
    some_subjects_empty: str | None
    session: Smartschool
    def __init__(
        self,
        moment_id: str,
        lesson_id: str,
        hour_id: str,
        date: date,
        subject: str | None,
        course: str,
        course_title: str,
        classroom: str,
        classroom_title: str,
        teacher: str,
        teacher_title: str,
        klassen: str,
        klassen_title: str,
        class_ids: str,
        both_start_status: str,
        assignment_end_status: str,
        test_deadline_status: str,
        note_status: str,
        note: str | None,
        date_listview: str,
        hour: str,
        activity: str,
        activity_id: str | None,
        color: str,
        hour_value: str,
        components_hidden: object,
        freeday_icon: str,
        some_subjects_empty: str | None,
        session: Smartschool,
    ): ...

class SmartschoolLessons(AgendaPoster):
    session: Smartschool
    cache: dict
    timestamp_to_use: datetime | date | None
    def __init__(
        self,
        session: Smartschool,
        cache: dict = ...,
        timestamp_to_use: datetime | date | None = None,
    ): ...

class SmartschoolHours(AgendaPoster):
    session: Smartschool
    cache: dict
    timestamp_to_use: datetime | date | None
    def __init__(
        self,
        session: Smartschool,
        cache: dict = ...,
        timestamp_to_use: datetime | date | None = None,
    ): ...
    def search_by_hour_id(
        self,
        hour_id: str,
    ): ...

class SmartschoolMomentInfos(AgendaPoster):
    session: Smartschool
    cache: dict
    timestamp_to_use: datetime | date | None
    def __init__(
        self,
        session: Smartschool,
        moment_id: str,
    ): ...
