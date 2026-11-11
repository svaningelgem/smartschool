# Planner & Tasks

## Planned Elements

Scheduled assignments, activities, and to-dos from the Smartschool planner.

```python
from datetime import date
from smartschool import Smartschool, PathCredentials, PlannedElements

session = Smartschool(PathCredentials())

# Default: today + 34 days
for element in PlannedElements(session):
    print(f"{element.name} ({element.plannedElementType})")
    print(f"  From: {element.period.dateTimeFrom}")
    print(f"  To:   {element.period.dateTimeTo}")
    print(f"  Color: {element.color}")

    if element.courses:
        print(f"  Courses: {', '.join(c.name for c in element.courses)}")

    if element.organisers:
        for user in element.organisers.users:
            print(f"  Organiser: {user.name.startingWithFirstName}")
```

### Custom Date Range

```python
elements = PlannedElements(
    session,
    from_date=date(2026, 3, 1),
    till_date=date(2026, 3, 31),
)

for element in elements:
    print(element.name)
```

### Element Types

The `plannedElementType` field indicates the type:
- `planned-assignments` - Assignments with courses, participants, and locations
- `planned-to-dos` - Personal to-do items (may not have courses/participants)
- `planned-placeholders` - Placeholder events

### Details of an Element

The list only holds the headers of each element. `PlannedElementDetails` fetches its detail view, which adds
the teacher's info for the pupils ("Info voor de leerling", as HTML), the attachments, the weblinks and the
linked curriculum goals.

```python
from pathlib import Path
from smartschool import PlannedElementDetails

for element in PlannedElements(session):
    details = PlannedElementDetails(session, element=element)
    detail = details.get()

    print(detail.public_info)
    for link in detail.weblinks:
        print(f"  {link.name}: {link.url}")
    for attachment in detail.attachments:
        Path(attachment.file_name).write_bytes(details.download(attachment))
```

## Future Tasks

Upcoming assignments and deadlines grouped by day and course.

```python
from smartschool import FutureTasks

for day in FutureTasks(session):
    print(f"\n{day.pretty_date} ({day.date})")
    for course in day.courses:
        print(f"  {course.course_title}:")
        for task in course.items.tasks:
            print(f"    - {task.label}: {task.description}")
            if task.warning:
                print(f"      [WARNING]")
```

## Assignment Types

List the available assignment types configured for the platform.

```python
from smartschool import ApplicableAssignmentTypes

for atype in ApplicableAssignmentTypes(session):
    print(f"{atype.name} ({atype.abbreviation}) - weight: {atype.weight}")
```
