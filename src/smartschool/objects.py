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
    last_date: Date | None = None

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
        self.last_date = convert_to_date(json["last_date"]) if json["last_date"] else None


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


# TODO:
# Planner --- future tasks
# https://paridaens.smartschool.be/planner/api/v1/planned-elements/user/49_10880_0?from=2025-05-01T00%3A00%3A00%2B02%3A00&to=2025-06-04T23%3A59%3A59%2B02%3A00&types=planned-assignments%2Cplanned-to-dos
# {
# 	"GET": {
# 		"scheme": "https",
# 		"host": "paridaens.smartschool.be",
# 		"filename": "/planner/api/v1/planned-elements/user/49_10880_0",
# 		"query": {
# 			"from": "2025-05-01T00:00:00+02:00",
# 			"to": "2025-06-04T23:59:59+02:00",
# 			"types": "planned-assignments,planned-to-dos"
# 		},
# 		"remote": {
# 			"Address": "193.56.132.11:443"
# 		}
# 	}
# }


# Returns:
# [{"id":"834149ab-3d17-4b83-8f7d-4efa5e09b387","platformId":49,"name":"Dag van de arbeid","icon":"flower_green","participants":{"groups":[{"identifier":"49_1","id":"49_1","platformId":49,"name":"Iedereen","type":"G","icon":"users_relation","sort":"Iedereen"}],"users":[]},"period":{"dateTimeFrom":"2025-05-01T08:00:00+02:00","dateTimeTo":"2025-05-01T08:30:00+02:00","wholeDay":true,"deadline":false},"plannedElementType":"planned-lesson-free-days","capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserReschedule":false,"canUserEditPresence":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"icon":true,"participants":true,"period":true,"plannedElementType":true,"capabilities":true}},"sort":"20250501000000_0_Iedereen_Dag van de arbeid","unconfirmed":false,"pinned":false,"color":"mint-200","joinIds":{"from":"bb7ad3b7-c2ea-5c10-b1fb-1a1a2cd6bee6","to":"218814cd-b2e9-5dae-86dc-66724be46120"}},{"id":"0af25169-413e-4d2f-b875-5135a10b4830","platformId":49,"name":"Trajet 5 : L\u0027\u00e9cologie \u0026 l\u0027environnement","period":{"dateTimeFrom":"2025-05-02T13:40:00+02:00","dateTimeTo":"2025-05-02T14:30:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2046_0","pictureHash":"initials_MH","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_MH\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Marie Herbosch","startingWithLastName":"Herbosch Marie"},"sort":"herbosch-marie","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"a66a103f-c96b-4627-8f85-ee67c926a1ab","platformId":49,"name":"Frans","scheduleCodes":["FR3","FR4","FR5","FrFL"],"icon":"flag_france","courseCluster":{"id":30,"name":"Frans"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502134000_4_4CHU_Trajet 5 : L\u0027\u00e9cologie \u0026 l\u0027environnement","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"eed03ff8-65cc-548e-bfac-a43e0001d7a3","to":"9e89f236-9d7d-5ebf-9d97-e047eacf4bf2"}},{"id":"1fc41337-f567-58f3-ba21-c3fcbc4c9409","platformId":49,"period":{"dateTimeFrom":"2025-05-05T09:15:00+02:00","dateTimeTo":"2025-05-05T10:05:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9891_0","pictureHash":"initials_JB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jef Binnemans","startingWithLastName":"Binnemans Jef"},"sort":"binnemans-jef","deleted":false}]},"participants":{"groups":[{"identifier":"49_4518","id":"49_4518","platformId":49,"name":"4AEC","type":"K","icon":"briefcase","sort":"4AEC"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"50242241-e4bc-42d3-84b6-b71103961169","platformId":49,"name":"Wiskunde","scheduleCodes":["WFL","WIS+","WIS3","WIS4","WIS5","WIS6","WIS8"],"icon":"math_symbol_collection_blue","courseCluster":{"id":69,"name":"Wiskunde"},"isVisible":true}],"locations":[{"id":"27d420ac-40e9-4aa3-92bc-df56a9ffb6eb","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"C.0.08","icon":"classroom_red","type":"mini-db-item","selectable":true}],"sort":"20250505091500_8_4AEC_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"e68075e2-38a5-5270-be5b-99f75f3d42c0","to":"f79eb1ed-f707-5236-9b21-fb89068ff20c"}},{"id":"218a7d16-c6a0-4f9e-95ba-4059e3ab7fe9","platformId":49,"name":"Media","period":{"dateTimeFrom":"2025-05-05T10:20:00+02:00","dateTimeTo":"2025-05-05T11:10:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9897_0","pictureHash":"initials_HG","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_HG\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Hanne Geets","startingWithLastName":"Geets Hanne"},"sort":"geets-hanne","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"e1c74a00-c401-4602-ae78-b3c9b33709e7","platformId":49,"name":"Nederlands","scheduleCodes":["NE4","NER1","NFL","NED TR1"],"icon":"zill_08_bubble_aqua","courseCluster":{"id":48,"name":"Nederlands"},"isVisible":true}],"locations":[{"id":"eaf974ed-11cb-415f-b05f-29babc22d1c6","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.07","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250505102000_4_4CHU_Media","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"8e86d87c-0bfe-5a5d-9b3c-ff4019b041fd","to":"c47403b3-6719-5f6e-a367-70094e8bc73f"}},{"id":"21fa06d2-8eee-4c8b-8433-5a5f579174cb","platformId":49,"name":"Keine Schule = Tag der Arbeit","period":{"dateTimeFrom":"2025-05-01T08:25:00+02:00","dateTimeTo":"2025-05-01T09:15:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2320_0","pictureHash":"initials_NM","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_NM\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Nathalie Moss","startingWithLastName":"Moss Nathalie"},"sort":"moss-nathalie","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"d9119e9f-b11c-4184-95b4-99b498262cbd","platformId":49,"name":"Duits","scheduleCodes":["DU1","DU2","DU3"],"icon":"flag_germany","courseCluster":{"id":22,"name":"Duits"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250501082500_4_4CNW_Keine Schule = Tag der Arbeit","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"237c511e-1bca-55cd-8aca-c71ea9d7a8e1","to":"0a684151-4ba4-5a58-abfe-187c51c6a39b"}},{"id":"2d3a8925-ac42-4f02-8d6b-a0fb59fc4646","platformId":49,"name":"theorie zuurtegraad + practicum STEM zuurtegraad oplossingen","period":{"dateTimeFrom":"2025-05-05T13:40:00+02:00","dateTimeTo":"2025-05-05T14:30:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_7243_0","pictureHash":"initials_LV","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_LV\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Liske Versieren","startingWithLastName":"Versieren Liske"},"sort":"versieren-liske","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"c3ed788d-2bb7-40c4-a99e-217f779d77c8","platformId":49,"name":"Chemie","scheduleCodes":["CH1","CH2","CH3"],"icon":"potion_yellow","courseCluster":{"id":20,"name":"Chemie"},"isVisible":true}],"locations":[{"id":"5ed7d7ba-85f2-4a56-b6c6-5362a34f429e","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.4.06","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250505134000_4_4CNW_theorie zuurtegraad + practicum STEM zuurtegraad oplossingen","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"1d483776-ff62-5df8-bfce-2d93760cfbbc","to":"0b3e5a7e-fee5-525e-93f1-25c8e7f45834"}},{"id":"2f62160d-415f-5867-b101-ca13fb82ae4c","platformId":49,"period":{"dateTimeFrom":"2025-05-01T10:20:00+02:00","dateTimeTo":"2025-05-01T11:10:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_1016_0","pictureHash":"initials_EW","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_EW\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Elke Wuytack","startingWithLastName":"Wuytack Elke"},"sort":"wuytack-elke","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"af4d1930-95db-4ef3-93ab-53abbcc32d9e","platformId":49,"name":"Fysica","scheduleCodes":["FY1","FY1+1","FY2","FY3"],"icon":"ringed_planet","courseCluster":{"id":31,"name":"Fysica"},"isVisible":true}],"locations":[{"id":"47e327fe-0f2a-436b-8ae7-73452580842d","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"D.1.10","icon":"classroom_lavender","type":"mini-db-item","selectable":true}],"sort":"20250501102000_8_4CNW_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"d24693c5-ce53-55cf-b343-e675db6557af","to":"a47ccae8-b256-5c2f-8310-87fa0273dc67"}},{"id":"2fae124f-6ceb-4f75-a8aa-daa1a177ce41","platformId":49,"name":"STEM: practicum: zuurtegraad van oplossingen uit het dagelijks leven bepalen","period":{"dateTimeFrom":"2025-05-05T14:45:00+02:00","dateTimeTo":"2025-05-05T15:35:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_7243_0","pictureHash":"initials_LV","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_LV\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Liske Versieren","startingWithLastName":"Versieren Liske"},"sort":"versieren-liske","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"ec19f8b8-03c1-45c2-a5b5-5b6db23212e0","platformId":49,"name":"STEM","scheduleCodes":["STEM1","STEM5"],"icon":"stem_course","courseCluster":{"id":119,"name":"STEM"},"isVisible":true}],"locations":[{"id":"5ed7d7ba-85f2-4a56-b6c6-5362a34f429e","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.4.06","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250505144500_4_4CNW_STEM: practicum: zuurtegraad van oplossingen uit het dagelijks leven bepalen","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"e4df50ff-93c7-5803-872e-d637121181ad","to":"3a4bef4a-8ea9-5cfa-b843-f8f9a2d6a149"}},{"id":"30ee0d97-1626-42c4-87c3-4c26147d6f01","platformId":49,"name":"partner in crime","assignmentType":{"id":"16062db8-c721-47de-9e69-9a8bcc2d4fb1","name":"Meebrengen","abbreviation":"ME","isVisible":true,"weight":1},"period":{"dateTimeFrom":"2025-05-01T12:00:00+02:00","dateTimeTo":"2025-05-01T12:50:00+02:00","wholeDay":false,"deadline":true},"organisers":{"users":[{"id":"49_2753_0","pictureHash":"initials_JA","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JA\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jan Anthonis","startingWithLastName":"Anthonis Jan"},"sort":"anthonis-jan","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserPin":false,"canUserResolve":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"assignmentType":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"plannedElementType":true,"resolvedStatus":true,"onlineSession":true,"courses":true,"locations":true}},"plannedElementType":"planned-assignments","resolvedStatus":"resolved","onlineSession":null,"courses":[{"id":"f850e023-428a-4186-a2cb-4056d46729f4","platformId":49,"name":"Engels","scheduleCodes":["E+","E2","E3"],"icon":"flag_great_britain","courseCluster":{"id":25,"name":"Engels"},"isVisible":true}],"locations":[{"id":"eaf974ed-11cb-415f-b05f-29babc22d1c6","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.07","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250501120000_5_4CHU_partner in crime","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"279108de-fbc2-5a90-937b-def4afd89ee4","to":"279108de-fbc2-5a90-937b-def4afd89ee4"}},{"id":"493466da-c549-5b9e-a711-81d57dd04b0f","platformId":49,"period":{"dateTimeFrom":"2025-05-02T11:10:00+02:00","dateTimeTo":"2025-05-02T12:00:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2039_0","pictureHash":"initials_TV","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_TV\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Thomas Verhaegen","startingWithLastName":"Verhaegen Thomas"},"sort":"verhaegen-thomas","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"cc349d99-9ff4-48d2-8c33-8285cd5b436b","platformId":49,"name":"Lichamelijke opvoeding","scheduleCodes":["LO2","ZW2"],"icon":"soccer_ball","courseCluster":{"id":44,"name":"Lichamelijke opvoeding"},"isVisible":true}],"locations":[{"id":"044fa59c-ae1d-499c-87cf-6406ccd3f1f5","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.0.03","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502111000_8_4CHU_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"0d601f30-a611-5213-be5c-c2168b0338a3","to":"5fcea176-07ca-5df2-ad59-700b94dab405"}},{"id":"6b98e3af-c394-41d7-a646-4c166c5cadcd","platformId":49,"name":"laptop mee","assignmentType":{"id":"16062db8-c721-47de-9e69-9a8bcc2d4fb1","name":"Meebrengen","abbreviation":"ME","isVisible":true,"weight":1},"period":{"dateTimeFrom":"2025-05-02T10:20:00+02:00","dateTimeTo":"2025-05-02T11:10:00+02:00","wholeDay":false,"deadline":true},"organisers":{"users":[{"id":"49_2753_0","pictureHash":"initials_JA","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JA\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jan Anthonis","startingWithLastName":"Anthonis Jan"},"sort":"anthonis-jan","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserPin":false,"canUserResolve":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"assignmentType":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"plannedElementType":true,"resolvedStatus":true,"onlineSession":true,"courses":true,"locations":true}},"plannedElementType":"planned-assignments","resolvedStatus":"resolved","onlineSession":null,"courses":[{"id":"f850e023-428a-4186-a2cb-4056d46729f4","platformId":49,"name":"Engels","scheduleCodes":["E+","E2","E3"],"icon":"flag_great_britain","courseCluster":{"id":25,"name":"Engels"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502102000_5_4CHU_laptop mee","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"84e0c130-a64d-53c1-9326-398cd7c35a66","to":"84e0c130-a64d-53c1-9326-398cd7c35a66"}},{"id":"7172e1f1-74a6-538b-858c-64c76725d0b0","platformId":49,"period":{"dateTimeFrom":"2025-05-01T14:45:00+02:00","dateTimeTo":"2025-05-01T15:35:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9891_0","pictureHash":"initials_JB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jef Binnemans","startingWithLastName":"Binnemans Jef"},"sort":"binnemans-jef","deleted":false}]},"participants":{"groups":[{"identifier":"49_4518","id":"49_4518","platformId":49,"name":"4AEC","type":"K","icon":"briefcase","sort":"4AEC"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"50242241-e4bc-42d3-84b6-b71103961169","platformId":49,"name":"Wiskunde","scheduleCodes":["WFL","WIS+","WIS3","WIS4","WIS5","WIS6","WIS8"],"icon":"math_symbol_collection_blue","courseCluster":{"id":69,"name":"Wiskunde"},"isVisible":true}],"locations":[{"id":"ab394d22-0a91-414c-962b-62e33c5f9c61","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.03","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250501144500_8_4AEC_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"5441028b-042f-5f1a-9bde-7af2f24a3bbb","to":"6dd96a97-a4d3-5910-a4bf-141c9ebb1870"}},{"id":"7537ddb6-ddc8-406a-9fec-1881eddb69ed","platformId":49,"name":"Repetitie thema 4: Classificatie","assignmentType":{"id":"03464bcc-1384-49b8-b301-56d13daf0bfd","name":"Repetitie","abbreviation":"RE","isVisible":true,"weight":1},"period":{"dateTimeFrom":"2025-05-05T12:00:00+02:00","dateTimeTo":"2025-05-05T12:50:00+02:00","wholeDay":false,"deadline":true},"organisers":{"users":[{"id":"49_10356_0","pictureHash":"initials_EB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_EB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Elke Barbier","startingWithLastName":"Barbier Elke"},"sort":"barbier-elke","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserPin":false,"canUserResolve":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"assignmentType":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"plannedElementType":true,"resolvedStatus":true,"onlineSession":true,"courses":true,"locations":true}},"plannedElementType":"planned-assignments","resolvedStatus":"unresolved","onlineSession":null,"courses":[{"id":"f2d5894f-872d-4e94-9eaa-42cd98f83c2a","platformId":49,"name":"Biologie","scheduleCodes":["BIO1","BIO2","BIO3"],"icon":"flower_red","courseCluster":{"id":19,"name":"Biologie"},"isVisible":true}],"locations":[{"id":"05c6452c-a9a2-46f5-a1db-cf9c169abbaa","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"D.2.05","icon":"classroom_lavender","type":"mini-db-item","selectable":true}],"sort":"20250505120000_5_4CNW_Repetitie thema 4: Classificatie","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"3c691524-eae2-5e1d-8f8a-93487c3cf699","to":"3c691524-eae2-5e1d-8f8a-93487c3cf699"}},{"id":"82f6d7aa-fa5f-5311-904d-3703dba423ea","platformId":49,"period":{"dateTimeFrom":"2025-05-05T08:25:00+02:00","dateTimeTo":"2025-05-05T09:15:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9891_0","pictureHash":"initials_JB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jef Binnemans","startingWithLastName":"Binnemans Jef"},"sort":"binnemans-jef","deleted":false}]},"participants":{"groups":[{"identifier":"49_4518","id":"49_4518","platformId":49,"name":"4AEC","type":"K","icon":"briefcase","sort":"4AEC"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"50242241-e4bc-42d3-84b6-b71103961169","platformId":49,"name":"Wiskunde","scheduleCodes":["WFL","WIS+","WIS3","WIS4","WIS5","WIS6","WIS8"],"icon":"math_symbol_collection_blue","courseCluster":{"id":69,"name":"Wiskunde"},"isVisible":true}],"locations":[{"id":"27d420ac-40e9-4aa3-92bc-df56a9ffb6eb","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"C.0.08","icon":"classroom_red","type":"mini-db-item","selectable":true}],"sort":"20250505082500_8_4AEC_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"6e5d6eeb-11e4-51c5-be5b-ee12957ef7c2","to":"e68075e2-38a5-5270-be5b-99f75f3d42c0"}},{"id":"84d3396b-5705-4396-bd57-fefcd1b124fd","platformId":49,"name":"Dag van de Arbeid : geen les","period":{"dateTimeFrom":"2025-05-01T09:15:00+02:00","dateTimeTo":"2025-05-01T10:05:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2046_0","pictureHash":"initials_MH","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_MH\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Marie Herbosch","startingWithLastName":"Herbosch Marie"},"sort":"herbosch-marie","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"a66a103f-c96b-4627-8f85-ee67c926a1ab","platformId":49,"name":"Frans","scheduleCodes":["FR3","FR4","FR5","FrFL"],"icon":"flag_france","courseCluster":{"id":30,"name":"Frans"},"isVisible":true}],"locations":[{"id":"13e1e06d-9e63-4b83-a9ba-2d69c278d42f","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.2.07","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250501091500_4_4CHU_Dag van de Arbeid : geen les","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"0a684151-4ba4-5a58-abfe-187c51c6a39b","to":"f7da334c-a12a-5ba7-aaf4-c22f7fb1bfd7"}},{"id":"8e65dff3-466d-4d71-9b5f-67627395af29","platformId":49,"period":{"dateTimeFrom":"2025-05-01T12:00:00+02:00","dateTimeTo":"2025-05-01T12:50:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2753_0","pictureHash":"initials_JA","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JA\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jan Anthonis","startingWithLastName":"Anthonis Jan"},"sort":"anthonis-jan","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"f850e023-428a-4186-a2cb-4056d46729f4","platformId":49,"name":"Engels","scheduleCodes":["E+","E2","E3"],"icon":"flag_great_britain","courseCluster":{"id":25,"name":"Engels"},"isVisible":true}],"locations":[{"id":"eaf974ed-11cb-415f-b05f-29babc22d1c6","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.07","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250501120000_8_4CHU_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"a3ee5157-2517-5be0-9616-87a6f0f3a5b7","to":"9d1f494a-278c-5e8a-ba06-9b5079dc3643"}},{"id":"8f939a88-6e4a-5b79-844e-378c7f64952f","platformId":49,"period":{"dateTimeFrom":"2025-05-01T11:10:00+02:00","dateTimeTo":"2025-05-01T12:00:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_8933_0","pictureHash":"initials_IW","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_IW\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Iris Wittevrongel","startingWithLastName":"Wittevrongel Iris"},"sort":"wittevrongel-iris","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"4637d7f7-52de-48b7-ab91-3c6fd4a0abf9","platformId":49,"name":"Godsdienst","scheduleCodes":["GO2"],"icon":"angel","courseCluster":{"id":43,"name":"Levensbeschouwing (Godsdienst of Niet-confessionele zedenleer)"},"isVisible":true}],"locations":[{"id":"1bd970d8-885a-4aa6-b762-ed34db7bb4b2","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"C.3.06","icon":"classroom_red","type":"mini-db-item","selectable":true}],"sort":"20250501111000_8_4CHU_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"a47ccae8-b256-5c2f-8310-87fa0273dc67","to":"a3ee5157-2517-5be0-9616-87a6f0f3a5b7"}},{"id":"a99319c9-b0e3-46b8-b4d4-29ac6d09b82b","platformId":49,"name":"Ionuitwisselingsreacties: gasontwikkeling + neutralisatiereacties","period":{"dateTimeFrom":"2025-05-02T09:15:00+02:00","dateTimeTo":"2025-05-02T10:05:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_7243_0","pictureHash":"initials_LV","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_LV\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Liske Versieren","startingWithLastName":"Versieren Liske"},"sort":"versieren-liske","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"c3ed788d-2bb7-40c4-a99e-217f779d77c8","platformId":49,"name":"Chemie","scheduleCodes":["CH1","CH2","CH3"],"icon":"potion_yellow","courseCluster":{"id":20,"name":"Chemie"},"isVisible":true}],"locations":[{"id":"5ed7d7ba-85f2-4a56-b6c6-5362a34f429e","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.4.06","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250502091500_4_4CNW_Ionuitwisselingsreacties: gasontwikkeling + neutralisatiereacties","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"be24f9fd-cb69-57b9-8c39-db5e20a0d082","to":"c9e247a9-472b-598a-95fd-6405fbb7ee10"}},{"id":"ab571b12-5f2e-5947-9892-7678058cecdc","platformId":49,"period":{"dateTimeFrom":"2025-05-02T08:25:00+02:00","dateTimeTo":"2025-05-02T09:15:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9891_0","pictureHash":"initials_JB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jef Binnemans","startingWithLastName":"Binnemans Jef"},"sort":"binnemans-jef","deleted":false}]},"participants":{"groups":[{"identifier":"49_4518","id":"49_4518","platformId":49,"name":"4AEC","type":"K","icon":"briefcase","sort":"4AEC"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"50242241-e4bc-42d3-84b6-b71103961169","platformId":49,"name":"Wiskunde","scheduleCodes":["WFL","WIS+","WIS3","WIS4","WIS5","WIS6","WIS8"],"icon":"math_symbol_collection_blue","courseCluster":{"id":69,"name":"Wiskunde"},"isVisible":true}],"locations":[{"id":"73dea8c3-52ee-4a17-8038-0eae51cb3bc0","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.04","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502082500_8_4AEC_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"b4368085-ddf7-5b8a-9aa3-234bb9a148ff","to":"be24f9fd-cb69-57b9-8c39-db5e20a0d082"}},{"id":"b6e3b5b8-517d-47bf-9903-b9bb7e390ee2","platformId":49,"name":"Unit 4, Part I. Conclusion. Second version of partner in crime.","period":{"dateTimeFrom":"2025-05-02T10:20:00+02:00","dateTimeTo":"2025-05-02T11:10:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2753_0","pictureHash":"initials_JA","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JA\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jan Anthonis","startingWithLastName":"Anthonis Jan"},"sort":"anthonis-jan","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"f850e023-428a-4186-a2cb-4056d46729f4","platformId":49,"name":"Engels","scheduleCodes":["E+","E2","E3"],"icon":"flag_great_britain","courseCluster":{"id":25,"name":"Engels"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502102000_4_4CHU_Unit 4, Part I. Conclusion. Second version of partner in crime.","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"f31945c9-731a-57d3-a859-eaaebfdc10b1","to":"0d601f30-a611-5213-be5c-c2168b0338a3"}},{"id":"baf4b7d8-3007-404e-bff3-f4d382c58fc2","platformId":49,"name":"H11. De Nederlanden en de Tachtigjarige Oorlog","period":{"dateTimeFrom":"2025-05-02T12:00:00+02:00","dateTimeTo":"2025-05-02T12:50:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9801_0","pictureHash":"initials_TB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_TB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Tiffany Bousard","startingWithLastName":"Bousard Tiffany"},"sort":"bousard-tiffany","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"44315978-1572-413e-bea8-6411d75e89f8","platformId":49,"name":"Geschiedenis","scheduleCodes":["GE1","GE2"],"icon":"fortress","courseCluster":{"id":33,"name":"Geschiedenis"},"isVisible":true}],"locations":[{"id":"2ebcfbde-d5db-4f2e-9d09-8607885142bd","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"C.2.08","icon":"classroom_red","type":"mini-db-item","selectable":true}],"sort":"20250502120000_4_4CHU_H11. De Nederlanden en de Tachtigjarige Oorlog","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"5fcea176-07ca-5df2-ad59-700b94dab405","to":"eb4266aa-8829-58a3-9be9-a13d4efc8fd6"}},{"id":"bcd65d00-e8be-48d2-be32-815da200740d","platformId":49,"name":"Kapitel 4 - Lektion 2","period":{"dateTimeFrom":"2025-05-02T14:45:00+02:00","dateTimeTo":"2025-05-02T15:35:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2320_0","pictureHash":"initials_NM","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_NM\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Nathalie Moss","startingWithLastName":"Moss Nathalie"},"sort":"moss-nathalie","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"d9119e9f-b11c-4184-95b4-99b498262cbd","platformId":49,"name":"Duits","scheduleCodes":["DU1","DU2","DU3"],"icon":"flag_germany","courseCluster":{"id":22,"name":"Duits"},"isVisible":true}],"locations":[{"id":"13e1e06d-9e63-4b83-a9ba-2d69c278d42f","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.2.07","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250502144500_4_4CNW_Kapitel 4 - Lektion 2","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"ca4dc132-3583-59d0-8c30-3e6830419fe1","to":"19298424-0b3e-5437-b202-6505d4290dab"}},{"id":"bcfda86d-08bd-4325-af58-862ee4a03938","platformId":49,"name":"laptop","assignmentType":{"id":"12657aa0-3b29-4977-925b-e2a0f133f2ba","name":"-","abbreviation":"-","isVisible":true,"weight":1},"period":{"dateTimeFrom":"2025-05-02T10:20:00+02:00","dateTimeTo":"2025-05-02T11:10:00+02:00","wholeDay":false,"deadline":true},"organisers":{"users":[{"id":"49_2753_0","pictureHash":"initials_JA","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_JA\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Jan Anthonis","startingWithLastName":"Anthonis Jan"},"sort":"anthonis-jan","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserPin":false,"canUserResolve":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"assignmentType":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"plannedElementType":true,"resolvedStatus":true,"onlineSession":true,"courses":true,"locations":true}},"plannedElementType":"planned-assignments","resolvedStatus":"resolved","onlineSession":null,"courses":[{"id":"f850e023-428a-4186-a2cb-4056d46729f4","platformId":49,"name":"Engels","scheduleCodes":["E+","E2","E3"],"icon":"flag_great_britain","courseCluster":{"id":25,"name":"Engels"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250502102000_5_4CHU_laptop","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"045a415a-0f1a-5bf6-ab84-b7fed9bcc8a4","to":"045a415a-0f1a-5bf6-ab84-b7fed9bcc8a4"}},{"id":"d159871e-136b-4204-9697-a539eab1e095","platformId":49,"name":"Repetitie thema 4: Classificatie","period":{"dateTimeFrom":"2025-05-05T12:00:00+02:00","dateTimeTo":"2025-05-05T12:50:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_10356_0","pictureHash":"initials_EB","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_EB\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Elke Barbier","startingWithLastName":"Barbier Elke"},"sort":"barbier-elke","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"f2d5894f-872d-4e94-9eaa-42cd98f83c2a","platformId":49,"name":"Biologie","scheduleCodes":["BIO1","BIO2","BIO3"],"icon":"flower_red","courseCluster":{"id":19,"name":"Biologie"},"isVisible":true}],"locations":[{"id":"05c6452c-a9a2-46f5-a1db-cf9c169abbaa","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"D.2.05","icon":"classroom_lavender","type":"mini-db-item","selectable":true}],"sort":"20250505120000_4_4CNW_Repetitie thema 4: Classificatie","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"b8453482-1743-5d57-b702-4f04e772bf58","to":"2baeb560-a73b-5669-aba9-3cda4d5f4451"}},{"id":"d8a96c2f-494f-52e2-b844-55e3359902ac","platformId":49,"period":{"dateTimeFrom":"2025-05-05T11:10:00+02:00","dateTimeTo":"2025-05-05T12:00:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2046_0","pictureHash":"initials_MH","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_MH\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Marie Herbosch","startingWithLastName":"Herbosch Marie"},"sort":"herbosch-marie","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"plannedElementType":"planned-placeholders","isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeOrganisers":false,"canUserChangeParticipants":false,"canUserChangeParticipantGroupFilters":false,"canUserChangeCourses":false,"canUserChangeLocations":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserSeeProperties":{"id":true,"platformId":true,"period":true,"organisers":true,"participants":true,"plannedElementType":true,"isParticipant":true,"capabilities":true,"courses":true,"locations":true}},"courses":[{"id":"a66a103f-c96b-4627-8f85-ee67c926a1ab","platformId":49,"name":"Frans","scheduleCodes":["FR3","FR4","FR5","FrFL"],"icon":"flag_france","courseCluster":{"id":30,"name":"Frans"},"isVisible":true}],"locations":[{"id":"cb15a596-f526-4df1-bb6f-9b7639984172","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"G.2.06","icon":"classroom_green","type":"mini-db-item","selectable":true}],"sort":"20250505111000_8_4CHU_","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"c47403b3-6719-5f6e-a367-70094e8bc73f","to":"b8453482-1743-5d57-b702-4f04e772bf58"}},{"id":"e954db30-02d5-443d-9db0-f492d056e9f3","platformId":49,"name":"Kapitel 4 und 5 mitbringen","assignmentType":{"id":"16062db8-c721-47de-9e69-9a8bcc2d4fb1","name":"Meebrengen","abbreviation":"ME","isVisible":true,"weight":1},"period":{"dateTimeFrom":"2025-05-02T14:45:00+02:00","dateTimeTo":"2025-05-02T15:35:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_2320_0","pictureHash":"initials_NM","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_NM\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Nathalie Moss","startingWithLastName":"Moss Nathalie"},"sort":"moss-nathalie","deleted":false}]},"participants":{"groups":[{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"},{"identifier":"49_6638","id":"49_6638","platformId":49,"name":"4DNW","type":"K","icon":"briefcase","sort":"4DNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserPin":false,"canUserResolve":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"assignmentType":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"plannedElementType":true,"resolvedStatus":true,"onlineSession":true,"courses":true,"locations":true}},"plannedElementType":"planned-assignments","resolvedStatus":"unresolved","onlineSession":null,"courses":[{"id":"d9119e9f-b11c-4184-95b4-99b498262cbd","platformId":49,"name":"Duits","scheduleCodes":["DU1","DU2","DU3"],"icon":"flag_germany","courseCluster":{"id":22,"name":"Duits"},"isVisible":true}],"locations":[{"id":"13e1e06d-9e63-4b83-a9ba-2d69c278d42f","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.2.07","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250502144500_5_4CNW_Kapitel 4 und 5 mitbringen","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"34ee21df-4c52-541e-bc9e-453fe4007e64","to":"3ff86c99-65f4-58a3-ba41-93e2d4149942"}},{"id":"e9c4f14b-14dd-4123-b9c2-dc14ef597c83","platformId":49,"name":"Dag van de arbeid","period":{"dateTimeFrom":"2025-05-01T13:40:00+02:00","dateTimeTo":"2025-05-01T14:30:00+02:00","wholeDay":false,"deadline":false},"organisers":{"users":[{"id":"49_9897_0","pictureHash":"initials_HG","pictureUrl":"https:\/\/userpicture20.smartschool.be\/User\/Userimage\/hashimage\/hash\/initials_HG\/plain\/1\/res\/128","description":{"startingWithFirstName":"","startingWithLastName":""},"name":{"startingWithFirstName":"Hanne Geets","startingWithLastName":"Geets Hanne"},"sort":"geets-hanne","deleted":false}]},"participants":{"groups":[{"identifier":"49_4522","id":"49_4522","platformId":49,"name":"4CHU","type":"K","icon":"briefcase","sort":"4CHU"},{"identifier":"49_6634","id":"49_6634","platformId":49,"name":"4CNW","type":"K","icon":"briefcase","sort":"4CNW"}],"users":[],"groupFilters":{"filters":[],"additionalUsers":[]}},"isParticipant":true,"capabilities":{"canUserTrash":false,"canUserRestoreFromTrash":false,"canUserDelete":false,"canUserEdit":false,"canUserReplace":false,"canUserEditPresence":false,"canUserReschedule":false,"canUserChangeUserColor":true,"canUserChangeUserViewMetadata":true,"canUserCreateVideoCall":false,"canUserSeeVideoCall":true,"canUserManageVideoCall":false,"canUserSeeProperties":{"id":true,"platformId":true,"name":true,"period":true,"organisers":true,"participants":true,"isParticipant":true,"capabilities":true,"onlineSession":true,"plannedElementType":true,"courses":true,"locations":true}},"onlineSession":null,"plannedElementType":"planned-lessons","courses":[{"id":"e1c74a00-c401-4602-ae78-b3c9b33709e7","platformId":49,"name":"Nederlands","scheduleCodes":["NE4","NER1","NFL","NED TR1"],"icon":"zill_08_bubble_aqua","courseCluster":{"id":48,"name":"Nederlands"},"isVisible":true}],"locations":[{"id":"9eefa7b0-e7d5-40e1-9a89-224ec6757ce3","platformId":49,"platformName":"Paridaensinstituut","number":"","title":"E.3.05","icon":"classroom_purple","type":"mini-db-item","selectable":true}],"sort":"20250501134000_4_4CHU_Dag van de arbeid","unconfirmed":false,"pinned":false,"color":"aqua-200","joinIds":{"from":"b3b3cee9-197c-5112-adc9-0ec449d180aa","to":"ef5be38f-93bc-5654-936b-7e5e02bb6c67"}}]


# CourseConfig (vakken-dropdown):
# {
# 	"POST": {
# 		"scheme": "https",
# 		"host": "paridaens.smartschool.be",
# 		"filename": "/Topnav/getCourseConfig",
# 		"remote": {
# 			"Address": "193.56.132.11:443"
# 		}
# 	}
# }

# {
# 	"GET": {
# 		"scheme": "https",
# 		"host": "paridaens.smartschool.be",
# 		"filename": "/lesson-content/api/v1/assignments/applicable-assignment-types",
# 		"remote": {
# 			"Address": "193.56.132.11:443"
# 		}
# 	}
# }
