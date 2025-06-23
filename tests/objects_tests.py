from datetime import date, datetime, time, timedelta, timezone

import pytest
import time_machine

from smartschool.objects import convert_to_date, convert_to_datetime


@time_machine.travel("2023-09-01 10:02:03+02:00", tick=False)
def test_convert_to_datetime() -> None:
    expected = datetime(2023, 9, 1, 10, 2, 3, tzinfo=timezone(timedelta(hours=2)))

    assert convert_to_datetime("2023-09-01T10:02:03+02:00") == expected
    assert convert_to_datetime(expected) == expected
    assert convert_to_datetime(None) == expected

    with pytest.raises(ValueError, match="No timezone information found in this date"):
        convert_to_datetime(expected.replace(tzinfo=None))

    assert convert_to_datetime("2023-09-01 10:02") == expected.replace(second=0, tzinfo=None)


@time_machine.travel("2023-09-01 10:02:03+02:00", tick=False)
def test_convert_to_date() -> None:
    expected = date(2023, 9, 1)

    assert convert_to_date("2023-09-01") == expected
    assert convert_to_date(None) == expected
    assert convert_to_date(expected) == expected
    assert convert_to_date(datetime.combine(expected, time.min)) == expected
