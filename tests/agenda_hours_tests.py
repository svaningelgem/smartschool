import pytest
from smartschool import SmartschoolHours
from smartschool.objects import AgendaHour


def test_agenda_hours_normal_flow():
    sut = SmartschoolHours()

    assert sut.search_by_hourId("318") == AgendaHour(hourID="318", start="08:25", end="09:15", title="1")
    assert sut.search_by_hourId("320") == AgendaHour(hourID="320", start="09:15", end="10:05", title="2")

    with pytest.raises(ValueError, match="Couldn't find 123456789"):
        sut.search_by_hourId("123456789")
