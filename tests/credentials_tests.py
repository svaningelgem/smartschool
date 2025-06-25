from pathlib import Path

import pytest
import yaml

from smartschool import EnvCredentials, PathCredentials, Smartschool


def _create_credentials_file(tmp_path: Path):
    file = tmp_path.joinpath("creds.yml")

    with file.open(mode="w", encoding="utf8") as fp:
        yaml.dump(EnvCredentials().as_dict(), fp)

    return file


def test_env_credentials(session: Smartschool):
    # This information comes from conftest.py:session (included fixture)

    sut = EnvCredentials()
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


@pytest.mark.parametrize("make_empty", ["SMARTSCHOOL_USERNAME", "SMARTSCHOOL_PASSWORD", "SMARTSCHOOL_MAIN_URL", "SMARTSCHOOL_MFA"])
def test_env_credentials_empty(monkeypatch, make_empty):
    monkeypatch.delenv(make_empty, raising=False)

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        EnvCredentials().validate()


@pytest.mark.parametrize("as_type", [Path, str])
def test_path_credentials(tmp_path: Path, session: Smartschool, as_type: type):
    tmp_credentials = _create_credentials_file(tmp_path)
    sut = PathCredentials(as_type(tmp_credentials))
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


def test_path_credentials_without_path(monkeypatch, tmp_path: Path, session):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    tmp_path.joinpath(PathCredentials.CREDENTIALS_FILENAME).write_text(yaml.dump(EnvCredentials().as_dict()), encoding="utf8")

    sut = PathCredentials()
    sut.validate()

    assert sut.username == "bumba"
    assert sut.password == "delu"
    assert sut.main_url == "site"
    assert sut.mfa == "1234-56-78"


def test_path_credentials_file_not_found(tmp_path: Path, session: Smartschool):
    with pytest.raises(FileNotFoundError):
        PathCredentials(tmp_path.joinpath("not_found.yml"))


@pytest.mark.parametrize(
    "make_empty",
    [
        "USERNAME",
        "PASSWORD",
        "MAIN_URL",
        "MFA",
    ],
)
def test_path_credentials_empty(monkeypatch, make_empty, tmp_path: Path, session: Smartschool):
    monkeypatch.setenv(f"SMARTSCHOOL_{make_empty}", "")

    with pytest.raises(RuntimeError, match="Please verify and correct these attribute"):
        PathCredentials(_create_credentials_file(tmp_path)).validate()


def test_credentials_exporting_as_dict_with_other_info(session: Smartschool):
    sut = EnvCredentials()
    object.__setattr__(sut, "other_info", {"test": "something"})

    assert sut.as_dict() == {
        "username": "bumba",
        "password": "delu",
        "main_url": "site",
        "mfa": "1234-56-78",
        "other_info": {"test": "something"},
    }


def test_credentials_exporting_as_dict_without_other_info(session: Smartschool):
    sut = EnvCredentials()

    assert sut.as_dict() == {
        "username": "bumba",
        "password": "delu",
        "main_url": "site",
        "mfa": "1234-56-78",
    }
