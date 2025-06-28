# Smartschool Parser

[![codecov](https://codecov.io/gh/svaningelgem/smartschool/graph/badge.svg?token=U0A3H3K4L0)](https://codecov.io/gh/svaningelgem/smartschool)

Unofficial Python library providing programmatic access to Smartschool's web platform. Access courses, documents, messages, results, agenda, and more through a clean, type-safe API.

## Quick Start

Create `credentials.yml` with your Smartschool credentials:

```yaml
username: your_username
password: your_password
main_url: your_school.smartschool.be
mfa: your_birthday_or_2fa_secret  # YYYY-mm-dd or Google Authenticator secret

# Optional: email configuration for scripts
email_from: me@myself.ai
email_to:
  - me@myself.ai
```

```python
from smartschool import Smartschool, PathCredentials, Courses

session = Smartschool(PathCredentials())
for course in Courses(session):
    print(course.name)
```

## Core Features

### 📚 Course Management
- **Courses**: List all available courses with metadata
- **TopNavCourses**: Navigation bar courses with full document access
- **Document Browser**: Navigate course folders and download files
- **File Downloads**: Support for all file types with automatic extension detection

### 📊 Academic Information
- **Results**: Retrieve grades and detailed evaluations with teacher feedback
- **Reports**: Download official academic reports (PDF format)
- **Periods**: Academic terms and grading periods
- **FutureTasks**: Upcoming assignments and deadlines
- **PlannedElements**: Scheduled assignments and activities from the planner

### 💬 Communication
- **Messages**: Complete inbox/outbox management with threading support
- **Attachments**: Download and manage message attachments
- **Message Operations**: Mark read/unread, archive, delete, apply labels

### 📅 Calendar & Schedule
- **SmartschoolLessons**: Daily lesson schedules with detailed information
- **SmartschoolHours**: Class period definitions and timings
- **SmartschoolMomentInfos**: Detailed lesson content and assignments

### 🆘 Support & Resources
- **StudentSupportLinks**: Access to school support resources and links

## Authentication Methods

### File-based Credentials (Recommended)
```python
from smartschool import Smartschool, PathCredentials

# Automatically searches for credentials.yml in common locations
session = Smartschool(PathCredentials())
```

### Environment Variables
```python
from smartschool import Smartschool, EnvCredentials

# Uses SMARTSCHOOL_USERNAME, SMARTSCHOOL_PASSWORD, etc.
session = Smartschool(EnvCredentials())
```

### Direct Credentials
```python
from smartschool import Smartschool, AppCredentials

creds = AppCredentials(
    username="your_username",
    password="your_password", 
    main_url="school.smartschool.be",
    mfa="your_birthday_or_2fa_secret"
)
session = Smartschool(creds)
```

### Multi-Factor Authentication
- **Birthday verification**: Use format `YYYY-mm-dd`
- **Google Authenticator**: Requires `pip install smartschool[mfa]`

## Advanced Usage Examples

### Document Management & Downloads
```python
from smartschool import TopNavCourses
from pathlib import Path

# Browse and download course documents
for course in TopNavCourses(session):
    print(f"📚 Course: {course.name}")
    
    for item in course.items:
        if isinstance(item, FileItem):
            # Download individual files
            target_dir = Path("downloads") / course.name
            item.download_to_dir(target_dir)
            print(f"  📄 Downloaded: {item.name}")
            
        elif isinstance(item, FolderItem):
            # Navigate folders recursively
            print(f"  📁 Folder: {item.name}")
            for subitem in item.items:
                print(f"    - {subitem.name}")
```

### Academic Results Analysis
```python
from smartschool import Results

# Analyze academic performance
for result in Results(session):
    points = result.graphic.achieved_points
    total = result.graphic.total_points
    percentage = result.graphic.percentage
    
    print(f"📊 {result.name}: {points}/{total} ({percentage:.1%})")
    print(f"   📅 Date: {result.date}")
    print(f"   👨‍🏫 Teacher: {result.gradebookOwner.name.startingWithFirstName}")
    
    # Access detailed feedback
    if result.feedback:
        for fb in result.feedback:
            print(f"   💬 {fb.user.name.startingWithFirstName}: {fb.text}")
```

### Message Management
```python
from smartschool import MessageHeaders, Message, BoxType

# Process inbox messages
for header in MessageHeaders(session, box_type=BoxType.INBOX):
    if header.unread:
        # Get full message content
        full_message = Message(session, header.id).get()
        
        print(f"📧 From: {full_message.from_}")
        print(f"   Subject: {full_message.subject}")
        print(f"   Body: {full_message.body[:100]}...")
        
        # Download attachments if present
        if header.attachment:
            from smartschool import Attachments
            for attachment in Attachments(session, header.id):
                content = attachment.download()
                Path(f"attachments/{attachment.name}").write_bytes(content)
```

### Task & Assignment Tracking
```python
from smartschool import FutureTasks, PlannedElements
from datetime import datetime

# Track upcoming assignments
print("📋 Upcoming Tasks:")
for day in FutureTasks(session):
    print(f"\n📅 {day.date}")
    for course in day.courses:
        for task in course.items.tasks:
            print(f"  📝 {course.course_title}: {task.label}")
            print(f"     {task.description}")

# Check planned activities
print("\n📅 Planned Activities:")
for element in PlannedElements(session):
    start_time = element.period.dateTimeFrom
    course_names = [c.name for c in element.courses]
    
    print(f"🎯 {element.name}")
    print(f"   📅 {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   📚 Courses: {', '.join(course_names)}")
```

### Schedule Information
```python
from smartschool import SmartschoolLessons, SmartschoolHours
from datetime import date, timedelta

# Get tomorrow's schedule
tomorrow = date.today() + timedelta(days=1)
lessons = SmartschoolLessons(session, timestamp_to_use=tomorrow)

for lesson in lessons:
    hour_details = lesson.hour_details
    
    print(f"🕐 {hour_details.start}-{hour_details.end}: {lesson.course}")
    print(f"   📍 Room: {lesson.classroom}")
    print(f"   👨‍🏫 Teacher: {lesson.teacher}")
    if lesson.subject:
        print(f"   📝 Subject: {lesson.subject}")
```

## Utility Scripts

The package includes several command-line utilities:

### Document Management
```bash
# Interactive document browser
smartschool_browse_docs

# Bulk download all course documents  
smartschool_download_all_documents
```

### Automated Notifications
```bash
# Email notifications for new results
smartschool_report_on_results

# Daily task summaries
smartschool_report_on_future_tasks

# Planned assignment alerts
smartschool_report_on_planned_tasks
```

## Error Handling

```python
from smartschool.exceptions import (
    SmartSchoolException,
    SmartSchoolAuthenticationError,
    SmartSchoolDownloadError,
    SmartSchoolParsingError
)

try:
    session = Smartschool(PathCredentials())
    results = list(Results(session))
except SmartSchoolAuthenticationError:
    print("❌ Login failed - check your credentials")
except SmartSchoolDownloadError as e:
    print(f"❌ Download failed: {e}")
except SmartSchoolParsingError as e:
    print(f"❌ Data parsing error: {e}")
except SmartSchoolException as e:
    print(f"❌ General API error: {e}")
```

## Development Setup

```bash
git clone https://github.com/svaningelgem/smartschool.git
cd smartschool

# Using conda/mamba (recommended)
mamba create -n smartschool python=3.11
mamba activate smartschool

# Install with poetry
pip install poetry
poetry install

# Run tests
poetry run pytest

# Code formatting and linting
poetry run ruff format .
poetry run ruff check .
```

### Development Tools

- **Stub Generation**: `./restub` - Auto-generates `.pyi` files
- **Testing**: pytest with coverage reporting
- **Linting**: ruff for formatting and code quality
- **CI/CD**: GitHub Actions with automated PyPI publishing

## API Reference

### Core Classes
- `Smartschool`: Main session handler with automatic authentication
- `PathCredentials`, `EnvCredentials`, `AppCredentials`: Authentication methods

### Academic Data
- `Courses`, `TopNavCourses`: Course information and navigation
- `Results`: Grade and evaluation management
- `Reports`: Official academic reports
- `Periods`: Academic term information

### Communication
- `MessageHeaders`, `Message`: Email-like messaging system
- `Attachments`: File attachment handling
- `BoxType`, `MessageLabel`: Message organization

### Planning & Schedule
- `FutureTasks`: Assignment deadlines and tasks
- `PlannedElements`: Calendar events and activities
- `SmartschoolLessons`, `SmartschoolHours`: Daily schedules

### Document Management
- `FileItem`, `FolderItem`, `InternetShortcut`: Document types
- `DocumentOrFolderItem`: Union type for navigation

### Support
- `StudentSupportLinks`: School support resources

## Requirements

- **Python**: 3.11+
- **Core Dependencies**: requests, beautifulsoup4, pydantic, pyyaml, logprise
- **Optional**: pyotp (for 2FA support)

## License

GNU General Public License v3.0

## Contributing

Contributions welcome! Please ensure:
- Tests pass: `poetry run pytest`
- Code is formatted: `poetry run ruff format .`
- Linting passes: `poetry run ruff check .`
- Type stubs are updated: `./restub`

## Support

- **Documentation**: Check docstrings and type hints
- **Issues**: [GitHub Issues](https://github.com/svaningelgem/smartschool/issues)
- **API Changes**: See [CHANGELOG.md](CHANGELOG.md)