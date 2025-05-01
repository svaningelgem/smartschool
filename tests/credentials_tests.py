from pathlib import Path

import pytest
import yaml

from smartschool import EnvCredentials, PathCredentials


def _create_credentials_file(tmp_path: Path):
    file = tmp_path.joinpath("creds.yml")

    with file.open(mode="w", encoding="utf8") as fp:
        yaml.dump(EnvCredentials().as_dict(), fp)

    return file


def test_env_credentials():
    # This information comes from conftest.py:"_setup_smartschool_for_tests"

    sut = EnvCredentials()
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.birthday == "1234-56-78"


@pytest.mark.parametrize("make_empty", ["SMARTSCHOOL_USERNAME", "SMARTSCHOOL_PASSWORD", "SMARTSCHOOL_MAIN_URL"])
def test_env_credentials_empty(monkeypatch, make_empty):
    monkeypatch.delenv(make_empty, raising=False)

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        EnvCredentials().validate()


def test_path_credentials(tmp_path: Path):
    sut = PathCredentials(_create_credentials_file(tmp_path))
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.birthday == "1234-56-78"


@pytest.mark.parametrize("make_empty", ["USERNAME",
                                        "PASSWORD",
                                        "MAIN_URL",
                                        "BIRTHDAY",])
def test_path_credentials_empty(monkeypatch, make_empty, tmp_path: Path):
    monkeypatch.setenv(f"SMARTSCHOOL_{make_empty}", "")

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        PathCredentials(_create_credentials_file(tmp_path)).validate()
