from datetime import date
from typing import TYPE_CHECKING

from smartschool import FutureTasks, Smartschool

if TYPE_CHECKING:
    from smartschool.objects import FutureTaskOneDay


def test_future_tasks_normal_flow(session: Smartschool):
    """Note to self: for the "text": enclose the XHR with single quotes, and make it a raw string. No further processing needed."""
    x: list[FutureTaskOneDay] = list(FutureTasks(session))

    assert x[0].date == date(2023, 11, 16)
    assert x[0].courses[0].course_title == "2 - AAR1, Lotte Peeters"
    assert x[0].courses[0].items.materials == []
    assert x[0].courses[0].items.tasks[0].assignmentID == "549556"
    assert x[0].courses[0].items.tasks[0].description == "Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47"

    assert x[0].courses[0].items.tasks[0].endMomentTS is None


def test_future_tasks_moved_task(session: Smartschool):
    """'Toets Heelal' was moved from 2023-11-20 -> 2023-11-27."""
    x: list[FutureTaskOneDay] = list(FutureTasks(session))

    assert x[0].date == date(2023, 11, 27)
    assert x[0].courses[0].course_title == "1 - STEM1, Carla Verhoelst"
    assert x[0].courses[0].items.materials == []
    assert x[0].courses[0].items.tasks[0].assignmentID == "551612"
    assert x[0].courses[0].items.tasks[0].description == "Toets Heelal"

    assert x[0].courses[0].items.tasks[0].endMomentTS == "318_20231127"
