#!/usr/bin/env python3
"""
Generic Smartschool web-traffic monitor for reverse-engineering endpoints.

Drives a real browser through the Smartschool login chain (login ->
birthday account-verification -> optional TOTP 2fa), visits any path(s) you
point it at, and records every non-static network call (method, url, status,
post body, and the JSON/HTML response body) plus a screenshot and a DOM dump.

Use it to discover the XHR/fetch API behind any part of Smartschool before
writing a client module for it (this is how the `/mydoc` module was mapped).

Login state is cached to a storage-state file, so repeated runs reuse the
session instead of logging in again (Smartschool rate-limits failed logins).

Requires Playwright (kept out of the project dependencies as this is a
standalone dev tool)::

    pip install playwright && playwright install chromium

Usage
-----
    python dev/web_monitor.py /mydoc
    python dev/web_monitor.py /mydoc /intradesk /Topnav/getCourseConfig
    python dev/web_monitor.py --headed --fresh /mydoc

Output goes to dev/_captures/<path>/ : calls.json, bodies.json, page.html,
dom.json and screenshot.png. As a library:

    from dev.web_monitor import SmartschoolMonitor
    with SmartschoolMonitor() as mon:
        mon.login()
        mon.visit("/mydoc")
        # mon.page is a live Playwright page for custom interactions
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Hosts/extensions that are never the API we are looking for.
_BORING = re.compile(r"(static\d*\.smart-school\.net|sentry|/build/|\.(css|js|mjs|woff2?|ttf|png|jpe?g|gif|svg|ico|map))(\?|$)", re.I)


def _is_api(url: str, content_type: str) -> bool:
    if _BORING.search(url):
        return False
    return "/api/" in url or "json" in content_type or "/mydoc" in url or "/Documents" in url or "smsc" in url.lower()


def _load_credentials(path: str = "credentials.yml") -> dict:
    """Find credentials.yml walking up from cwd, like the library does."""
    here = Path.cwd()
    for folder in [here, *here.parents]:
        candidate = folder / path
        if candidate.exists():
            return yaml.safe_load(candidate.read_text(encoding="utf8"))
    raise FileNotFoundError(f"Could not locate {path} from {here}")


def _safe_output_dir(out_dir: Path | str) -> Path:
    """Resolve the capture directory and confine it to the project tree (rejects path-traversal in CLI args)."""
    base = Path.cwd().resolve()
    resolved = Path(base, out_dir).resolve()
    if os.path.commonpath((base, resolved)) != str(base):
        raise ValueError(f"--out must stay within {base}; refusing {resolved}")
    return resolved


class SmartschoolMonitor:
    """Playwright session that logs in once and records traffic per visited path."""

    def __init__(self, *, out_dir: Path | str = "dev/_captures", headless: bool = True, fresh: bool = False) -> None:
        creds = _load_credentials()
        self.base = "https://" + creds["main_url"]
        self.username = creds["username"]
        self.password = creds["password"]
        # The "mfa" answer is the birthday (YYYY-MM-DD) for account-verification.
        self.birthday = str(creds.get("mfa") or creds.get("birthday") or "")
        self.totp_secret = str(creds.get("totp") or creds.get("totp_secret") or "")

        self.out_dir = _safe_output_dir(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.out_dir / "state.json"
        if fresh:
            self.state_file.unlink(missing_ok=True)

        self.headless = headless
        self._calls: list[dict] = []
        self._bodies: dict[str, str] = {}

    # ----- context management -----
    def __enter__(self) -> SmartschoolMonitor:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        kwargs = {"storage_state": str(self.state_file)} if self.state_file.exists() else {}
        self._ctx = self._browser.new_context(accept_downloads=True, **kwargs)
        self.page = self._ctx.new_page()
        self._attach_listeners(self._ctx)
        return self

    def __exit__(self, *exc) -> None:
        with self._suppress():
            self._ctx.storage_state(path=str(self.state_file))
        self._browser.close()
        self._pw.stop()

    @staticmethod
    def _suppress():
        import contextlib

        return contextlib.suppress(Exception)

    # ----- traffic capture -----
    def _attach_listeners(self, ctx) -> None:
        def on_request(req):
            self._calls.append({"d": "req", "method": req.method, "url": req.url, "rt": req.resource_type, "post": req.post_data})

        def on_response(resp):
            ct = resp.headers.get("content-type", "")
            self._calls.append({"d": "resp", "status": resp.status, "method": resp.request.method, "url": resp.url, "ct": ct})
            if _is_api(resp.url, ct):
                key = f"{resp.request.method} {resp.url}"
                try:
                    self._bodies[key] = resp.text()[:50000]
                except Exception as e:  # body already consumed / binary
                    self._bodies[key] = f"<no body: {e}>"

        ctx.on("request", on_request)
        ctx.on("response", on_response)

    @staticmethod
    def _settle(page: Page, ms: int = 2500) -> None:
        """Tolerant settle: the SPA keeps long-lived connections, so networkidle never fires."""
        with SmartschoolMonitor._suppress():
            page.wait_for_load_state("load", timeout=15000)
        with SmartschoolMonitor._suppress():
            page.wait_for_load_state("networkidle", timeout=ms)
        page.wait_for_timeout(800)

    # ----- login chain -----
    def login(self) -> None:
        page = self.page
        page.goto(self.base, wait_until="domcontentloaded", timeout=60000)
        self._settle(page)

        if "/login" in page.url:
            self._assert_not_locked(page)
            page.fill("input[name='login_form[_username]']", self.username)
            page.fill("input[name='login_form[_password]']", self.password)
            page.click("button[type='submit'], input[type='submit']")
            with self._suppress():
                page.wait_for_url(lambda u: "/login" not in u, timeout=30000)
            self._settle(page)
            if "/login" in page.url:
                self._assert_not_locked(page)
                raise RuntimeError("Login failed (still on /login) — check username/password")

        if "account-verification" in page.url:
            page.fill("input[name*='security_question_answer']", self.birthday)
            page.click("button[type='submit'], input[type='submit']")
            with self._suppress():
                page.wait_for_url(lambda u: "account-verification" not in u, timeout=30000)
            self._settle(page)

        if "/2fa" in page.url:
            self._do_2fa(page)

        if any(p in page.url for p in ("/login", "/account-verification", "/2fa")):
            raise RuntimeError(f"Login chain did not complete, stuck at {page.url}")

        self._ctx.storage_state(path=str(self.state_file))

    def _do_2fa(self, page: Page) -> None:
        if not self.totp_secret:
            raise RuntimeError("Account requires 2FA but no 'totp' secret in credentials.yml")
        import pyotp

        page.fill("input[type='text'], input[type='tel']", pyotp.TOTP(self.totp_secret).now())
        page.click("button[type='submit'], input[type='submit']")
        with self._suppress():
            page.wait_for_url(lambda u: "/2fa" not in u, timeout=30000)
        self._settle(page)

    @staticmethod
    def _assert_not_locked(page: Page) -> None:
        body = page.content()
        if "foutieve combinatie" in body or "niet meer mogelijk" in body:
            raise RuntimeError("Smartschool login is rate-limited (too many failed attempts) — wait ~1 minute")

    # ----- visiting & dumping -----
    def visit(self, path: str, *, settle_ms: int = 2500) -> Path:
        """Navigate to a path, let its XHR fire, and dump everything captured during the visit."""
        before = len(self._calls)
        url = path if path.startswith("http") else self.base + path
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self._settle(self.page, settle_ms)

        slug = re.sub(r"[^a-zA-Z0-9]+", "_", path.strip("/")) or "root"
        dest = self.out_dir / slug
        dest.mkdir(parents=True, exist_ok=True)
        with self._suppress():
            self.page.screenshot(path=str(dest / "screenshot.png"), full_page=True)
        (dest / "page.html").write_text(self.page.content(), encoding="utf8")
        (dest / "dom.json").write_text(self._dom_dump(), encoding="utf8")
        self.dump(dest, since=before)
        print(f"[{path}] -> {dest}  (final url: {self.page.url})")
        return dest

    def _dom_dump(self) -> str:
        data = self.page.eval_on_selector_all(
            "a, button, [data-id], [data-folder-id], [data-action], [onclick]",
            "els => els.slice(0,300).map(e => ({tag:e.tagName, txt:(e.innerText||'').slice(0,50),"
            " id:e.id, cls:e.className, href:e.getAttribute('href'), onclick:e.getAttribute('onclick'),"
            " data:Object.assign({},e.dataset)}))",
        )
        return json.dumps(data, indent=2, ensure_ascii=False)

    def dump(self, dest: Path, *, since: int = 0) -> None:
        calls = self._calls[since:]
        (dest / "calls.json").write_text(json.dumps(calls, indent=2, ensure_ascii=False), encoding="utf8")
        (dest / "bodies.json").write_text(json.dumps(self._bodies, indent=2, ensure_ascii=False), encoding="utf8")
        seen = set()
        lines = []
        for c in calls:
            if c["d"] == "resp" and _is_api(c["url"], c.get("ct", "")):
                key = (c["method"], c["url"].split("?")[0])
                if key not in seen:
                    seen.add(key)
                    lines.append(f"{c['method']:4} {c['status']} {c['url']}")
        (dest / "api_endpoints.txt").write_text("\n".join(lines), encoding="utf8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Smartschool web traffic to discover endpoints.")
    parser.add_argument("paths", nargs="+", help="Path(s) to visit, e.g. /mydoc /intradesk")
    parser.add_argument("--out", default="dev/_captures", help="Output directory (default: dev/_captures)")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser")
    parser.add_argument("--fresh", action="store_true", help="Ignore cached login state and log in again")
    args = parser.parse_args()

    with SmartschoolMonitor(out_dir=args.out, headless=not args.headed, fresh=args.fresh) as mon:
        mon.login()
        print("logged in:", mon.page.url)
        for path in args.paths:
            mon.visit(path)


if __name__ == "__main__":
    main()
