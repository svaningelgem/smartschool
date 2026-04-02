from __future__ import annotations

import re
from datetime import date, datetime
from functools import cached_property
from typing import Annotated, Literal

from pydantic import AliasChoices, BeforeValidator, ConfigDict, constr
from pydantic.alias_generators import to_camel
from pydantic.dataclasses import Field, dataclass

from .common import as_float, convert_to_date, convert_to_datetime

String = constr(strip_whitespace=True)
UUID = constr(pattern=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", flags=re.IGNORECASE))

Url = String
Date = Annotated[date, BeforeValidator(convert_to_date)]
DateTime = Annotated[datetime, BeforeValidator(convert_to_datetime)]

_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


@dataclass(config=_config)
class CourseGraphic:
    type: Literal["icon"]
    value: String


@dataclass(config=_config)
class PercentageGraphic:
    type: Literal["percentage"]
    color: Literal["green", "red", "olive", "yellow", "steel"]
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
    color: Literal["green", "red", "olive", "yellow", "steel"]
    value: String
    description: String


ResultGraphic = Annotated[PercentageGraphic | TextGraphic, Field(discriminator="type")]


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
class Course:
    id: int
    name: String
    graphic: CourseGraphic
    teachers: list[Teacher]
    skore_class_id: int
    parent_course_id: None | int
    skore_work_year: SkoreWorkYear
    class_: SchoolClass = Field(validation_alias=AliasChoices("class", "class_"))

    def __str__(self):
        ret = f"{self.name} (Teacher"
        if len(self.teachers) != 1:
            ret += "s"
        ret += f": {', '.join(t.name.starting_with_last_name for t in self.teachers)}"
        # ret += f", ID: {self.id}"
        return ret + ")"


@dataclass(config=_config)
class Feedback:
    text: String
    user: Teacher


@dataclass(config=_config)
class FeedbackFull:
    attachments: list[String]
    changed_at: DateTime
    created_at: DateTime
    evaluation_id: String
    id: String
    student: Student
    teacher: Teacher
    text: String


@dataclass(config=_config)
class Result:
    identifier: String
    type: Literal["normal"]
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
    url: Url = Field()

    id: int | None = Field(repr=False, default=None)
    platform_id: int | None = Field(repr=False, default=None)

    descr: String = Field(repr=False, default="")
    icon: String = Field(repr=False, default="")


@dataclass(config=_config)
class FutureTaskOneTask:
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
class AgendaLesson:
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
class AgendaMomentInfoAssignment:
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
class ShortMessage:
    id: int
    from_image: Url
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
    has_forward: bool
    real_box: String
    send_date: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass(config=_config)
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
class MessageSearchUser:
    user_id: Annotated[int, Field(validation_alias="userID")]
    value: String
    ss_id: Annotated[int, Field(validation_alias="ssID")]
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
class UserSeeProperties:
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
class UserCapabilities:
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
class PlannedElementLocation:
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
    to: String = Field(alias="to")


@dataclass(config=_config)
class PlannedElementAssignmentType:
    id: UUID
    name: String
    abbreviation: String
    is_visible: bool
    weight: int


@dataclass(config=_config)
class PlannedElement:
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
