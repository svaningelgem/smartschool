# Error Handling

All exceptions inherit from `SmartSchoolException`.

## Exception Hierarchy

```
SmartSchoolException
├── SmartSchoolAuthenticationError
├── SmartSchoolParsingError
└── SmartSchoolDownloadError
    └── SmartSchoolJsonError
```

## Exception Types

| Exception | When |
|-----------|------|
| `SmartSchoolAuthenticationError` | Login failed, max attempts reached, or 2FA misconfigured |
| `SmartSchoolParsingError` | Unexpected HTML/data format from Smartschool |
| `SmartSchoolDownloadError` | HTTP error during file download (includes `response` and `status_code`) |
| `SmartSchoolJsonError` | API returned invalid JSON (includes `response`) |

## Usage

```python
from smartschool import Smartschool, PathCredentials, Results
from smartschool.exceptions import (
    SmartSchoolAuthenticationError,
    SmartSchoolDownloadError,
    SmartSchoolJsonError,
    SmartSchoolParsingError,
    SmartSchoolException,
)

try:
    session = Smartschool(PathCredentials())
    results = list(Results(session))
except SmartSchoolAuthenticationError as e:
    print(f"Login failed: {e.message}")
except SmartSchoolJsonError as e:
    print(f"Invalid JSON (HTTP {e.status_code}): {e.message}")
except SmartSchoolDownloadError as e:
    print(f"Download failed (HTTP {e.status_code}): {e.message}")
except SmartSchoolParsingError as e:
    print(f"Parsing error: {e.message}")
except SmartSchoolException as e:
    print(f"General error: {e.message}")
```

## Common Scenarios

**No results available yet** (start of school year):
```python
# Courses() depends on results being available.
# Use CourseList() instead — it always works.
from smartschool import CourseList

for course in CourseList(session):
    print(course.name)
```

**2FA not installed**:
```python
# If your school uses Google Authenticator 2FA, install the optional dependency:
#   pip install smartschool[mfa]
# Then provide the TOTP secret as the mfa field in your credentials.
```
