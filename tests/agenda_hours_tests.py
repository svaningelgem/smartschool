import pytest

from smartschool import Smartschool, SmartschoolHours
from smartschool.objects import AgendaHour


def test_agenda_hours_normal_flow(session: Smartschool):
    sut = SmartschoolHours(session)

    assert sut.search_by_hour_id("318") == AgendaHour(hour_id="318", start="08:25", end="09:15", title="1")
    assert sut.search_by_hour_id("320") == AgendaHour(hour_id="320", start="09:15", end="10:05", title="2")

    with pytest.raises(ValueError, match="Couldn't find 123456789"):
        sut.search_by_hour_id("123456789")
