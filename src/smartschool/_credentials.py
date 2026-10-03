from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Final

import yaml

try:
    import keyring  # ty: ignore[unresolved-import]  # optional `keyring` extra
except ImportError:
    keyring = None

required_fields: Final[list[str]] = ["username", "password", "main_url", "mfa"]

DEFAULT_KEYRING_SERVICE: Final[str] = "smartschool"

__all__ = ["AppCredentials", "Credentials", "EnvCredentials", "KeyringCredentials", "PathCredentials"]


def _password_from_keyring(service: str, username: str) -> str:
    """Fetch the password of `username` from the OS keychain (macOS Keychain, Windows Credential Manager, Secret Service, ...)."""
    if keyring is None:
        raise RuntimeError("Reading the password from the keyring requires the 'keyring' package. Install with: pip install smartschool[keyring]")

    password = keyring.get_password(service, username)
    if not password:
        raise RuntimeError(
            f"No password found in the keyring for service '{service}' and account '{username}'. Store it with: python -m keyring set {service} {username}"
        )

    return password


class Credentials:
    username: str = ""
    password: str = ""
    mfa: str = ""
    main_url: str = ""

    other_info: dict | None = None

    def validate(self) -> None:
        error = []
        for required in required_fields:
            original_value = getattr(self, required)
            new_value = str(original_value or "").strip()

            object.__setattr__(self, required, new_value)

            if not new_value:
                error.append(required)

        if error:
            raise RuntimeError(f"Please verify and correct these attributes: {error}")

    def as_dict(self) -> dict[str, str | dict]:
        data: dict = {name: getattr(self, name) for name in required_fields}

        if self.other_info:
            data["other_info"] = self.other_info

        return data


@dataclass(frozen=True)
class PathCredentials(Credentials):
    CREDENTIALS_FILENAME: ClassVar[str] = "credentials.yml"
    filename: str | Path = ""

    username: str = field(init=False, default="")
    password: str = field(init=False, default="", repr=False)
    main_url: str = field(init=False, default="")
    mfa: str = field(init=False, default="")
    other_info: dict | None = field(init=False, default=None)

    def __post_init__(self):
        credentials_file = self._find_credentials_file()
        object.__setattr__(self, "filename", credentials_file)

        cred_file: dict = yaml.safe_load(credentials_file.read_text(encoding="utf8"))
        for attr in required_fields:
            object.__setattr__(self, attr, cred_file.pop(attr, ""))

        object.__setattr__(self, "other_info", cred_file)

        # No password in the file: fall back on the OS keychain (only when the optional `keyring` package is installed).
        if not self.password and self.username and keyring is not None:
            object.__setattr__(self, "password", _password_from_keyring(DEFAULT_KEYRING_SERVICE, str(self.username)))

    def _find_credentials_file(self) -> Path:
        to_investigate = self.filename
        potential_paths = [to_investigate]

        if to_investigate:
            if isinstance(to_investigate, str):
                to_investigate = Path(to_investigate)

            potential_paths.extend(p / to_investigate.name for p in to_investigate.parents)
            potential_paths.extend(p / to_investigate.name for p in Path.cwd().parents)
            potential_paths.append(Path.home() / to_investigate.name)
            potential_paths.append(Path.home() / ".cache/smartschool" / to_investigate.name)
            potential_paths.extend(p / self.CREDENTIALS_FILENAME for p in to_investigate.parents)

        potential_paths.append(Path.cwd() / self.CREDENTIALS_FILENAME)
        potential_paths.extend(p / self.CREDENTIALS_FILENAME for p in Path.cwd().parents)
        potential_paths.append(Path.home() / self.CREDENTIALS_FILENAME)
        potential_paths.append(Path.home() / ".cache/smartschool" / self.CREDENTIALS_FILENAME)

        already_seen = set()
        for p in potential_paths:
            if not p:
                continue

            if not isinstance(p, Path):
                p = Path(p).resolve().absolute()

            if p not in already_seen and p.exists():
                return p

            already_seen.add(p)

        raise FileNotFoundError(self.filename)


@dataclass(frozen=True)
class EnvCredentials(Credentials):
    def __post_init__(self):
        for attr in required_fields:
            object.__setattr__(self, attr, os.getenv(f"SMARTSCHOOL_{attr.upper()}", ""))


@dataclass(frozen=True)
class KeyringCredentials(Credentials):
    """
    Credentials whose password lives in the OS keychain instead of a file or environment variable.

    Store the password once with: `python -m keyring set smartschool <username>`
    """

    username: str
    main_url: str
    mfa: str
    service: str = DEFAULT_KEYRING_SERVICE
    password: str = field(init=False, default="", repr=False)

    def __post_init__(self):
        if self.username:  # An empty username is reported by validate()
            object.__setattr__(self, "password", _password_from_keyring(self.service, str(self.username)))


@dataclass(frozen=True)
class AppCredentials(Credentials):
    username: str
    password: str = field(default="", repr=False)  # `default` mirrors the class-level default inherited from Credentials
    main_url: str
    mfa: str
