#!/usr/bin/env python
"""Capture screenshots for docs/USER_JOURNEY.md.

Idempotent and re-runnable:

1. Starts the Django dev server itself on a dedicated port (8321) with the
   env it needs (DJANGO_DEBUG=true, ENABLE_WEBUI=true), waits for readiness.
2. Visits each page in the user journey with Playwright (Chromium,
   1280x800) and saves full-page PNGs to docs/screenshots/<kebab>.png,
   overwriting any previous capture. With --mobile, emulates an iPhone-14
   class device (390x844, dpr 2, touch) and writes to
   docs/screenshots/mobile/<kebab>.png instead.
3. If a page redirects to a login form, creates a throwaway superuser via
   `manage.py shell -c` and logs in through the form, then retries.
4. Kills the server and prints a captured/skipped summary.

Pages that return 4xx/5xx are skipped and reported -- never faked.

Usage:
    .venv/bin/python scripts/capture_user_journey.py [--mobile]

Requires: `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")
PORT = 8321
BASE_URL = f"http://127.0.0.1:{PORT}"
SCREENSHOT_DIR = REPO_ROOT / "docs" / "screenshots"
VIEWPORT = {"width": 1280, "height": 800}
# iPhone 14-class emulation for --mobile runs.
MOBILE_VIEWPORT = {"width": 390, "height": 844}

# Throwaway credentials for the dev-server superuser (local only, never
# committed anywhere; the dev db is throwaway state).
ADMIN_USER = "journey-admin"
ADMIN_PASS = "journey-pass-8321"

# (output filename stem, path, human name)
# NOTE: spa-* paths are client-side React Router routes served by the SPA
# fallback; they require a built webui/frontend/dist. Django template pages
# keep their own slugs. SCREENSHOTS.md tracks every capture produced here.
PAGES = [
    # SPA routes resolve at their no-trailing-slash URLs (Django owns the
    # trailing-slash variants; the SPA fallback regex excludes only those).
    ("landing", "/", "Landing page (React SPA dashboard)"),
    ("spa-chat", "/chat", "Chat (React SPA)"),
    ("spa-teams", "/teams", "Teams (React SPA)"),
    ("spa-blueprints", "/blueprints", "Blueprints (React SPA)"),
    ("spa-agent-creator", "/agent-creator", "Agent creator (React SPA)"),
    ("spa-settings", "/settings", "Settings (React SPA)"),
    ("login", "/accounts/login/", "Login page"),
    ("teams", "/teams/", "Teams dashboard (Django)"),
    ("teams-launch", "/teams/launch/", "Team launcher (Django)"),
    ("blueprint-library", "/blueprint-library/", "Blueprint library (Django)"),
    ("my-blueprints", "/blueprint-library/my-blueprints/", "My blueprints (Django)"),
    ("agent-creator", "/agent-creator/", "Agent creator (Django)"),
    ("settings", "/settings/", "Settings dashboard (Django)"),
]

SERVER_ENV = {
    "DJANGO_DEBUG": "true",       # dev mode; also relaxes SECRET_KEY requirement
    "ENABLE_WEBUI": "true",       # /teams/ et al. 404 without this
    # Uncomment to exercise token auth instead of open dev access:
    # "API_AUTH_TOKEN": "local-journey-token",
}


def start_server() -> subprocess.Popen:
    env = {**os.environ, **SERVER_ENV}
    proc = subprocess.Popen(
        [PYTHON, "manage.py", "runserver", str(PORT), "--noreload"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Django server exited early (rc={proc.returncode})")
        try:
            urllib.request.urlopen(BASE_URL + "/v1/models", timeout=2)
            return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("Django server did not become ready within 60s")


def ensure_superuser() -> None:
    """Create (or reset) a throwaway superuser for form login."""
    code = (
        "from django.contrib.auth import get_user_model; "
        "U = get_user_model(); "
        f"u, _ = U.objects.get_or_create(username='{ADMIN_USER}'); "
        "u.is_staff = True; u.is_superuser = True; "
        f"u.set_password('{ADMIN_PASS}'); u.save(); "
        "print('superuser ready')"
    )
    env = {**os.environ, **SERVER_ENV}
    # Fresh checkouts/dbs have no tables yet — make auth_user exist first.
    subprocess.run(
        [PYTHON, "manage.py", "migrate", "-v", "0"],
        cwd=REPO_ROOT, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [PYTHON, "manage.py", "shell", "-c", code],
        cwd=REPO_ROOT, env=env, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def login_if_needed(page) -> bool:
    """If the current page is a login form, log in with the throwaway
    superuser. Returns True if a login was performed."""
    if "login" not in page.url:
        return False
    user_box = page.locator(
        "input[name='username'], input[type='text']").first
    pass_box = page.locator("input[name='password'], input[type='password']").first
    if user_box.count() == 0 or pass_box.count() == 0:
        return False
    ensure_superuser()
    user_box.fill(ADMIN_USER)
    pass_box.fill(ADMIN_PASS)
    page.locator("button[type='submit'], input[type='submit']").first.click()
    page.wait_for_load_state("networkidle", timeout=15000)
    return True


def capture(page, slug: str, path: str, name: str,
            screenshot_dir: Path) -> tuple[bool, str]:
    """Returns (captured, detail)."""
    url = BASE_URL + path
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    status = response.status if response else 0
    if status >= 400:
        return False, f"HTTP {status}"
    # Follow a login redirect if auth hardening kicked in.
    if "login" in page.url and path not in ("/accounts/login/", "/login/"):
        if login_if_needed(page):
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else 0
            if status >= 400 or "login" in page.url:
                return False, f"auth-blocked (HTTP {status})"
        else:
            return False, "redirected to login; no login form found"
    # Let the SPA / async widgets settle.
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # busy pages (polling) never go idle; capture anyway
    page.wait_for_timeout(750)
    out = screenshot_dir / f"{slug}.png"
    page.screenshot(path=str(out), full_page=True)
    return True, str(out.relative_to(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mobile", action="store_true",
        help="emulate an iPhone-14 class device (390x844, dpr 2, touch) and "
             "write captures to docs/screenshots/mobile/ instead",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed. Run:")
        print("  .venv/bin/pip install playwright && .venv/bin/playwright install chromium")
        return 1

    screenshot_dir = SCREENSHOT_DIR / "mobile" if args.mobile else SCREENSHOT_DIR
    context_kwargs: dict = {"viewport": MOBILE_VIEWPORT if args.mobile else VIEWPORT}
    if args.mobile:
        context_kwargs.update(device_scale_factor=2, is_mobile=True, has_touch=True)

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    print(f"Starting Django dev server on port {PORT} ...")
    server = start_server()
    captured: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(**context_kwargs)
            # Authenticate up front: the chat websocket consumer only accepts
            # logged-in sessions, and authed pages render more realistically.
            try:
                ensure_superuser()
                page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
                login_if_needed(page)
                print(f"  [auth     ] logged in as {ADMIN_USER}")
            except Exception as exc:
                print(f"  [auth     ] anonymous capture (login failed: {exc})")
            for slug, path, name in PAGES:
                try:
                    ok, detail = capture(page, slug, path, name, screenshot_dir)
                except Exception as exc:  # never let one page kill the run
                    ok, detail = False, f"error: {exc}"
                if ok:
                    captured.append((name, detail))
                    print(f"  [captured] {name:30s} {path} -> {detail}")
                else:
                    skipped.append((f"{name} ({path})", detail))
                    print(f"  [skipped ] {name:30s} {path} -- {detail}")
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        print("Django dev server stopped.")

    print(f"\nSummary: {len(captured)} captured, {len(skipped)} skipped")
    for name, detail in skipped:
        print(f"  skipped: {name} -- {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
