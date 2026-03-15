from smartschool import Smartschool, SmartschoolLessons


def test_agenda_lessons_normal_flow(session: Smartschool):
    sut = list(SmartschoolLessons(session))

    assert sut[0].moment_id == "3728444"
    assert sut[1].moment_id == "3728468"

    assert sut[0].hour_details.start == "08:25"
