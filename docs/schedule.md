# Schedule & Agenda

## Daily Lessons

Retrieve the lesson schedule for a given date range (defaults to 20 days from the provided date).

A school that keeps its timetable in the planner exposes it through `PlannedElements`: see
[Planner & Tasks](planner.md#element-types).

```python
from datetime import date, timedelta
from smartschool import Smartschool, PathCredentials, SmartschoolLessons

session = Smartschool(PathCredentials())

# Tomorrow's schedule
tomorrow = date.today() + timedelta(days=1)

for lesson in SmartschoolLessons(session, timestamp_to_use=tomorrow):
    print(f"{lesson.hour}: {lesson.course_title}")
    print(f"  Room: {lesson.classroom_title}")
    print(f"  Teacher: {lesson.teacher_title}")
    if lesson.subject:
        print(f"  Subject: {lesson.subject}")
```

## Class Periods

Get the time definitions for each class hour.

```python
from smartschool import SmartschoolHours

hours = SmartschoolHours(session, timestamp_to_use=tomorrow)

for hour in hours:
    print(f"{hour.title}: {hour.start} - {hour.end}")

# Look up a specific hour
hour = hours.search_by_hour_id("123")
print(f"{hour.start} - {hour.end}")
```

## Lesson Details (Moment Info)

Get detailed information about a specific lesson, including assignments.

```python
from smartschool import SmartschoolMomentInfos

lesson = list(SmartschoolLessons(session, timestamp_to_use=tomorrow))[0]

for info in SmartschoolMomentInfos(session, moment_id=lesson.moment_id):
    print(f"Class: {info.class_name}")
    print(f"Subject: {info.subject}")
    if info.materials:
        print(f"Materials: {info.materials}")
    for assignment in info.assignments:
        print(f"  Assignment: {assignment.description} (due: {assignment.assignment_deadline})")
```
