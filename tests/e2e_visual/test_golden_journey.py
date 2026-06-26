import pytest

pytestmark = pytest.mark.e2e_visual
# NOTE: these tests execute against the built React app served by Django,
# checking the final artifact (including compiled CSS/assets), NOT the Vite dev server.


TRANSPARENT = (
    "rgba(0, 0, 0, 0)",
    "transparent",
    "rgba(0,0,0,0)",
)


# The empty-CSS guard: the healthy bundle is ~100kB; the Tailwind v4
# misconfiguration shipped ~2kB. Anything under this is utilities-free.
MIN_CSS_BYTES = 50_000


def _computed(page, locator, prop: str) -> str:
    return locator.evaluate(f"el => getComputedStyle(el)['{prop}']")


def test_landing_page_is_styled(page, live_server_url):
    page.goto(live_server_url + "/", wait_until="networkidle")

    # Browser-default rendering means the stylesheet never applied.
    font = _computed(page, page.locator("body"), "fontFamily")
    assert "times" not in font.lower() and font.lower() != "serif", (
        f"body font-family is the browser serif default ({font!r}); "
        "the built CSS is not applying"
    )

    btn = page.locator(".btn-primary").first
    btn.wait_for(state="visible", timeout=10_000)
    bg = _computed(page, btn, "backgroundColor")
    assert bg not in TRANSPARENT, (
        ".btn-primary has a transparent background; DaisyUI component "
        "styles are missing from the bundle"
    )

    css_files = [r.url for r in page.request.sizes if ".css" in r.url]
    assert css_files, "No CSS files were downloaded by the browser"

    # In production/Playwright, Vite chunks this to exactly 1 CSS file.
    css_url = css_files[0]
    resp = page.request.get(css_url)
    assert resp.ok, f"Failed to download compiled CSS: {resp.status}"

    size = len(resp.body())
    assert size > MIN_CSS_BYTES, (
        f"The compiled CSS bundle is suspiciously small ({size} bytes). "
        "The Tailwind v4 extractor probably failed to see the React source files."
    )


def test_login_with_throwaway_superuser(browser, live_server_url, auth_state):
    """The throwaway auth-state guard: ensures that the auto-login works
    and that it persists into the frontend's Context provider."""
    # Spin up an isolated context seeded with the pre-authenticated cookies
    context = browser.new_context(storage_state=auth_state)
    page = context.new_page()

    page.goto(live_server_url + "/settings", wait_until="networkidle")

    assert "login" not in page.url, "Auto-authenticated session redirected to login"

    btn = page.locator("text=API configuration")
    btn.wait_for(state="visible", timeout=10_000)


def test_chat_websocket_connects(page, live_server_url):
    """The ASGI plumbing guard: ensures Daphne/Channels are properly hooked up
    and that the frontend can establish the wss:// connection."""
    messages = []
    page.on("console", lambda msg: messages.append(msg.text))

    page.goto(live_server_url + "/chat", wait_until="networkidle")
    badge = page.locator(".badge-success", has_text="Connected")
    badge.wait_for(state="visible", timeout=5000)


def test_blueprint_cards_have_borders(page, live_server_url):
    """The card-bordered guard: DaisyUI 5 renamed ``card-bordered`` to
    ``card-border``; with the stale class the cards rendered borderless."""
    page.goto(live_server_url + "/blueprints", wait_until="networkidle")
    cards = page.locator(".card")
    cards.first.wait_for(state="visible", timeout=10_000)
    widths = []
    for i in range(cards.count()):
        w = _computed(page, cards.nth(i), "borderTopWidth")
        widths.append(w)

    # Check that at least one card has a visible border (>0px)
    has_border = any(w != "0px" for w in widths)
    assert has_border, f"No cards have top borders. Widths: {widths}"


def test_teams_navbar_has_no_zero_text_links(page, live_server_url):
    """The white-box guard: every visible navbar link on the Django-rendered
    /teams/ page must carry text, not render as an empty box."""
    page.goto(live_server_url + "/teams/", wait_until="domcontentloaded")
    assert "login" not in page.url, "/teams/ redirected to login despite auth"
    links = page.locator("nav a")
    count = links.count()
    assert count >= 3, f"expected a populated navbar on /teams/, found {count} links"
    empty = []
    for i in range(count):
        link = links.nth(i)
        if not link.inner_text().strip():
            empty.append(link.evaluate("el => el.outerHTML"))
    assert not empty, f"navbar has zero-text nav links: {empty}"


def test_dark_mode_toggle(page, live_server_url):
    """Clicking the toggle must flip the theme attribute AND visibly change
    the themed background — proving the DaisyUI theme CSS was compiled in.

    Note: this SPA carries ``data-theme`` on the app root <div> (App.tsx),
    not on documentElement, so assert on the actual attribute carrier.
    """
    page.goto(live_server_url + "/", wait_until="networkidle")
    themed = page.locator("[data-theme]").first
    themed.wait_for(state="attached", timeout=10_000)

    theme_before = themed.get_attribute("data-theme")
    bg_before = _computed(page, themed, "backgroundColor")

    # Use a robust attribute selector with .first to avoid strict mode violations
    # since aria-label maps to both the parent label and its internal checkbox
    page.locator('[aria-label="Toggle dark mode"]').first.click(force=True)
    page.wait_for_timeout(250)  # let React re-render + CSS vars resolve

    theme_after = themed.get_attribute("data-theme")
    bg_after = _computed(page, themed, "backgroundColor")

    assert theme_after != theme_before, (
        f"data-theme did not change on toggle (still {theme_after!r})"
    )
    assert bg_after != bg_before, (
        f"theme attribute flipped to {theme_after!r} but background stayed "
        f"the same ({bg_before!r})"
    )
