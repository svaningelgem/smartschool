# Smartschool Parser

[![codecov](https://codecov.io/gh/svaningelgem/smartschool/graph/badge.svg?token=U0A3H3K4L0)](https://codecov.io/gh/svaningelgem/smartschool)

Unofficial Python library providing programmatic access to Smartschool's web platform. Access courses, documents, messages, results, agenda, and more through a clean, type-safe API.

## Quick Start

Install from PyPI:

```bash
pip install smartschool
```

Create `credentials.yml` with your Smartschool credentials:

```yaml
username: your_username
password: your_password
main_url: your_school.smartschool.be
mfa: your_birthday_or_2fa_secret  # YYYY-mm-dd or Google Authenticator secret
```

```python
from smartschool import Smartschool, PathCredentials, Courses

session = Smartschool(PathCredentials())
for course in Courses(session):
    print(course.name)
```

## Features

| Category | Classes | Description |
|----------|---------|-------------|
| **Courses** | `TopNavCourses`, `Courses`, `CourseList` | Browse courses and download documents |
| **Intradesk** | `Intradesk` | Browse and download files from the intradesk |
| **Results** | `Results`, `Reports`, `Periods` | Grades, evaluations, report cards |
| **Messages** | `MessageHeaders`, `Message`, `Attachments`, `MessageComposerForm`, `RecipientType` | Inbox/outbox, compose, attachments, labels |
| **Schedule** | `SmartschoolLessons`, `SmartschoolHours` | Daily schedules, class periods |
| **Planner** | `PlannedElements`, `FutureTasks` | Assignments, deadlines, activities |
| **Support** | `StudentSupportLinks` | School support resources |

## Documentation

Detailed usage guides with examples:

- [Authentication](docs/authentication.md) - Credential setup and MFA
- [Courses & Documents](docs/courses.md) - Browsing courses and downloading files
- [Intradesk](docs/intradesk.md) - Intradesk file management
- [Results & Reports](docs/results.md) - Grades, evaluations, and report cards
- [Messages](docs/messages.md) - Inbox, compose/send, attachments, and message management
- [Schedule & Agenda](docs/schedule.md) - Lessons, hours, and moment info
- [Planner & Tasks](docs/planner.md) - Planned elements and future tasks
- [Error Handling](docs/errors.md) - Exception types and handling patterns

## Development

```bash
git clone https://github.com/svaningelgem/smartschool.git
cd smartschool
pip install poetry
poetry install

# Run tests
poetry run pytest

# Linting & formatting
poetry run ruff check .
poetry run ruff format .
```

## Requirements

- **Python**: 3.10+
- **Core Dependencies**: requests, beautifulsoup4, pydantic, pyyaml, logprise
- **Optional**: `pip install smartschool[mfa]` for Google Authenticator 2FA support

## License

GNU General Public License v3.0

## Contributing

Contributions welcome! Please ensure:
- Tests pass: `poetry run pytest`
- Code is formatted: `poetry run ruff format .`
- Linting passes: `poetry run ruff check .`
- Type stubs are updated: `./restub`

## Support

- **Issues**: [GitHub Issues](https://github.com/svaningelgem/smartschool/issues)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
