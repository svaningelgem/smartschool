from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, time


def _email_text(hour_start: datetime | time, hour_end: datetime | time, course_name: str, task_label: str, description: str) -> str:
    return f"date: {hour_start:%Y-%m-%d}\ntime: {hour_start:%H:%M} -> {hour_end:%H:%M}\nles: {course_name}\n\n{task_label}:\n  {description}\n"


@lru_cache(1)
def _next_weekday() -> date | None:
    now = datetime.now()

    if now.hour in [12, 20] and now.isoweekday() == 3:  # Wednesday  # noqa: SIM114
        ...  # Ok
    elif now.hour in [17, 20] and now.isoweekday() != 3:  # !Wednesday
        ...  # Ok
    else:
        return None

    next_weekday = now + timedelta(days=1)
    while next_weekday.isoweekday() in [6, 7]:  # Saturday, Sunday
        next_weekday += timedelta(days=1)

    return next_weekday.date()
