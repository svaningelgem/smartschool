from datetime import date, datetime, time, timedelta, timezone

import pytest
from smartschool.objects import convert_to_date, convert_to_datetime


def test_convert_to_datetime() -> None:
    expected = datetime(2023, 9, 1, 1, 2, 3, tzinfo=timezone(timedelta(hours=2)))

    assert convert_to_datetime("2023-09-01T01:02:03+02:00") == expected
    assert convert_to_datetime(expected) == expected

    with pytest.raises(ValueError, match="No timezone information found in this date"):
        convert_to_datetime(expected.replace(tzinfo=None))

    assert convert_to_datetime("2023-09-01 01:02") == expected.replace(second=0, tzinfo=None)


def test_convert_to_date() -> None:
    expected = date(2023, 9, 1)

    assert convert_to_date("2023-09-01") == expected
    assert convert_to_date(expected) == expected
    assert convert_to_date(datetime.combine(expected, time.min)) == expected
