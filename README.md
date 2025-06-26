# Smartschool Parser

[![codecov](https://codecov.io/gh/svaningelgem/smartschool/graph/badge.svg?token=U0A3H3K4L0)](https://codecov.io/gh/svaningelgem/smartschool)

Unofficial Python library to interface with Smartschool's web platform, providing programmatic access to courses, documents, messages, results, and more.

## Quick Start

Copy `credentials.yml.example` to `credentials.yml` and configure with your credentials:

```yaml
username: your_username
password: your_password
main_url: your_school.smartschool.be
mfa: your_birthday_or_2fa_secret
```

```python
from smartschool import Smartschool, PathCredentials, Courses

session = Smartschool(PathCredentials())
for course in Courses(session):
    print(course.name)
```

## Features

### Course Management
- **Courses**: List all available courses
- **TopNavCourses**: Navigation bar courses with document access
- **Document Browser**: Navigate and download course documents and folders
- **File Downloads**: Support for various file types with automatic extension detection

### Academic Information
- **Results**: Retrieve grades and evaluations with detailed feedback
- **Periods**: Academic periods and terms
- **FutureTasks**: Upcoming assignments and deadlines
- **PlannedElements**: Scheduled assignments and activities

### Communication
- **Messages**: Full inbox/outbox management with attachments
- **Message Operations**: Mark as read/unread, archive, delete, label management
- **Attachments**: Download message attachments

### Calendar & Schedule
- **AgendaLessons**: Daily lesson schedules
- **AgendaHours**: Class period definitions
- **AgendaMomentInfos**: Detailed lesson information

### Support
- **StudentSupportLinks**: Access to support resources

## Authentication

Supports multiple authentication methods:
- **Standard login**: Username/password
- **Security question**: Birthday verification
- **2FA**: Google Authenticator (requires `pyotp`)

```python
# Environment variables
from smartschool import Smartschool, EnvCredentials
session = Smartschool(EnvCredentials())

# Direct credentials
from smartschool import Smartschool, AppCredentials
creds = AppCredentials(
    username="user",
    password="pass", 
    main_url="school.smartschool.be",
    mfa="birthday_or_2fa"
)
session = Smartschool(creds)
```

## Advanced Usage

### Document Management
```python
from smartschool import TopNavCourses

for course in TopNavCourses(session):
    print(f"Course: {course.name}")
    for item in course.items:
        if isinstance(item, FileItem):
            item.download_to_dir(Path("downloads"))
        elif isinstance(item, FolderItem):
            # Navigate into subfolders
            for subitem in item.items:
                print(f"  - {subitem.name}")
```

### Message Processing
```python
from smartschool import MessageHeaders, Message, BoxType

for header in MessageHeaders(session, box_type=BoxType.INBOX):
    full_message = Message(session, header.id).get()
    print(f"From: {full_message.from_}")
    print(f"Subject: {full_message.subject}")
    print(f"Body: {full_message.body}")
```

### Results Analysis
```python
from smartschool import Results, ResultDetail

for result in Results(session):
    print(f"{result.name}: {result.graphic.achieved_points}/{result.graphic.total_points}")
    
    # Get detailed information
    detail = ResultDetail(session, result.identifier).get()
    print(f"Teacher feedback: {detail.feedback}")
```

### Task Management
```python
from smartschool import FutureTasks, PlannedElements

# Upcoming assignments
for day in FutureTasks(session):
    print(f"Date: {day.date}")
    for course in day.courses:
        for task in course.items.tasks:
            print(f"  {task.label}: {task.description}")

# Planned activities
for element in PlannedElements(session):
    print(f"{element.name} - {element.period.dateTimeFrom}")
```

## Scripts

The package includes several utility scripts:

- `smartschool_browse_docs`: Interactive document browser
- `smartschool_download_all_documents`: Bulk download all course documents
- `smartschool_report_on_*`: Email notification scripts for tasks and results

## API Reference

### Core Classes
- `Smartschool`: Main session handler
- `PathCredentials`, `EnvCredentials`, `AppCredentials`: Authentication methods

### Data Access
- `Courses`, `TopNavCourses`: Course information
- `Results`, `ResultDetail`: Grade management
- `MessageHeaders`, `Message`, `Attachments`: Communication
- `FutureTasks`, `PlannedElements`: Task scheduling
- `Periods`: Academic terms
- `StudentSupportLinks`: Support resources

### File Management
- `FileItem`, `FolderItem`, `InternetShortcut`: Document types
- `DocumentOrFolderItem`: Union type for navigation

### Agenda
- `SmartschoolLessons`, `SmartschoolHours`, `SmartschoolMomentInfos`: Schedule access

## Error Handling

```python
from smartschool.exceptions import (
    SmartSchoolException,
    SmartSchoolAuthenticationError, 
)

try:
    session = Smartschool(PathCredentials())
except SmartSchoolAuthenticationError:
    print("Login failed - check credentials")
except SmartSchoolException as e:
    print(f"API error: {e}")
```

## Development

```bash
git clone https://github.com/svaningelgem/smartschool.git
cd smartschool
mamba create -n smartschool python=3.11
mamba activate smartschool
pip install poetry
poetry install
```

Run tests:
```bash
poetry run pytest
```

## License

GNU GPLv3

## Contributing

Contributions welcome! Please ensure tests pass and follow the existing code style.