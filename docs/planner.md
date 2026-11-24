# Planner & Tasks

## Planned Elements

Everything in the Smartschool planner: assignments and to-dos by default, and on request the timetable, meetings and
lesson-free days.

```python
from datetime import date
from smartschool import Smartschool, PathCredentials, PlannedElements

session = Smartschool(PathCredentials())

# Default: the assignments and to-dos of today + 34 days
for element in PlannedElements(session):
    print(f"{element.name} ({element.planned_element_type})")
    print(f"  From: {element.period.date_time_from}")
    print(f"  To:   {element.period.date_time_to}")
    print(f"  Color: {element.color}")

    if element.courses:
        print(f"  Courses: {', '.join(c.name for c in element.courses)}")

    for user in element.organisers.users:
        print(f"  Organiser: {user.name.starting_with_first_name}")
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

`element_types` picks what is fetched, and `planned_element_type` says what each element is:
- `planned-assignments` - Assignments with courses, participants, and locations
- `planned-to-dos` - Personal to-do items (may not have courses/participants)
- `planned-lessons` - Lessons in the timetable; the name is the lesson's subject
- `planned-placeholders` - Timetable slots without content
- `planned-lesson-free-days` - Holidays and other days without lessons (no organisers)
- `planned-meetings` - Meetings

By default only assignments and to-dos are fetched. Pass `element_types` to choose: one type name, or several, e.g. the
timetable:

```python
lessons = PlannedElements(session, element_types="planned-lessons")
timetable = PlannedElements(session, element_types=("planned-lessons", "planned-placeholders"))
```

Nothing (`None` or an empty tuple) fetches everything the planner has:

```python
everything = PlannedElements(session, element_types=None)
```

Smartschool has no call that lists the types, and refuses a request naming one it does not know. Besides the ones above it
accepts `planned-activities`, `planned-generics`, `planned-lesson-clusters`, `planned-lesson-cluster-assignments`,
`planned-lesson-cluster-lessons`, `planned-lesson-cluster-moments`, `planned-partner-elements`, `planned-routines`,
`planned-school-activities` and `private-planned-elements`. Why the library keeps no list of its own is written down in
[this decision](decisions/planner-element-types.md).

### Includes

`includes` asks the planner to add related data to each element. The website asks for
`icon,courses,locations,upload-folders,labels`. Pass one name or several; by default nothing extra is asked for.

```python
elements = PlannedElements(session, includes=("icon", "courses", "locations", "upload-folders", "labels"))
```

### Pinned elements

`PinnedPlannedElements` gives the elements the user pinned in the planner, whatever their date. It takes `includes` too.

```python
from smartschool import PinnedPlannedElements

for element in PinnedPlannedElements(session):
    print(element.name)
```

### Locations

A location is either a room from the school's list or a place that was typed in:

```python
from smartschool import PlannedElementLocation, PlannedElementTextLocation

for location in element.locations:
    if isinstance(location, PlannedElementLocation):
        print(location.title)  # a room
    elif isinstance(location, PlannedElementTextLocation):
        print(location.text)  # typed in as free text
```

A kind of location the library does not know yet comes as a `PlannedElementUnknownLocation`, which only carries its `type`.

### Details of an Element

The list only holds the headers of each element. `PlannedElementDetails` fetches its detail view, which adds
the teacher's info for the pupils ("Info voor de leerling", as HTML), the attachments, the weblinks, the linked
curriculum goals and the reservations of a room or an item. `files()` gives the attachments as files to download.

Some fields only come with certain types: an assignment has `date_created` and `visibility` (from when the pupils
see it); a meeting has its description in `info`, plus `privacy`, `repeat_options`, `calendars`, `extra_organisers`,
`extra_participants` and `invite_statuses`; a school activity has its description in `info` as well.

A calendar of a meeting is a `PlannedElementUserCalendar` (a person's) or a `PlannedElementPlatformCalendar` (the
school's). A kind the library does not know yet comes as a `PlannedElementUnknownCalendar`, which only carries its `type`.

```python
from pathlib import Path
from smartschool import PlannedElementDetails, PlannedElements

for element in PlannedElements(session):
    details = PlannedElementDetails(session, element=element)
    detail = details.get()

    print(detail.public_info)
    for link in detail.weblinks:
        print(f"  {link.name}: {link.url}")
    for file in details.files():
        file.download_to_dir(Path("downloads") / element.id)  # a directory per element: names can repeat
```

## Future Tasks

Upcoming assignments and deadlines grouped by day and course, as the agenda holds them. A school that works with the
planner has none here: its assignments and to-dos are the [planned elements](#planned-elements) above.

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
