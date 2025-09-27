from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, Mock

import pytest

from smartschool._dev_tracing import DevTracingMixin


@pytest.fixture
def sut(tmp_path: Path) -> DevTracingMixin:
    class TracingTestClass(DevTracingMixin):
        cache_path: Path = tmp_path
        dev_tracing: bool = True
        _login_attempts: int = 1
        creds: str = "fake_creds"
        cookies: ClassVar[list[str]] = ["cookie1=value1", "cookie2=value2"]

    return TracingTestClass()


@pytest.fixture
def mock_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.reason = "OK"
    resp.url = "https://example.com/final"
    resp.history = [MagicMock(status_code=301, url="https://example.com/redirect")]
    resp.request = MagicMock(
        method="GET",
        url="https://example.com",
        path_url="/path",
        headers={"User-Agent": "test"},
        _cookies=[MagicMock(name="session", value="abc123")],
        body=b"test body",
    )
    resp.headers = {"Content-Type": "text/plain"}
    resp.cookies = [MagicMock(name="new_cookie", value="new_value")]
    resp.content = b"response content"
    resp.encoding = "utf-8"
    resp.text = "response text"
    return resp


def test_dev_tracing_disabled(tmp_path):
    class DummyDisabled(DevTracingMixin):
        @property
        def cache_path(self):
            return tmp_path

        @property
        def dev_tracing(self):
            return False

    dummy = DummyDisabled()
    mock_method = Mock(return_value=Mock())
    dummy._make_traced_request(mock_method, "GET", "https://example.com")
    trace_files = list((tmp_path / "dev_tracing").glob("*.txt"))
    assert len(trace_files) == 0


def test_successful_request(sut, mock_response, tmp_path):
    mock_method = Mock(return_value=mock_response)
    sut._make_traced_request(mock_method, "POST", "https://example.com", data={"key": "value"})

    trace_dir = tmp_path / "dev_tracing"
    trace_files = list(trace_dir.glob("*.txt"))
    assert len(trace_files) == 1
    trace_file = trace_files[0]

    with trace_file.open() as f:
        content = f.read()

    assert "TRACE #1" in content
    assert "CALL CONTEXT" in content
    assert "Auth state: 1 login attempts" in content
    assert "Has credentials: True" in content
    assert "Session cookies count: 2" in content
    assert "Method: POST" in content
    assert "URL: https://example.com" in content
    assert "  data: {'key': 'value'}" in content
    assert "Status Code: 200 OK" in content
    assert "Redirect History:" in content
    assert "Actual Request Details:" in content
    assert "  Body (9 bytes): b'test body'" in content
    assert (
        """Content:
----------------------------------------
response text
----------------------------------------
"""
        in content
    )
    assert "END TRACE" in content


def _get_content_with_exception(sut: DevTracingMixin, tmp_path: Path, mock_response: Mock) -> str:
    class TestExc(Exception):
        response = mock_response

    mock_method = Mock(side_effect=TestExc)
    with pytest.raises(TestExc):
        sut._make_traced_request(mock_method, "GET", "https://example.com", params={"p": 1})

    trace_dir = tmp_path / "dev_tracing"
    trace_files = list(trace_dir.glob("*.txt"))
    assert len(trace_files) == 1
    return trace_files[0].read_text()


def test_failed_request(sut, tmp_path):
    content = _get_content_with_exception(sut, tmp_path, None)

    assert "TRACE #1" in content
    assert "ERROR" in content
    assert (
        """Exception Message: ''
Full Traceback:
----------------------------------------
Traceback (most recent call last):"""
        in content
    )
    assert "ERROR RESPONSE" not in content
    assert "Status Code: 200 OK" not in content
    assert "END TRACE" in content


def test_failed_request_with_response(sut, mock_response, tmp_path):
    content = _get_content_with_exception(sut, tmp_path, mock_response)

    assert "TRACE #1" in content
    assert "ERROR" in content
    assert (
        """Exception Message: ''
Full Traceback:
----------------------------------------
Traceback (most recent call last):"""
        in content
    )
    assert "ERROR RESPONSE" in content
    assert "Status Code: 200 OK" in content
    assert "END TRACE" in content


def test_failed_request_with_bare_bones_response(sut, mock_response, tmp_path):
    mock_response.history = None
    mock_response.request = None
    mock_response.cookies = None

    content = _get_content_with_exception(sut, tmp_path, mock_response)

    assert "Redirect History:" not in content
    assert "Actual Request Details:" not in content
    assert "  Headers:" not in content
    assert "Response Cookies:" not in content


def test_failed_request_with_bare_bones_response2(sut, mock_response, tmp_path):
    mock_response.request.headers = None
    mock_response.request._cookies = None
    mock_response.request.body = None

    content = _get_content_with_exception(sut, tmp_path, mock_response)

    assert "Redirect History:" in content
    assert "Actual Request Details:" in content
    assert "  Headers:" not in content
    assert "  Request Cookies:" not in content
    assert "Response Cookies:" in content
