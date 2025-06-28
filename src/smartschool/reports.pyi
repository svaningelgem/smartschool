# Auto-generated stub file
from collections.abc import Iterable, Iterator
from datetime import datetime

from . import objects
from .objects import Class_
from .session import SessionMixin, Smartschool

class Report(objects.Report, SessionMixin):
    session: Smartschool
    id: int
    name: str
    icon: str
    date: datetime
    downloadUrl: str
    class_: Class_
    schoolyearLabel: str
    def __init__(
        self,
        session: Smartschool,
        id: int,
        name: str,
        icon: str,
        date: datetime,
        downloadUrl: str,
        class_: Class_,
        schoolyearLabel: str,
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
