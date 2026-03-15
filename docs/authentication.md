# Authentication

All API access requires an authenticated `Smartschool` session. Three credential methods are available.

## File-based Credentials (Recommended)

Create a `credentials.yml` file:

```yaml
username: your_username
password: your_password
main_url: your_school.smartschool.be
mfa: your_birthday_or_2fa_secret

# Optional: email configuration for notification scripts
email_from: me@myself.ai
email_to:
  - me@myself.ai
```

```python
from smartschool import Smartschool, PathCredentials

# Auto-discovers credentials.yml in cwd, parent dirs, home folder, or cache folder
session = Smartschool(PathCredentials())

# Or specify the path explicitly
session = Smartschool(PathCredentials(filename="/path/to/credentials.yml"))
```

## Environment Variables

```python
from smartschool import Smartschool, EnvCredentials

# Reads from:
#   SMARTSCHOOL_USERNAME
#   SMARTSCHOOL_PASSWORD
#   SMARTSCHOOL_MAIN_URL
#   SMARTSCHOOL_MFA
session = Smartschool(EnvCredentials())
```

## Direct Credentials

```python
from smartschool import Smartschool, AppCredentials

creds = AppCredentials(
    username="your_username",
    password="your_password",
    main_url="school.smartschool.be",
    mfa="your_birthday_or_2fa_secret",
)
session = Smartschool(creds)
```

## Multi-Factor Authentication

The `mfa` field supports two formats:

- **Birthday verification**: Use format `YYYY-mm-dd` (e.g., `2010-05-15`)
- **Google Authenticator (TOTP)**: Provide the secret key from your authenticator setup. Requires the optional dependency:

```bash
pip install smartschool[mfa]
```

## Dev Tracing

For debugging API interactions, enable dev tracing:

```python
session = Smartschool(PathCredentials(), dev_tracing=True)
```

This writes detailed request/response traces to the cache directory.
