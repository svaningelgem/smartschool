# Authentication

All API access requires an authenticated `Smartschool` session. Four credential methods are available.

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

## OS Keychain (keyring)

Prefer not to keep your password in plain text? Store it in your operating system's keychain
(macOS Keychain, Windows Credential Manager, or a Secret Service such as GNOME Keyring / KWallet)
using the optional [`keyring`](https://pypi.org/project/keyring/) dependency:

```bash
pip install smartschool[keyring]
```

Save the password once (you will be prompted for it, so it never ends up in your shell history):

```bash
python -m keyring set smartschool your_username
```

Then use `KeyringCredentials`, which looks the password up under service name `smartschool` and
account `your_username` (override the service name with `service="..."`):

```python
from smartschool import Smartschool, KeyringCredentials

creds = KeyringCredentials(
    username="your_username",
    main_url="your_school.smartschool.be",
    mfa="your_birthday_or_2fa_secret",
)
session = Smartschool(creds)
```

`PathCredentials` falls back on the keychain automatically: leave the `password:` line out of
`credentials.yml` and, when `keyring` is installed, the password is read from service `smartschool` and
the `username` from that file. A clear error is raised when no such item exists. Without `keyring`
installed, a missing password is reported as before.

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
