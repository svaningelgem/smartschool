# Smartschool parser

[![codecov](https://codecov.io/gh/svaningelgem/smartschool/graph/badge.svg?token=U0A3H3K4L0)](https://codecov.io/gh/svaningelgem/smartschool)

Unofficial interpreter to interface against smartschool's website.

## How to use?

Copy the `credentials.yml.example` file to `credentials.yml` and adjust the contents with the username/password and school uri.

```python
from smartschool import SmartSchool, PathCredentials, Courses

SmartSchool.start(PathCredentials())
for course in Courses():
    print(course.name)
```

## Implemented:

- [AgendaLessons](src/smartschool/agenda.py)
- [AgendaHours](src/smartschool/agenda.py)
- [AgendaMomentInfos](src/smartschool/agenda.py)
- [TopNavCourses](src/smartschool/courses.py)
- [Courses](src/smartschool/courses.py)
- [FutureTasks](src/smartschool/objects.py)
- [Periods](src/smartschool/periods.py)
- [Results](src/smartschool/results.py)
- [StudentSupportLinks](src/smartschool/student_support.py)
- [MessageHeaders](src/smartschool/messages.py)
- [Message](src/smartschool/messages.py)
- [Attachments](src/smartschool/messages.py)
- [MarkMessageUnread](src/smartschool/messages.py)
- [AdjustMessageLabel](src/smartschool/messages.py)
- [MessageMoveToArchive](src/smartschool/messages.py)
- [MessageMoveToTrash](src/smartschool/messages.py)


## Contributing?
To get started (I always use mamba/conda to create an environment)
```bash
git clone https://github.com/svaningelgem/smartschool.git
cd smartschool
mamba create -n smartschool python=3.11
mamba activate smartschool
pip install poetry
poetry install
```
Now you can start contributing.

To run the test suite:
```bash
poetry run pytest
```
