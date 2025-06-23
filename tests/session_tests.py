import pytest

from smartschool import EnvCredentials, Smartschool


def test_smartschool_not_started_yet():
    with pytest.raises(RuntimeError, match="Smartschool instance must have valid credentials"):
        Smartschool().get("/")


def test_smartschool_repr(session: Smartschool):
    assert repr(session) == "Smartschool(for: bumba)"


def test_smartschool_without_params():
    assert Smartschool().creds is None


def test_smartschool_with_credentials(session: Smartschool):
    assert session.creds is not None
