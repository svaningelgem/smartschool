import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from smartschool import EnvCredentials, SmartSchool


@pytest.fixture(scope="session", autouse=True)
def _setup_smartschool_for_tests() -> None:
    original_dir = Path.cwd()

    with TemporaryDirectory() as tmp_dir:  # Because cookies.txt will be written
        os.chdir(tmp_dir)

        try:
            with pytest.MonkeyPatch.context() as monkeypatch:
                monkeypatch.setenv("SMARTSCHOOL_USERNAME", "bumba")
                monkeypatch.setenv("SMARTSCHOOL_PASSWORD", "delu")
                monkeypatch.setenv("SMARTSCHOOL_MAIN_URL", "site")

                SmartSchool.start(EnvCredentials())

                yield
        finally:
            os.chdir(original_dir)
