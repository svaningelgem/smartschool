from datetime import date, datetime, timedelta, time
from functools import lru_cache


def _email_text(hour_start: datetime | time, hour_end: datetime | time, course_name: str, task_label: str, description: str) -> str:
    return (
        f"date: {hour_start:%Y-%m-%d}\n"
        f"time: {hour_start:%H:%M} -> {hour_end:%H:%M}\n"
        f"les: {course_name}\n"
        "\n"
        f"{task_label}:\n"
        f"  {description}\n"
    )

@lru_cache(1)
def _next_weekday() -> date | None:
    now = datetime.now()

    if now.hour in [12, 20] and now.isoweekday() == 3:  # Wednesday
        ...  # Ok
    elif now.hour in [17, 20] and now.isoweekday() != 3:  # !Wednesday
        ...  # Ok
    else:
        return None

    next_weekday = now + timedelta(days=1)
    while next_weekday.isoweekday() in [6, 7]:  # Saturday, Sunday
        next_weekday += timedelta(days=1)

    return next_weekday.date()

