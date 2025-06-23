from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import yaml


class Credentials:
    username: str = ""
    password: str = ""
    birthday: str = ""
    main_url: str = ""

    other_info: dict | None = None

    def validate(self) -> None:
        required_fields = [
            "username",
            "password",
            "birthday",
            "main_url",
        ]

        error = []
        for required in required_fields:
            original_value = getattr(self, required)
            new_value = (original_value or "").strip()

            object.__setattr__(self, required, new_value)

            if not new_value:
                error.append(required)

        if error:
            raise RuntimeError(f"Please verify and correct these attributes: {error}")

    def as_dict(self) -> dict[str, str | dict]:
        data: dict = {
            "username": self.username,
            "password": self.password,
            "birthday": self.birthday,
            "main_url": self.main_url,
        }

        if self.other_info:
            data["other_info"] = self.other_info

        return data


@dataclass(frozen=True)
class PathCredentials(Credentials):
    _CREDENTIALS_NAME: ClassVar[str] = "credentials.yml"
    filename: str | Path = ""

    def __post_init__(self):
        object.__setattr__(self, "filename", self._find_credentials_file())

        cred_file: dict = yaml.safe_load(self.filename.read_text(encoding="utf8"))
        object.__setattr__(self, "username", cred_file.pop("username", ""))
        object.__setattr__(self, "password", cred_file.pop("password", ""))
        object.__setattr__(self, "main_url", cred_file.pop("main_url", ""))
        object.__setattr__(self, "birthday", cred_file.pop("birthday", ""))

        object.__setattr__(self, "other_info", cred_file)

    def _find_credentials_file(self) -> Path | None:
        potential_paths = [self.filename]

        if isinstance(self.filename, Path):
            potential_paths.extend(p / self.filename.name for p in self.filename.parents)
            potential_paths.extend(p / self.filename.name for p in Path.cwd().parents)
            potential_paths.append(Path.home() / self.filename.name)
            potential_paths.append(Path.home() / ".cache/smartschool" / self.filename.name)
            potential_paths.extend(p / self._CREDENTIALS_NAME for p in self.filename.parents)

        potential_paths.extend(p / self._CREDENTIALS_NAME for p in Path.cwd().parents)
        potential_paths.append(Path.home() / self._CREDENTIALS_NAME)
        potential_paths.append(Path.home() / f".cache/smartschool/{self._CREDENTIALS_NAME}")

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
        object.__setattr__(self, "username", os.getenv("SMARTSCHOOL_USERNAME", ""))
        object.__setattr__(self, "password", os.getenv("SMARTSCHOOL_PASSWORD", ""))
        object.__setattr__(self, "main_url", os.getenv("SMARTSCHOOL_MAIN_URL", ""))
        object.__setattr__(self, "birthday", os.getenv("SMARTSCHOOL_BIRTHDAY", ""))
