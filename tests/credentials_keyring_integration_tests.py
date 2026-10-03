"""The keychain support against the real `keyring` package, through backends that never touch an OS keychain."""

from pathlib import Path

import keyring
import keyring.errors
import pytest
import yaml
from keyring.backend import KeyringBackend
from keyring.backends import fail, null
from pytest_mock import MockerFixture

from smartschool import KeyringCredentials, PathCredentials


class _MemoryKeyring(KeyringBackend):
    """A real backend that keeps its passwords in a dict."""

    priority = 1

    def __init__(self) -> None:
        super().__init__()
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        del self.passwords[(service, username)]


@pytest.fixture(autouse=True)
def _memory_keyring(mocker: MockerFixture) -> None:
    """What `keyring.get_keyring()` returns; a test swaps in another backend the same way."""
    mocker.patch("keyring.core._keyring_backend", _MemoryKeyring())


def _credentials_file(tmp_path: Path, **settings: object) -> Path:
    file = tmp_path / "credentials.yml"
    file.write_text(yaml.dump({"username": "bumba", "main_url": "site", "mfa": "1234-56-78", **settings}), encoding="utf8")
    return file


def test_path_credentials_read_the_password_from_the_keyring(tmp_path: Path):
    keyring.set_password("smartschool", "bumba", "s3cret")

    assert PathCredentials(_credentials_file(tmp_path, keyring=True)).password == "s3cret"


def test_keyring_credentials_read_from_their_own_service():
    keyring.set_password("work", "bumba", "s3cret")

    assert KeyringCredentials(username="bumba", main_url="site", service="work").password == "s3cret"


def test_a_password_that_is_not_stored_asks_to_store_it(tmp_path: Path):
    with pytest.raises(RuntimeError, match=r"No password found .*Store it with: python -m keyring set smartschool bumba$"):
        PathCredentials(_credentials_file(tmp_path, keyring=True))


def test_a_backend_that_cannot_be_used_is_wrapped(tmp_path: Path, mocker: MockerFixture):
    mocker.patch("keyring.core._keyring_backend", fail.Keyring())

    with pytest.raises(RuntimeError, match=r"keyring backend could not be used.*keyrings\.alt") as raised:
        PathCredentials(_credentials_file(tmp_path, keyring=True))

    assert isinstance(raised.value.__cause__, keyring.errors.KeyringError)


def test_a_switched_off_keyring_says_so_instead_of_asking_to_store_the_password(tmp_path: Path, mocker: MockerFixture):
    """The null backend stores nothing, so `python -m keyring set` can never help."""
    mocker.patch("keyring.core._keyring_backend", null.Keyring())

    with pytest.raises(RuntimeError, match=r"keyring is switched off \(keyring\.backends\.null\.Keyring") as raised:
        PathCredentials(_credentials_file(tmp_path, keyring=True))

    assert "python -m keyring set" not in str(raised.value)
