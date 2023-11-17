import logging

from .agenda import SmartschoolHours, SmartschoolLessons, SmartschoolMomentInfos
from .courses import Courses, TopNavCourses
from .credentials import EnvCredentials, PathCredentials
from .logger import setup_logger
from .messages import (
    AdjustMessageLabel,
    Attachments,
    BoxType,
    MarkMessageUnread,
    Message,
    MessageHeaders,
    MessageLabel,
    MessageMoveToArchive,
    MessageMoveToTrash,
    SortField,
    SortOrder,
)
from .objects import FutureTasks
from .periods import Periods
from .results import ResultDetail, Results
from .session import Smartschool
from .student_support import StudentSupportLinks

__all__ = [
    "PathCredentials",
    "EnvCredentials",
    "Smartschool",
    "logger",
    "Courses",
    "TopNavCourses",
    "Results",
    "Periods",
    "FutureTasks",
    "SortField",
    "SortOrder",
    "BoxType",
    "MessageHeaders",
    "StudentSupportLinks",
    "SmartschoolHours",
    "SmartschoolLessons",
    "SmartschoolMomentInfos",
    "Message",
    "Attachments",
    "MarkMessageUnread",
    "AdjustMessageLabel",
    "MessageMoveToArchive",
    "MessageMoveToTrash",
    "MessageLabel",
    "ResultDetail",
]

logger = setup_logger(logging.DEBUG)
