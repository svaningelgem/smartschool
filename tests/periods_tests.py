from datetime import datetime, timedelta, timezone

from smartschool import Periods, Smartschool


def test_periods_happy_flow(session: Smartschool):
    sut = list(Periods(session))

    assert len(sut) == 2

    assert sut[0].name == "1 september - 24 oktober"
    assert sut[0].class_.name == "3ENW"
    assert not sut[0].isActive

    assert sut[1].name == "25 oktober - 19 december"
    assert sut[1].skoreWorkYear.dateRange.start == datetime(2023, 9, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert sut[1].isActive
