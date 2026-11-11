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

### Project Results

The marks of a project are in its details: one per curriculum goal, taken from the scale that comes with it.

```python
from smartschool import ResultType

for result in Results(session):
    if result.type == ResultType.PROJECT and result.details:
        print(result.name)
        for project_goal in result.details.project_goals:
            mark = project_goal.graphic
            print(f"  {project_goal.goal.leerplan_key}: {mark.value} ({mark.description})")
        print(f"  Scale: {[scale.value for scale in result.details.scales]}")
```

A goal is identified by `goal_id`, `leerplan_id` and `leerplan_key`; its text is not part of the result.

### Result Details

Each result can fetch additional details on demand:

```python
result = list(Results(session))[0]
details = result.details  # Lazy-loaded on first access

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
    pdf_bytes = report.download()
    Path(f"reports/{report.name}.pdf").write_bytes(pdf_bytes)
```

## Periods

Academic terms and grading periods.

```python
from smartschool import Periods

for period in Periods(session):
    print(f"{period.name} (active: {period.is_active})")
    print(f"  School year: {period.skore_work_year.date_range.start} - {period.skore_work_year.date_range.end}")
```
