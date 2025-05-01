from __future__ import annotations

import os
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class Credentials(ABC):
    username: str
    password: str
    birthday: str
    main_url: str

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
            value = (getattr(self, required) or "").strip()
            setattr(self, required, value)
            if not value:
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

@dataclass
class PathCredentials(Credentials):
    filename: str | Path = field(default=Path.cwd().joinpath("credentials.yml"))

    def __post_init__(self):
        self.filename = Path(self.filename)

        cred_file: dict = yaml.safe_load(self.filename.read_text(encoding="utf8"))
        self.username = cred_file.pop("username", None)
        self.password = cred_file.pop("password", None)
        self.main_url = cred_file.pop("main_url", None)
        self.birthday = cred_file.pop("birthday", None)

        self.other_info = cred_file


@dataclass
class EnvCredentials(Credentials):
    def __post_init__(self):
        self.username = os.getenv("SMARTSCHOOL_USERNAME")
        self.password = os.getenv("SMARTSCHOOL_PASSWORD")
        self.main_url = os.getenv("SMARTSCHOOL_MAIN_URL")
        self.birthday = os.getenv("SMARTSCHOOL_BIRTHDAY")
