"""The 2FA path of `dev/web_monitor.py`, the capture tool that keeps playwright and pyotp out of the dependencies."""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from pytest_mock import MockerFixture


def _load_monitor(mocker: MockerFixture, tmp_path: Path, **credentials: str) -> tuple[ModuleType, Any]:
    """Import the tool with playwright stubbed out and build a monitor from a throwaway credentials file."""
    playwright = mocker.MagicMock()
    mocker.patch.dict(sys.modules, {"playwright": playwright, "playwright.sync_api": playwright.sync_api})

    (tmp_path / "credentials.yml").write_text(
        yaml.dump({"main_url": "site", "username": "bumba", "password": "delu", "mfa": "1234-56-78", **credentials}),
        encoding="utf8",
    )

    module = importlib.import_module("dev.web_monitor")
    return module, module.SmartschoolMonitor(out_dir="captures")


def test_2fa_without_a_totp_secret_is_refused(tmp_path: Path, mocker: MockerFixture):
    _, monitor = _load_monitor(mocker, tmp_path)

    with pytest.raises(RuntimeError, match=r"no 'totp' secret in credentials\.yml"):
        monitor._do_2fa(mocker.Mock())  # pylint: disable=protected-access  # white-box test


def test_2fa_without_pyotp_is_refused(tmp_path: Path, mocker: MockerFixture):
    """An optional extra that is not installed is reported, not raised as an ImportError."""
    module, monitor = _load_monitor(mocker, tmp_path, totp="BASE32SECRET")
    mocker.patch.object(module, "pyotp", None)

    with pytest.raises(RuntimeError, match="pip install pyotp"):
        monitor._do_2fa(mocker.Mock())  # pylint: disable=protected-access  # white-box test


def test_2fa_submits_the_current_totp_code(tmp_path: Path, mocker: MockerFixture):
    module, monitor = _load_monitor(mocker, tmp_path, totp="BASE32SECRET")
    pyotp = mocker.patch.object(module, "pyotp")
    pyotp.TOTP.return_value.now.return_value = "123456"
    page = mocker.Mock()

    monitor._do_2fa(page)  # pylint: disable=protected-access  # white-box test

    pyotp.TOTP.assert_called_once_with("BASE32SECRET")
    page.fill.assert_called_once_with("input[type='text'], input[type='tel']", "123456")
