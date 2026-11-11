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
- `planned-lessons` - Lessons in the timetable; the name is the lesson's subject
- `planned-placeholders` - Timetable slots without content
- `planned-lesson-free-days` - Holidays and other days without lessons (no organisers)
- `planned-meetings` - Meetings

By default only assignments and to-dos are fetched. Pass `element_types` to choose, e.g. the timetable:

```python
timetable = PlannedElements(session, element_types=("planned-lessons", "planned-placeholders"))
```

An empty tuple fetches everything the planner has:

```python
everything = PlannedElements(session, element_types=())
```

Smartschool has no call that lists the types, and refuses a request naming one it does not know. Besides the ones above it
accepts `planned-activities`, `planned-generics`, `planned-lesson-clusters`, `planned-lesson-cluster-assignments`,
`planned-lesson-cluster-lessons`, `planned-lesson-cluster-moments`, `planned-partner-elements`, `planned-routines`,
`planned-school-activities` and `private-planned-elements`.

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
