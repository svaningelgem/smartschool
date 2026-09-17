import dataclasses

import pytest

from smartschool import AgendaPoster, Smartschool, SmartschoolLessons


def test_agenda_lessons_normal_flow(session: Smartschool):
    sut = list(SmartschoolLessons(session))

    assert sut[0].moment_id == "3728444"
    assert sut[1].moment_id == "3728468"

    assert sut[0].hour_details.start == "08:25"


def test_agenda_classes_are_dataclasses_with_their_own_init():
    """The generated `__init__` is what names the class in a wrong-call TypeError."""
    assert dataclasses.is_dataclass(SmartschoolLessons)
    assert SmartschoolLessons.__init__.__qualname__ == "SmartschoolLessons.__init__"
    assert AgendaPoster.__init__.__qualname__ == "AgendaPoster.__init__"
    assert AgendaPoster.__doc__ == "Caches the information on a weekly basis, and posts to the mentioned URL."

    with pytest.raises(TypeError, match=r"SmartschoolLessons.__init__\(\) missing 1 required positional argument: 'session'"):
        SmartschoolLessons()  # pylint: disable=no-value-for-parameter  # ty: ignore[missing-argument]  # that is the behaviour under test
