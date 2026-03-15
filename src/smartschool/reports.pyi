# Auto-generated stub file
from collections.abc import Iterable, Iterator
from datetime import datetime

from . import objects
from .objects import SchoolClass
from .session import SessionMixin, Smartschool

class Report(objects.Report, SessionMixin):
    session: Smartschool
    id: int
    name: str
    icon: str
    date: datetime
    download_url: str
    class_: SchoolClass
    schoolyear_label: str
    def __init__(
        self,
        session: Smartschool,
        id: int,
        name: str,
        icon: str,
        date: datetime,
        download_url: str,
        class_: SchoolClass,
        schoolyear_label: str,
    ): ...
    def download(
        self,
    ) -> bytes: ...

class Reports(SessionMixin, Iterable[Report]):
    session: Smartschool
    def __init__(
        self,
        session: Smartschool,
    ): ...
    def __iter__(
        self,
    ) -> Iterator[Report]: ...
