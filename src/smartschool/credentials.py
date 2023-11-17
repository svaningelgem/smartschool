from __future__ import annotations

import os
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class Credentials(ABC):
    username: str
    password: str
    main_url: str

    other_info: dict | None = None

    def validate(self) -> None:
        self.username = (self.username or "").strip()
        self.password = (self.password or "").strip()
        self.main_url = (self.main_url or "").strip()

        error = []
        if not self.username:
            error.append("username")
        if not self.password:
            error.append("password")
        if not self.main_url:
            error.append("main_url")

        if error:
            raise RuntimeError(f"Please verify and correct these attributes: {error}")


@dataclass
class PathCredentials(Credentials):
    filename: str | Path = field(default=Path.cwd().joinpath("credentials.yml"))

    def __post_init__(self):
        self.filename = Path(self.filename)

        cred_file: dict = yaml.safe_load(self.filename.read_text(encoding="utf8"))
        self.username = cred_file.pop("username", None)
        self.password = cred_file.pop("password", None)
        self.main_url = cred_file.pop("main_url", None)

        self.other_info = cred_file


@dataclass
class EnvCredentials(Credentials):
    def __post_init__(self):
        self.username = os.getenv("SMARTSCHOOL_USERNAME")
        self.password = os.getenv("SMARTSCHOOL_PASSWORD")
        self.main_url = os.getenv("SMARTSCHOOL_MAIN_URL")
