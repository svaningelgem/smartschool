from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final

import yaml

if TYPE_CHECKING:
    from datetime import date

required_fields: Final[list[str]] = ["username", "password", "main_url", "mfa"]

__all__ = ["AppCredentials", "Credentials", "EnvCredentials", "PathCredentials"]


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
        data: dict = {field: getattr(self, field) for field in required_fields}

        if self.other_info:
            data["other_info"] = self.other_info

        return data


@dataclass(frozen=True)
class PathCredentials(Credentials):
    CREDENTIALS_FILENAME: ClassVar[str] = "credentials.yml"
    filename: str | Path = ""

    username: str = field(init=False, default=None)
    password: str = field(init=False, default=None)
    main_url: str = field(init=False, default=None)
    mfa: date = field(init=False, default=None)
    other_info: dict = field(init=False, default=None)

    def __post_init__(self):
        object.__setattr__(self, "filename", self._find_credentials_file())

        cred_file: dict = yaml.safe_load(self.filename.read_text(encoding="utf8"))
        for attr in required_fields:
            object.__setattr__(self, attr, cred_file.pop(attr, ""))

        object.__setattr__(self, "other_info", cred_file)

    def _find_credentials_file(self) -> Path | None:
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
class AppCredentials(Credentials):
    username: str
    password: str
    main_url: str
    mfa: str
