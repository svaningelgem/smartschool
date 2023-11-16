from smartschool import SmartschoolLessons


def test_agenda_lessons_normal_flow():
    sut = list(SmartschoolLessons())

    assert sut[0].momentID == "3728444"
    assert sut[1].momentID == "3728468"

    assert sut[0].hour_details.start == "08:25"
