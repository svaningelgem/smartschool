from datetime import date

from smartschool import FutureTasks


def test_future_tasks_normal_flow(requests_mock):
    """Note to self: for the "text": enclose the XHR with single quotes, and make it a raw string. No further processing needed."""
    requests_mock.get(
        "https://site/Agenda/Futuretasks/getFuturetasks",
        text=r'"{\"days\":[{\"date\":\"2023-11-16\",\"pretty_date\":\"Donderdag 16 november\",\"courses\":[{\"lessonID\":\"962\",\"hourID\":\"320\",\"classID\":\"3467\",\"course_title\":\"2 - AAR1, Lotte Peeters\",\"items\":{\"tasks\":[{\"label\":\"Toets\",\"description\":\"Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47\",\"icon\":\"book_red\",\"warning\":false,\"click_handle\":\"showForm\",\"activityID\":0,\"dateID\":\"\",\"assignmentID\":\"549556\",\"endMomentTS\":null,\"startMomentID\":\"3727494\",\"endMomentID\":\"3732340\",\"lessonID\":\"962\",\"type\":\"1\",\"classID\":\"3467\",\"course\":\"AAR1\",\"date\":\"2023-11-16\",\"hourID\":\"320\"}],\"materials\":[]}}]}],\"last_assignment_id\":-2,\"last_date\":\"2023-12-01\"}"',
    )

    x: FutureTasks = FutureTasks()

    assert x.days[0].date == date(2023, 11, 16)
    assert x.days[0].courses[0].course_title == "2 - AAR1, Lotte Peeters"
    assert x.days[0].courses[0].items.materials == []
    assert x.days[0].courses[0].items.tasks[0].assignmentID == "549556"
    assert x.days[0].courses[0].items.tasks[0].description == "Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47"
