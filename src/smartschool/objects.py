from __future__ import annotations

import base64
from datetime import date, datetime
from functools import cached_property
from typing import Annotated, Literal

from pydantic import AliasChoices, BeforeValidator, constr
from pydantic.dataclasses import Field, dataclass

from .common import as_float
from .session import session

String = constr(strip_whitespace=True)


def convert_to_datetime(x: str | String | datetime) -> datetime:
    if isinstance(x, datetime):
        if x.tzinfo is None:
            raise ValueError("No timezone information found in this date")
        return x

    try:
        return datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:  # 2023-11-16 08:24
        return datetime.strptime(x, "%Y-%m-%d %H:%M")


def convert_to_date(x: str | String | date | datetime) -> date:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x

    return datetime.strptime(x, "%Y-%m-%d").date()


Url = Annotated[str | String, BeforeValidator(lambda x: session.create_url(x))]
Date = Annotated[date, BeforeValidator(convert_to_date)]
DateTime = Annotated[datetime, BeforeValidator(convert_to_datetime)]


@dataclass
class CourseGraphic:
    type: Literal["icon"]
    value: String


@dataclass
class ResultGraphic:
    type: Literal["percentage"]
    color: Literal["green", "red"]
    value: int
    description: String

    @cached_property
    def achieved_points(self) -> float:
        return as_float(self.description.split("/")[0])

    @cached_property
    def total_points(self) -> float:
        return as_float(self.description.split("/")[1])

    @property
    def percentage(self) -> float:
        return self.achieved_points / self.total_points


@dataclass
class PersonDescription:
    startingWithFirstName: String = ""
    startingWithLastName: String = ""


@dataclass
class _User:
    id: String
    pictureHash: String
    pictureUrl: Url
    description: PersonDescription
    name: PersonDescription
    sort: String


@dataclass
class DateRange:
    start: DateTime
    end: DateTime


@dataclass
class SkoreWorkYear:
    id: int
    dateRange: DateRange


@dataclass
class Class_:
    identifier: String
    id: int
    platformId: int
    name: String
    type: String
    icon: String


@dataclass
class Period:
    id: int
    name: String
    icon: String
    skoreWorkYear: SkoreWorkYear
    isActive: bool
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class Component:
    id: int
    name: String
    abbreviation: String


Teacher = _User
Student = _User


@dataclass
class Course:
    id: int
    name: String
    graphic: CourseGraphic
    teachers: list[Teacher]
    skoreClassId: int
    parentCourseId: None | int
    skoreWorkYear: SkoreWorkYear
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class Feedback:
    text: String
    user: Teacher


@dataclass
class FeedbackFull:
    attachments: list[String]
    changedAt: DateTime
    createdAt: DateTime
    evaluationId: String
    id: String
    student: Student
    teacher: Teacher
    text: String


@dataclass
class Result:
    identifier: String
    type: Literal["normal"]
    name: String
    graphic: ResultGraphic
    date: DateTime

    gradebookOwner: Teacher
    component: Component
    courses: list[Course]
    period: Period
    feedback: list[Feedback]
    feedbacks: list[FeedbackFull]
    availabilityDate: DateTime
    isPublished: bool
    doesCount: bool


@dataclass
class ResultDetails:
    centralTendencies: list[String]
    teachers: list[Teacher]
    dateChanged: DateTime
    userChanged: Teacher
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class ResultWithDetails(Result):
    details: ResultDetails


@dataclass
class CourseCondensed:
    name: String
    teacher: String
    url: Url

    descr: String = Field(repr=False, default="")
    icon: String = Field(repr=False, default="")


@dataclass
class FutureTaskOneTask:
    label: String
    description: String
    icon: String
    warning: bool
    click_handle: String
    activityID: int
    dateID: String
    assignmentID: String
    endMomentTS: String | None
    startMomentID: String
    endMomentID: String
    lessonID: String
    type: String
    classID: String
    course: String
    date: Date
    hourID: String


@dataclass
class FutureTaskOneItem:
    tasks: list[FutureTaskOneTask]
    materials: list[String]


@dataclass
class FutureTaskOneCourse:
    lessonID: String
    hourID: String
    classID: String
    course_title: String
    items: FutureTaskOneItem


@dataclass
class FutureTaskOneDay:
    date: Date
    pretty_date: String
    courses: list[FutureTaskOneCourse]


@dataclass
class FutureTasks:
    """
    Class that interfaces the retrieval of any task that needs to be made in the near future.

    Example:
    -------
    >>> for day in FutureTasks().days:
    >>>     for course in day.courses:
    >>>         print("Course:", course.course_title)
    >>>         for task in course.items.tasks:
    >>>             print("Task:", task.description)
    Course: 2 - AAR1, Lotte Peeters
    Task: Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47

    """

    days: list[FutureTaskOneDay] = Field(default_factory=list)
    last_assignment_id: int = 0
    last_date: Date = Field(default_factory=date.today)

    def __post_init__(self):
        """I need to do this here because when I do it in Agenda, it'll not lazily load it. But in this way, I load it on construction."""
        json = session.json(
            "/Agenda/Futuretasks/getFuturetasks",
            method="post",
            data={
                "lastAssignmentID": 0,
                "lastDate": "",
                "filterType": "false",
                "filterID": "false",
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        self.days = []
        for d in json["days"]:
            self.days.append(FutureTaskOneDay(**d))

        self.last_assignment_id = json["last_assignment_id"]
        self.last_date = convert_to_date(json["last_date"])


@dataclass
class AgendaHour:
    hourID: String
    start: String
    end: String
    title: String


@dataclass
class AgendaLesson:
    momentID: String
    lessonID: String
    hourID: String
    date: Date
    subject: String | None
    course: String
    courseTitle: String
    classroom: String
    classroomTitle: String
    teacher: String
    teacherTitle: String
    klassen: String
    klassenTitle: String
    classIDs: String
    bothStartStatus: String
    assignmentEndStatus: String
    testDeadlineStatus: String
    noteStatus: String
    note: String | None
    date_listview: String
    hour: String
    activity: String
    activityID: String | None
    color: String
    hourValue: String
    components_hidden: object
    freedayIcon: String
    someSubjectsEmpty: String | None

    @property
    def hour_details(self) -> AgendaHour:
        from .agenda import SmartschoolHours

        return SmartschoolHours().search_by_hourId(self.hourID)


@dataclass
class AgendaMomentInfoAssignment:
    startAssignment: String
    start: String
    end: String
    type: String
    description: String
    atdescription: String
    freedeadline: String
    warning: String
    assignmentInfo: String
    assignmentDeadline: String


@dataclass
class AgendaMomentInfo:
    className: String
    subject: String
    materials: String | None
    momentID: String
    assignments: list[AgendaMomentInfoAssignment]


@dataclass
class StudentSupportLink:
    id: String
    name: String
    description: String
    icon: String
    link: Url
    cleanLink: String
    isVisible: bool


@dataclass
class ShortMessage:
    id: int
    fromImage: Url
    subject: String
    date: DateTime
    status: int
    attachment: int
    unread: bool
    label: bool
    deleted: bool
    allowreply: bool
    allowreplyenabled: bool
    hasreply: bool
    hasForward: bool
    realBox: String
    sendDate: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class FullMessage:
    id: int
    to: String | None
    subject: String
    date: DateTime
    body: String
    status: int
    attachment: int
    unread: bool
    label: bool
    receivers: list[String]
    ccreceivers: list[String]
    bccreceivers: list[String]
    senderPicture: String
    markedInLVS: None
    fromTeam: int
    totalNrOtherToReciviers: int
    totalnrOtherCcReceivers: int
    totalnrOtherBccReceivers: int
    canReply: bool
    hasReply: bool
    hasForward: bool
    sendDate: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class Attachment:
    fileID: int
    name: String
    mime: String
    size: String
    icon: String
    wopiAllowed: bool
    order: int

    def download(self) -> bytes:
        resp = session.get(f"/?module=Messages&file=download&fileID={self.fileID}&target=0")
        return base64.b64decode(resp.content)


@dataclass
class MessageChanged:
    id: int
    new: int = Field(validation_alias=AliasChoices("status", "label", "new"))


@dataclass
class MessageDeletionStatus:
    msgID: int
    boxType: String
    is_deleted: bool = Field(validation_alias=AliasChoices("status", "is_deleted"))
