#!/usr/bin/env python
"""Capture screenshots for docs/USER_JOURNEY.md + GUIDED_TOUR.md.

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
4. Writes a JSON capture manifest (status, final URL, PNG path) when
   ``CAPTURE_MANIFEST`` is set, or to ``--manifest PATH``.
5. Kills the server and prints a captured/skipped summary.

Pages that return 4xx/5xx are skipped and reported -- never faked.

Usage:
    .venv/bin/python scripts/capture_user_journey.py [--mobile]
    CAPTURE_MANIFEST=/path/manifest.json .venv/bin/python scripts/capture_user_journey.py

Requires: `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`

Canonical operator UI is Django trailing-slash routes. Bare ``/teams``,
``/blueprints``, and ``/settings`` 302 to Django; spa-* stems still capture
those entry URLs so the tour can document the redirect honestly.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")
PORT = int(os.environ.get("CAPTURE_PORT", "8321"))
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
# SCREENSHOTS.md tracks every capture produced here.
PAGES = [
    # Landing remains the React SPA shell (demoted operator chrome → Django hrefs).
    ("landing", "/", "Landing page (React SPA dashboard)"),
    # SPA-only routes still served by React (no Django twin).
    ("spa-chat", "/chat", "Chat (React SPA)"),
    # Bare paths that redirect to canonical Django operator UI (document redirect).
    ("spa-teams", "/teams", "Bare /teams → Django Team Launcher (redirect)"),
    ("spa-blueprints", "/blueprints", "Bare /blueprints → Django Blueprint Library (redirect)"),
    ("spa-settings", "/settings", "Bare /settings → Django Settings Dashboard (redirect)"),
    ("spa-agent-creator", "/agent-creator", "Bare /agent-creator → Django Agent Creator (redirect)"),
    ("login", "/accounts/login/", "Login page"),
    ("teams", "/teams/", "Teams admin / registry (Django)"),
    ("teams-launch", "/teams/launch/", "Team launcher (Django)"),
    ("blueprint-library", "/blueprint-library/", "Blueprint library (Django)"),
    ("my-blueprints", "/blueprint-library/my-blueprints/", "My blueprints (Django)"),
    ("agent-creator", "/agent-creator/", "Agent creator (Django)"),
    ("settings", "/settings/", "Settings dashboard (Django)"),
    ("sessions", "/sessions/", "Session explorer (Django)"),
    ("profiles", "/profiles/", "LLM profiles (Django)"),
]

SERVER_ENV = {
    "DJANGO_DEBUG": "true",       # dev mode; also relaxes SECRET_KEY requirement
    "ENABLE_WEBUI": "true",       # /teams/ et al. 404 without this
    "DJANGO_SECRET_KEY": os.environ.get("DJANGO_SECRET_KEY", "journey-capture-secret"),
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
    "SWARM_TEST_MODE": "1",
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
            screenshot_dir: Path) -> dict:
    """Visit path, screenshot, return a manifest entry."""
    entry: dict = {
        "stem": slug,
        "path": path,
        "name": name,
        "ok": False,
    }
    url = BASE_URL + path
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    status = response.status if response else 0
    entry["status"] = status
    if status >= 400:
        entry["error"] = f"HTTP {status}"
        return entry
    # Follow a login redirect if auth hardening kicked in.
    if "login" in page.url and path not in ("/accounts/login/", "/login/"):
        if login_if_needed(page):
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else 0
            entry["status"] = status
            if status >= 400 or "login" in page.url:
                entry["error"] = f"auth-blocked (HTTP {status})"
                return entry
        else:
            entry["error"] = "redirected to login; no login form found"
            return entry
    # Let the SPA / async widgets settle.
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # busy pages (polling) never go idle; capture anyway
    page.wait_for_timeout(750)
    final_url = page.url
    entry["final_url"] = final_url
    # Compare path only (keep trailing-slash differences): /settings → /settings/
    # is still a redirect for bare SPA entry documentation.
    from urllib.parse import urlparse

    final_path = urlparse(final_url).path or "/"
    entry["redirected"] = final_path != path and path not in (
        "/accounts/login/",
        "/login/",
    )
    try:
        entry["title"] = page.title()
        entry["body_snip"] = page.locator("body").inner_text(timeout=5000)[:350].replace("\n", " ")
        entry["nav_sample"] = [
            t.strip()
            for t in page.locator("nav a, .navbar a, .os-bottom-nav a").all_inner_texts()
            if t.strip()
        ][:16]
    except Exception as exc:
        entry["dom_error"] = str(exc)
    # When this slug documents a bare SPA path that redirected, inject a
    # capture-only banner so spa-*.png is not a pixel twin of the canonical page.
    if entry.get("redirected") and slug.startswith("spa-"):
        try:
            from_path = path
            to_path = final_url.replace(BASE_URL, "") or final_url
            page.evaluate(
                """([fromPath, toPath]) => {
                  if (document.getElementById('os-capture-redirect-banner')) return;
                  const b = document.createElement('div');
                  b.id = 'os-capture-redirect-banner';
                  b.setAttribute('role', 'status');
                  b.style.cssText = [
                    'position:sticky','top:0','z-index:2000','padding:0.55rem 1rem',
                    'background:#1e3a5f','color:#e2e8f0','font:600 0.9rem/1.35 system-ui,sans-serif',
                    'border-bottom:2px solid #3b82f6','box-shadow:0 4px 12px rgba(0,0,0,.35)'
                  ].join(';');
                  b.textContent = 'Redirected: ' + fromPath + ' → ' + toPath
                    + '  ·  canonical Django operator UI (bare SPA path is not a separate product)';
                  const main = document.querySelector('main.os-main, main, body');
                  if (main && main.firstChild) main.insertBefore(b, main.firstChild);
                  else document.body.insertBefore(b, document.body.firstChild);
                }""",
                [from_path, to_path],
            )
        except Exception:
            pass

    # Full-page PNGs paint *fixed* bottom bars over content in Chromium stitch
    # (Django `.os-bottom-nav` and SPA `nav.fixed.bottom-0` / Daisy dock).
    # Park them as static at document end so mid-page metrics/CTAs stay readable.
    try:
        page.evaluate(
            """() => {
              const nodes = document.querySelectorAll(
                '.os-bottom-nav, nav.fixed.bottom-0, nav[class*="fixed"][class*="bottom-0"]'
              );
              nodes.forEach((n) => {
                n.style.position = 'static';
                n.style.boxShadow = 'none';
                n.style.inset = 'auto';
              });
              document.body.style.paddingBottom = '0';
              const app = document.querySelector('.min-h-screen.pb-20, .min-h-screen');
              if (app && app.classList) {
                app.classList.remove('pb-20');
                app.style.paddingBottom = '0';
              }
            }"""
        )
    except Exception:
        pass
    out = screenshot_dir / f"{slug}.png"
    page.screenshot(path=str(out), full_page=True)
    entry["ok"] = True
    entry["screenshot"] = str(out.relative_to(REPO_ROOT))
    entry["bytes"] = out.stat().st_size if out.is_file() else 0
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mobile", action="store_true",
        help="emulate an iPhone-14 class device (390x844, dpr 2, touch) and "
             "write captures to docs/screenshots/mobile/ instead",
    )
    parser.add_argument(
        "--manifest",
        default=os.environ.get("CAPTURE_MANIFEST", ""),
        help="write JSON capture manifest to this path (or set CAPTURE_MANIFEST)",
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
    entries: list[dict] = []
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
                    entry = capture(page, slug, path, name, screenshot_dir)
                except Exception as exc:  # never let one page kill the run
                    entry = {
                        "stem": slug,
                        "path": path,
                        "name": name,
                        "ok": False,
                        "error": f"error: {exc}",
                    }
                entries.append(entry)
                if entry.get("ok"):
                    detail = entry.get("screenshot", "")
                    captured.append((name, detail))
                    redir = f" -> {entry.get('final_url', '')}" if entry.get("redirected") else ""
                    print(f"  [captured] {name:40s} {path}{redir} -> {detail}")
                else:
                    detail = entry.get("error", "unknown")
                    skipped.append((f"{name} ({path})", detail))
                    print(f"  [skipped ] {name:40s} {path} -- {detail}")
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        print("Django dev server stopped.")

    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "base": BASE_URL,
            "port": PORT,
            "mobile": bool(args.mobile),
            "viewport": context_kwargs.get("viewport"),
            "pages": entries,
            "captured": len(captured),
            "skipped": len(skipped),
        }
        # Merge desktop+mobile into one file if both runs share a path.
        if manifest_path.is_file():
            try:
                prev = json.loads(manifest_path.read_text())
                key = "mobile" if args.mobile else "desktop"
                other = "desktop" if args.mobile else "mobile"
                merged = {
                    "base": BASE_URL,
                    key: report,
                    other: prev.get(other) or prev if other in prev or "pages" in prev else prev,
                }
                # If prev is a single-run report with pages, nest it.
                if "pages" in prev and key not in prev:
                    merged[other] = prev
                manifest_path.write_text(json.dumps(merged, indent=2))
            except Exception:
                manifest_path.write_text(json.dumps({"desktop" if not args.mobile else "mobile": report}, indent=2))
        else:
            key = "mobile" if args.mobile else "desktop"
            manifest_path.write_text(json.dumps({key: report}, indent=2))
        print(f"Manifest written to {manifest_path}")

    print(f"\nSummary: {len(captured)} captured, {len(skipped)} skipped")
    for name, detail in skipped:
        print(f"  skipped: {name} -- {detail}")
    return 0 if not skipped else 1


if __name__ == "__main__":
    sys.exit(main())
