# Results & Reports

## Results

Retrieve grades and evaluations with teacher feedback.

```python
from smartschool import Smartschool, PathCredentials, Results

session = Smartschool(PathCredentials())

for result in Results(session):
    points = result.graphic.achieved_points
    total = result.graphic.total_points
    pct = result.graphic.percentage

    print(f"{result.name}: {points}/{total} ({pct:.1%})")
    print(f"  Date: {result.date}")
    print(f"  Teacher: {result.gradebookOwner.name.startingWithFirstName}")
    print(f"  Course: {', '.join(c.name for c in result.courses)}")
    print(f"  Period: {result.period.name}")

    # Teacher feedback
    for fb in result.feedback:
        print(f"  Feedback: {fb.user.name.startingWithFirstName}: {fb.text}")
```

Results are paginated (50 per page) and lazy-loaded as you iterate.

### Result Details

Each result can fetch additional details on demand:

```python
result = list(Results(session))[0]
details = result.details  # Lazy-loaded on first access

print(f"Teachers: {[t.name.startingWithFirstName for t in details.teachers]}")
print(f"Changed by: {details.userChanged.name.startingWithFirstName}")
print(f"Date changed: {details.dateChanged}")
```

## Reports

Download official academic report cards (PDF).

```python
from smartschool import Reports
from pathlib import Path

for report in Reports(session):
    print(f"{report.name} ({report.schoolyearLabel}) - {report.date}")

    # Download report
    pdf_bytes = report.download()
    Path(f"reports/{report.name}.pdf").write_bytes(pdf_bytes)
```

## Periods

Academic terms and grading periods.

```python
from smartschool import Periods

for period in Periods(session):
    print(f"{period.name} (active: {period.isActive})")
    print(f"  School year: {period.skoreWorkYear.dateRange.start} - {period.skoreWorkYear.dateRange.end}")
```
