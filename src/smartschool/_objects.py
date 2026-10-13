from __future__ import annotations

import json
import sys
from datetime import date, datetime
from functools import cached_property
from typing import Annotated, Any, Literal

from logprise import logger
from pydantic import AliasChoices, BeforeValidator, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel
from pydantic.dataclasses import Field, dataclass

from ._common import as_float, convert_epoch_to_datetime, convert_to_date, convert_to_datetime, html_to_text

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:  # pragma: no cover
    from enum import Enum

    class StrEnum(str, Enum):
        __str__ = str.__str__


String = Annotated[str, StringConstraints(strip_whitespace=True)]
# `(?i)` inline flag = case-insensitive; pydantic-v2 StringConstraints over the legacy
# constr(pattern=...) form (which static analysers using v1 stubs misread).
UUID = Annotated[str, StringConstraints(pattern=r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]

Url = String
Date = Annotated[date, BeforeValidator(convert_to_date)]
DateTime = Annotated[datetime, BeforeValidator(convert_to_datetime)]
EpochDateTime = Annotated[datetime, BeforeValidator(convert_epoch_to_datetime)]
EpochDate = Annotated[date, BeforeValidator(lambda v: convert_epoch_to_datetime(v).date())]
# An empty XML leaf arrives as None.
OptionalString = Annotated[String, BeforeValidator(lambda v: v or "")]

_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class GraphicColor(StrEnum):
    """
    Colors emitted by Smartschool for ``PercentageGraphic`` / ``TextGraphic``.

    The members are Smartschool's colour palette (the ``--c-<name>--*`` CSS
    variables of the results app). An unknown colour is purely cosmetic, so it
    becomes an ad-hoc member with a warning instead of failing validation.
    """

    AQUA = "aqua"
    BEACH = "beach"
    BLACK = "black"
    BLUE = "blue"
    BROWN = "brown"
    CANDY = "candy"
    DOLPHIN = "dolphin"
    DYNAMITE = "dynamite"
    EMERALD = "emerald"
    GRASS = "grass"
    GREEN = "green"
    HAZELNUT = "hazelnut"
    HEAVEN = "heaven"
    JAZZ = "jazz"
    JEANS = "jeans"
    KIWI = "kiwi"
    LAVENDER = "lavender"
    LEMON = "lemon"
    MINT = "mint"
    MOSS = "moss"
    NIGHT = "night"
    OCEAN = "ocean"
    OLIVE = "olive"
    ORANGE = "orange"
    PINK = "pink"
    PURPLE = "purple"
    RED = "red"
    SAGE = "sage"
    SALMON = "salmon"
    SILVER = "silver"
    STEEL = "steel"
    TANGERINE = "tangerine"
    VIOLET = "violet"
    WATERMELON = "watermelon"
    YELLOW = "yellow"

    @classmethod
    def _missing_(cls, value: object) -> GraphicColor | None:
        if not isinstance(value, str):
            return None
        logger.warning("Unknown graphic color {!r}, please report it", value)
        member = str.__new__(cls, value)
        member._name_ = value.upper()
        member._value_ = value
        return member


class ResultType(StrEnum):
    """
    Discriminators emitted by Smartschool for ``Result.type``.

    Validation is strict: an unknown value raises so the missing member
    surfaces immediately and can be added here.
    """

    NORMAL = "normal"
    PROJECT_WITH_RUBRICS = "project-with-rubrics"


@dataclass(config=_config)
class CourseGraphic:
    type: Literal["icon", "image"]
    value: String


@dataclass(config=_config)
class PercentageGraphic:
    type: Literal["percentage"]
    color: GraphicColor
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


@dataclass(config=_config)
class TextGraphic:
    type: Literal["text"]
    color: GraphicColor
    value: String
    description: String


@dataclass(config=_config)
class IconGraphic:
    type: Literal["icon"]
    color: String | None = None
    value: String | None = None
    description: String | None = None


ResultGraphic = Annotated[PercentageGraphic | TextGraphic | IconGraphic, Field(discriminator="type")]


@dataclass(config=_config)
class PersonDescription:
    starting_with_first_name: String = ""
    starting_with_last_name: String = ""


@dataclass(config=_config)
class _User:
    id: String
    picture_hash: String
    picture_url: Url
    description: PersonDescription
    name: PersonDescription
    sort: String
    deleted: bool = False


@dataclass(config=_config)
class _Group:
    identifier: String
    id: String
    platform_id: int
    name: String
    type: String
    icon: String
    sort: String


@dataclass(config=_config)
class DateRange:
    start: DateTime
    end: DateTime


@dataclass(config=_config)
class SkoreWorkYear:
    id: int
    date_range: DateRange


@dataclass(config=_config)
class SchoolClass:
    identifier: String
    id: int
    platform_id: int
    name: String
    type: String
    icon: String


@dataclass(config=_config)
class Period:
    id: int
    name: String
    icon: String
    skore_work_year: SkoreWorkYear
    is_active: bool
    class_: SchoolClass = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass(config=_config)
class Component:
    id: int
    name: String
    abbreviation: String


@dataclass(config=_config)
class Teacher(_User): ...


@dataclass(config=_config)
class Student(_User): ...


@dataclass(config=_config)
class Course:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: int
    name: String
    graphic: CourseGraphic
    teachers: list[Teacher]
    skore_class_id: int
    parent_course_id: int | None
    skore_work_year: SkoreWorkYear
    class_: SchoolClass = Field(validation_alias=AliasChoices("class", "class_"))

    def __str__(self):
        ret = f"{self.name} (Teacher"
        if len(self.teachers) != 1:
            ret += "s"
        ret += f": {', '.join(t.name.starting_with_last_name for t in self.teachers)}"
        return ret + ")"


@dataclass(config=_config)
class Feedback:
    text: String
    user: Teacher


@dataclass(config=_config)
class FeedbackFull:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    attachments: list[String]
    changed_at: DateTime
    created_at: DateTime
    evaluation_id: String
    id: String
    student: Student
    teacher: Teacher
    text: String


@dataclass(config=_config)
class Result:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    identifier: String
    type: ResultType
    name: String
    graphic: ResultGraphic
    date: DateTime

    gradebook_owner: Teacher
    component: Component | None
    courses: list[Course]
    period: Period
    feedback: list[Feedback]
    feedbacks: list[FeedbackFull]
    availability_date: DateTime
    is_published: bool
    does_count: bool
    deleted: bool = False

    details: ResultDetails | None = None


@dataclass(config=_config)
class ResultDetails:
    central_tendencies: list[String]
    teachers: list[Teacher]
    date_changed: DateTime
    user_changed: Teacher
    class_: SchoolClass = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass(config=_config)
class CourseCondensed:
    name: String
    teacher: String
    url: Url

    id: int | None = Field(repr=False, default=None)
    platform_id: int | None = Field(repr=False, default=None)

    descr: String = Field(repr=False, default="")
    icon: String = Field(repr=False, default="")


@dataclass(config=_config)
class FutureTaskOneTask:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    label: String
    description: String
    icon: String
    warning: bool
    click_handle: String
    activity_id: Annotated[int, Field(validation_alias="activityID")]
    date_id: Annotated[String, Field(validation_alias="dateID")]
    assignment_id: Annotated[String, Field(validation_alias="assignmentID")]
    end_moment_ts: Annotated[String | None, Field(validation_alias="endMomentTS")]
    start_moment_id: Annotated[String, Field(validation_alias="startMomentID")]
    end_moment_id: Annotated[String, Field(validation_alias="endMomentID")]
    lesson_id: Annotated[String, Field(validation_alias="lessonID")]
    type: String
    class_id: Annotated[String, Field(validation_alias="classID")]
    course: String
    date: Date
    hour_id: Annotated[String, Field(validation_alias="hourID")]


@dataclass(config=_config)
class FutureTaskOneItem:
    tasks: list[FutureTaskOneTask]
    materials: list[String]


@dataclass(config=_config)
class FutureTaskOneCourse:
    lesson_id: Annotated[String, Field(validation_alias="lessonID")]
    hour_id: Annotated[String, Field(validation_alias="hourID")]
    class_id: Annotated[String, Field(validation_alias="classID")]
    course_title: String
    items: FutureTaskOneItem


@dataclass(config=_config)
class FutureTaskOneDay:
    date: Date
    pretty_date: String
    courses: list[FutureTaskOneCourse]


@dataclass(config=_config)
class AgendaHour:
    hour_id: Annotated[String, Field(validation_alias="hourID")]
    start: String
    end: String
    title: String


@dataclass(config=_config)
class AgendaLesson:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    moment_id: Annotated[String, Field(validation_alias="momentID")]
    lesson_id: Annotated[String, Field(validation_alias="lessonID")]
    hour_id: Annotated[String, Field(validation_alias="hourID")]
    date: Date
    subject: String | None
    course: String
    course_title: String
    classroom: String
    classroom_title: String
    teacher: String
    teacher_title: String
    klassen: String
    klassen_title: String
    class_ids: Annotated[String, Field(validation_alias="classIDs")]
    both_start_status: String
    assignment_end_status: String
    test_deadline_status: String
    note_status: String
    note: String | None
    date_listview: String
    hour: String
    activity: String
    activity_id: Annotated[String | None, Field(validation_alias="activityID")]
    color: String
    hour_value: String
    components_hidden: object
    freeday_icon: String
    some_subjects_empty: String | None


@dataclass(config=_config)
class AgendaMomentInfoAssignment:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    start_assignment: String
    start: String
    end: String
    type: String
    description: String
    atdescription: String
    freedeadline: String
    warning: String
    assignment_info: String
    assignment_deadline: String


@dataclass(config=_config)
class AgendaMomentInfo:
    class_name: String
    subject: String
    materials: String | None
    moment_id: Annotated[String, Field(validation_alias="momentID")]
    assignments: list[AgendaMomentInfoAssignment]


@dataclass(config=_config)
class StudentSupportLink:
    id: String
    name: String
    description: String
    icon: String
    link: Url
    clean_link: String
    is_visible: bool


@dataclass(config=_config)
class ShortMessage:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: int
    from_image: Url
    subject: String
    date: DateTime
    status: int
    attachment: int
    unread: bool
    deleted: bool
    allowreply: bool
    allowreplyenabled: bool
    hasreply: bool
    has_forward: bool
    real_box: String
    send_date: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))
    colored_flag: int = Field(default=0, validation_alias=AliasChoices("colored_flag", "label"))


@dataclass(config=_config)
class FullMessage:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: int
    to: String | None
    subject: String
    date: DateTime
    body: Annotated[String, BeforeValidator(lambda v: v or "")]  # a subject-only message has an empty (None) body
    status: int
    attachment: int
    unread: bool
    receivers: list[String]
    ccreceivers: list[String]
    bccreceivers: list[String]
    sender_picture: String
    marked_in_lvs: Annotated[None, Field(validation_alias="markedInLVS")]
    from_team: int
    total_nr_other_to_reciviers: int
    total_nr_other_cc_receivers: Annotated[int, Field(validation_alias="totalnrOtherCcReceivers")]
    total_nr_other_bcc_receivers: Annotated[int, Field(validation_alias="totalnrOtherBccReceivers")]
    can_reply: bool
    has_reply: bool
    has_forward: bool
    send_date: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))
    colored_flag: int = Field(default=0, validation_alias=AliasChoices("colored_flag", "label"))


@dataclass(config=_config)
class Attachment:
    file_id: Annotated[int, Field(validation_alias="fileID")]
    name: String
    mime: String
    size: String
    icon: String
    wopi_allowed: bool
    order: int


@dataclass(config=_config)
class MessageChanged:
    id: int
    new: int = Field(validation_alias=AliasChoices("status", "label", "new"))


@dataclass(config=_config)
class MessageDeletionStatus:
    msg_id: Annotated[int, Field(validation_alias="msgID")]
    box_type: String
    is_deleted: bool = Field(validation_alias=AliasChoices("status", "is_deleted"))


@dataclass(config=_config)
class MessageSearchUser:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    user_id: Annotated[int, Field(validation_alias="userID")]
    value: String
    ss_id: Annotated[int, Field(validation_alias="ssID")]
    # 0 = the account itself; 1, 2, ... = its co-accounts (parents). Co-accounts reuse the
    # account's user_id/ss_id and are told apart by this index.
    user_lt: Annotated[int, Field(validation_alias="userLT")] = 0
    coaccountname: String | None = None
    classname: String | None = None
    schoolname: String | None = None
    picture: Url | None = None


@dataclass(config=_config)
class MessageSearchGroup:
    group_id: Annotated[int, Field(validation_alias="groupID")]
    value: String
    ss_id: Annotated[int, Field(validation_alias="ssID")]
    icon: String | None = None
    description: String | None = None


@dataclass(config=_config)
class PlannedElementPeriod:
    date_time_from: datetime
    date_time_to: datetime
    whole_day: bool
    deadline: bool


@dataclass(config=_config)
class PlannedElementOrganisers:
    users: list[_User]


@dataclass(config=_config)
class GroupFilters:
    filters: list
    additional_users: list[_User]


@dataclass(config=_config)
class PlannedElementParticipants:
    groups: list[_Group]
    users: list[_User]
    group_filters: GroupFilters


@dataclass(config=_config)
class UserSeeProperties:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: bool
    platform_id: bool
    period: bool
    organisers: bool
    planned_element_type: bool
    capabilities: bool

    name: bool = False
    participants: bool = False
    is_participant: bool = False
    courses: bool = False
    locations: bool = False


@dataclass(config=_config)
class UserCapabilities:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    can_user_trash: bool
    can_user_restore_from_trash: bool
    can_user_delete: bool
    can_user_edit: bool
    can_user_replace: bool
    can_user_reschedule: bool
    can_user_change_user_color: bool
    can_user_see_properties: UserSeeProperties

    can_user_edit_presence: bool = False
    can_user_change_user_view_metadata: bool = False
    can_user_change_organisers: bool = False
    can_user_change_participants: bool = False
    can_user_change_participant_group_filters: bool = False
    can_user_change_courses: bool = False
    can_user_change_locations: bool = False
    can_user_create_video_call: bool = False
    can_user_see_video_call: bool = False
    can_user_manage_video_call: bool = False


@dataclass(config=_config)
class PlannedElementCourseCluster:
    id: int
    name: String


@dataclass(config=_config)
class PlannedElementCourse:
    id: UUID
    platform_id: int
    name: String
    schedule_codes: list[String]
    icon: String
    course_cluster: PlannedElementCourseCluster | None
    is_visible: bool


@dataclass(config=_config)
class PlannedElementLocation:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: UUID
    platform_id: int
    platform_name: String
    number: String
    title: String
    icon: String
    type: String
    selectable: bool


@dataclass(config=_config)
class PlannedElementJoinIds:
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))
    to: String = Field()


@dataclass(config=_config)
class PlannedElementAssignmentType:
    id: UUID
    name: String
    abbreviation: String
    is_visible: bool
    weight: int


@dataclass(config=_config)
class PlannedElement:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    id: UUID
    platform_id: int
    period: PlannedElementPeriod
    organisers: PlannedElementOrganisers
    planned_element_type: String
    capabilities: UserCapabilities
    sort: String
    unconfirmed: bool
    pinned: bool
    color: String
    join_ids: PlannedElementJoinIds

    name: String = ""
    participants: PlannedElementParticipants | None = None
    is_participant: bool = False
    courses: list[PlannedElementCourse] = Field(default_factory=list)
    locations: list[PlannedElementLocation] = Field(default_factory=list)
    assignment_type: PlannedElementAssignmentType | None = None
    resolved_status: String = ""
    online_session: String | None = None


@dataclass(config=_config)
class ApplicableAssignmentType:
    id: UUID
    platform_id: int
    name: String
    abbreviation: String
    is_visible: bool
    weight: float


@dataclass(config=_config)
class Report:
    id: int
    name: String
    icon: String
    date: DateTime
    download_url: Url
    class_: SchoolClass = Field(validation_alias=AliasChoices("class", "class_"))
    schoolyear_label: String = Field()


@dataclass(config=_config)
class StudentNote:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    """
    One line of the pupil's file in the pupil-follow-up system (LVS); `private` lines are meant for staff only.

    `pupil_id` is only the numeric middle part of the user id: Smartschool ids look like `<platform>_<id>_<role>`
    (e.g. `49_10880_2`), and the queries (`StudentNotes(pupil_id=...)`) take that full string.
    """

    item_id: Annotated[int, Field(validation_alias="itemID")]
    group_id: Annotated[int, Field(validation_alias="groupID")]
    pupil_id: Annotated[int, Field(validation_alias="pupilID")]
    cat_id: Annotated[int, Field(validation_alias="catID")]
    cat_name: OptionalString
    date: EpochDateTime
    author_reverse: OptionalString
    viewed: bool
    private: bool
    school_year: Annotated[OptionalString, Field(validation_alias="schoolyear")]
    study_direction: Annotated[OptionalString, Field(validation_alias="studierichting")]
    # Personal content: keep it out of logs and tracebacks.
    title: OptionalString = Field(default="", repr=False)
    author: OptionalString = Field(default="", repr=False)


@dataclass(config=_config)
class StudentAbsence:  # pylint: disable=too-many-instance-attributes  # mirrors the API payload
    """One absence code of the pupil. `part_of_day` is `VM` (morning) or `NM` (afternoon)."""

    absent_id: Annotated[int, Field(validation_alias="absentID")]
    code: OptionalString
    description: Annotated[OptionalString, Field(validation_alias="desc")]
    date: EpochDate
    info: OptionalString
    color: OptionalString
    part_of_day: Annotated[OptionalString, Field(validation_alias="pod")]
    school_year: Annotated[OptionalString, Field(validation_alias="schoolyear")]


@dataclass(config=_config)
class StudentNoteParam:
    """One parameter of a `StudentNote`. The `param_id` is school-specific: interpret a parameter by `param_type` and `title`."""

    param_id: Annotated[int, Field(validation_alias="paramID")]
    param_type: Annotated[int, Field(validation_alias="paramType")]
    title: OptionalString
    value: str | None = Field(default=None, repr=False)
    option_value: str | None = Field(default=None, validation_alias="optionvalue", repr=False)


# `StudentNoteParam.param_type` values that `StudentNoteDetail` interprets.
_PARAM_TEXT, _PARAM_MEASURE, _PARAM_ATTACHMENTS, _PARAM_DATE, _PARAM_INSTRUCTION = 2, 4, 6, 7, 8
_HANDLED_PARAM_TYPES = (_PARAM_TEXT, _PARAM_MEASURE, _PARAM_ATTACHMENTS, _PARAM_DATE, _PARAM_INSTRUCTION)


@dataclass(config=_config)
class StudentNoteDetail:
    """The content of one `StudentNote`, interpreted from its parameters. Which parameters exist differs per category."""

    item_id: int
    params: list[StudentNoteParam] = Field(default_factory=list, repr=False)  # personal content

    def _first(self, param_type: int) -> StudentNoteParam | None:
        return next((p for p in self.params if p.param_type == param_type), None)

    @property
    def text_html(self) -> str | None:
        """The free text of an announcement, as the HTML Smartschool sends it."""
        param = self._first(_PARAM_TEXT)
        return param.value if param else None

    @property
    def text(self) -> str | None:
        """The free text of an announcement without HTML."""
        html = self.text_html
        return html_to_text(html) if html else None

    @property
    def date(self) -> datetime | None:
        """The date parameter, for categories that have one (an announcement doesn't: use `StudentNote.date`)."""
        param = self._first(_PARAM_DATE)
        return convert_epoch_to_datetime(param.value) if param else None

    @property
    def measure(self) -> str | None:
        """The text of the disciplinary measure ("ordemaatregel") that was chosen, if any."""
        param = self._first(_PARAM_MEASURE)
        return param.option_value if param else None

    @property
    def attachments(self) -> list[Any]:
        """The attachments, as decoded from the JSON Smartschool sends; an empty list when there are none."""
        param = self._first(_PARAM_ATTACHMENTS)
        if not param or not param.option_value:
            return []
        try:
            decoded = json.loads(param.option_value)
        except json.JSONDecodeError:
            logger.warning("Cannot decode the attachments of note {}", self.item_id)
            return []
        return decoded if isinstance(decoded, list) else []

    @property
    def fields(self) -> dict[str, str]:
        """The remaining plain parameters by title (e.g. the teacher); the fixed instruction text is left out."""
        return {p.title: p.value or "" for p in self.params if p.param_type not in _HANDLED_PARAM_TYPES}
