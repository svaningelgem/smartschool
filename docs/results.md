# Results & Reports

## Results

Retrieve grades and evaluations with teacher feedback.

```python
from smartschool import Smartschool, PathCredentials, PercentageGraphic, Results

session = Smartschool(PathCredentials())

for result in Results(session):
    graphic = result.graphic
    if isinstance(graphic, PercentageGraphic):
        print(f"{result.name}: {graphic.achieved_points}/{graphic.total_points} ({graphic.percentage:.1%})")
    else:  # a text grade, or the icon of a project
        print(f"{result.name}: {graphic.value}")
    print(f"  Date: {result.date}")
    print(f"  Teacher: {result.gradebook_owner.name.starting_with_first_name}")
    print(f"  Course: {', '.join(c.name for c in result.courses)}")
    print(f"  Period: {result.period.name}")

    # Teacher feedback
    for fb in result.feedback:
        print(f"  Feedback: {fb.user.name.starting_with_first_name}: {fb.text}")
```

Results are paginated (50 per page) and lazy-loaded as you iterate.

`result.type` is `normal`, `project` or `project-with-rubrics`. A project is graded per goal: its own graphic is an icon,
and its details have no central tendencies.

### Result Details

Each result can fetch additional details on demand:

```python
result = list(Results(session))[0]
details = result.details  # Lazy-loaded on first access

if details:
    print(f"Teachers: {[t.name.starting_with_first_name for t in details.teachers]}")
    print(f"Changed by: {details.user_changed.name.starting_with_first_name}")
    print(f"Date changed: {details.date_changed}")
```

## Reports

Download official academic report cards (PDF).

```python
from smartschool import Reports
from pathlib import Path

for report in Reports(session):
    print(f"{report.name} ({report.schoolyear_label}) - {report.date}")

    # Download report
    target = Path("reports") / f"{report.name}.pdf"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(report.download())
```

## Periods

Academic terms and grading periods.

```python
from smartschool import Periods

for period in Periods(session):
    print(f"{period.name} (active: {period.is_active})")
    print(f"  School year: {period.skore_work_year.date_range.start} - {period.skore_work_year.date_range.end}")
```
