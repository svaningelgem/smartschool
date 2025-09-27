from __future__ import annotations

import abc
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pathlib import Path

    from requests.models import PreparedRequest, Response


@dataclass
class DevTracingMixin(abc.ABC):
    _trace_filename: str = field(init=False, default_factory=lambda: "dev_tracing/" + datetime.now().strftime("%Y%m%d.%H%M%S.") + "%counter%.txt")
    _trace_counter: int = field(init=False, default=0)

    @property
    def dev_tracing(self) -> bool:
        """Option to enable/disable dev tracing."""
        return False

    @property
    @abc.abstractmethod
    def cache_path(self) -> Path:
        """Where to store the traces."""

    def _make_traced_request(self, request_method: Callable, method: str, url: str, **kwargs) -> Response:
        """Make request with optional dev tracing."""
        try:
            response = request_method(method, url, **kwargs)
            self._save_trace(method, url, kwargs, response=response)
        except BaseException as e:
            self._save_trace(method, url, kwargs, error=e)
            raise
        else:
            return response

    def _save_trace(self, method: str, url: str, kwargs: dict, response: Response = None, error: BaseException | None = None) -> None:
        """Save detailed request trace to a file in human-readable format."""
        if not self.dev_tracing:
            return

        self._trace_counter += 1
        filepath = self.cache_path / self._trace_filename.replace("%counter%", str(self._trace_counter))
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w") as f:
            self._write_header(f)
            self._write_call_context(f)
            self._write_auth_state(f)
            self._write_request(f, method, url, kwargs)

            if response is not None:
                self._write_response_details(f, response, "RESPONSE")

            if error is not None:
                self._write_error(f, error)

            self._write_footer(f)

    def _write_header(self, f) -> None:
        """Write the trace header."""
        f.write("=" * 60 + "\n")
        f.write(f"TRACE #{self._trace_counter} - {datetime.now()}\n")
        f.write("=" * 60 + "\n")

    def _write_call_context(self, f) -> None:
        """Write the call context from the stack trace."""
        f.write("CALL CONTEXT\n")
        f.write("-" * 40 + "\n")
        stack = traceback.extract_stack()[:-1]  # Exclude current frame
        for frame in stack[-3:]:  # Last 3 frames
            f.write(f"  {frame.filename}:{frame.lineno} in {frame.name}\n")

    def _write_auth_state(self, f) -> None:
        """Write the authentication state."""
        login_attempts = getattr(self, "_login_attempts", 0)
        has_creds = getattr(self, "creds", None) is not None
        cookies_count = len(getattr(self, "cookies", []))
        f.write(f"\nAuth state: {login_attempts} login attempts\n")
        f.write(f"Has credentials: {has_creds}\n")
        f.write(f"Session cookies count: {cookies_count}\n")

    def _write_request(self, f, method: str, url: str, kwargs: dict) -> None:
        """Write the request details."""
        f.write("\n" + "=" * 60 + "\n")
        f.write("REQUEST\n")
        f.write("=" * 60 + "\n")
        f.write(f"Method: {method}\n")
        f.write(f"URL: {url}\n")

        f.write("kwargs:\n")
        for key, value in kwargs.items():
            f.write(f"  {key}: {value}\n")

    def _write_error(self, f, error: BaseException) -> None:
        """Write the error details."""
        f.write("\n" + "=" * 60 + "\n")
        f.write("ERROR\n")
        f.write("=" * 60 + "\n")
        f.write(f"Exception Type: {type(error).__name__}\n")
        f.write(f"Exception Message: '{error!s}'\n")

        f.write("Full Traceback:\n")
        f.write("-" * 40 + "\n")
        f.write(traceback.format_exc())
        f.write("-" * 40 + "\n")

        if hasattr(error, "response") and error.response is not None:
            self._write_response_details(f, error.response, "ERROR RESPONSE")

    def _write_footer(self, f) -> None:
        """Write the trace footer."""
        f.write("\n" + "=" * 60 + "\n")
        f.write("END TRACE\n")
        f.write("=" * 60 + "\n")

    def _write_response_details(self, f, response: Response, title: str) -> None:
        """Write response details to a trace file."""
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"{title}\n")
        f.write("=" * 60 + "\n")

        f.write(f"Status Code: {response.status_code} {response.reason}\n")
        f.write(f"Final URL: {response.url}\n")

        if response.history:
            f.write("Redirect History:\n")
            for i, resp in enumerate(response.history):
                f.write(f"  {i + 1}. {resp.status_code} -> {resp.url}\n")

        # Request details from response
        if hasattr(response, "request") and response.request:
            req: PreparedRequest = response.request
            f.write("\nActual Request Details:\n")
            f.write(f"  Method: {req.method}\n")
            f.write(f"  URL: {req.url}\n")
            f.write(f"  Path URL: {getattr(req, 'path_url', 'N/A')}\n")

            if req.headers:
                f.write("  Headers:\n")
                for key, value in req.headers.items():
                    f.write(f"    {key}: {value}\n")

            if hasattr(req, "_cookies") and req._cookies:
                f.write("  Request Cookies:\n")
                for cookie in req._cookies:
                    f.write(f"    {cookie.name}={cookie.value}\n")

            if hasattr(req, "body") and req.body:
                body_size = len(req.body) if isinstance(req.body, (str, bytes)) else 0
                f.write(f"  Body ({body_size} bytes): {req.body}\n")

        f.write("\nResponse Headers:\n")
        for key, value in response.headers.items():
            f.write(f"  {key}: {value}\n")

        if response.cookies:
            f.write("Response Cookies:\n")
            for cookie in response.cookies:
                f.write(f"  {cookie.name}={cookie.value}\n")

        f.write(f"\nContent Size: {len(response.content)} bytes\n")
        f.write(f"Content Encoding: {response.encoding}\n")
        f.write(f"Content Type: {response.headers.get('content-type', 'unknown')}\n")

        f.write("Content:\n")
        f.write("-" * 40 + "\n")
        f.write(response.text)
        f.write("\n" + "-" * 40 + "\n")
