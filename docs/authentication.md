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
pip install "smartschool[keyring]"
```

Save the password once (you will be prompted for it, so it never ends up in your shell history):

```bash
python -m keyring set smartschool your_username
```

Then use `KeyringCredentials`, which looks the password up under service name `smartschool` and
account `your_username` (override the service name with `service="..."`).:

```python
from smartschool import Smartschool, KeyringCredentials

creds = KeyringCredentials(
    username="your_username",
    main_url="your_school.smartschool.be",
    mfa="your_birthday_or_2fa_secret",
)
session = Smartschool(creds)
```

To keep using `credentials.yml` (`PathCredentials`), opt in explicitly: leave the `password:` line out and add
`keyring: true` (or `keyring: your-service-name` to use another service name). The `username` from that file is the account
that is looked up. Nothing changes without that opt-in, even when the `keyring` package happens to be installed:

```yaml
username: your_username
mfa: YYYY-mm-dd
main_url: your_school.smartschool.be
keyring: true
```

A clear error is raised when no such item exists, or when the keychain backend cannot be used.

> **Headless Linux and WSL** have no keychain backend, so reading from the keyring fails there. Either run a Secret
> Service (for example GNOME Keyring) or install a file-based backend such as
> [`keyrings.alt`](https://pypi.org/project/keyrings.alt/). Be aware that `keyrings.alt` on its own does **not encrypt**
> the password: it stores it base64-encoded in `~/.local/share/python_keyring/keyring_pass.cfg` (readable only by your
> user), which protects it no better than a `password:` line in `credentials.yml`. Install `pycryptodomex` as well to
> get its encrypted keyring instead, which asks for a master password to unlock it.

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
