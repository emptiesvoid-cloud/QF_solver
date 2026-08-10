from __future__ import annotations

import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest


pytestmark = pytest.mark.docs
ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
FORMULA_REGISTRY = ROOT / "qualification" / "formulas.json"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


@pytest.fixture(scope="module")
def site_url() -> str:
    if os.environ.get("QF_SOLVER_RUN_DOCS_UI") != "1":
        pytest.skip("Set QF_SOLVER_RUN_DOCS_UI=1 after building the MkDocs site.")
    assert (SITE / "index.html").is_file(), "Build the site before running browser checks."
    handler = functools.partial(QuietHandler, directory=str(SITE))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 900}, {"width": 390, "height": 844}])
def test_site_is_responsive_offline_and_typesets_formulas(site_url: str, viewport: dict[str, int]) -> None:
    playwright_api = pytest.importorskip("playwright.sync_api")
    console_errors: list[str] = []
    page_errors: list[str] = []
    remote_requests: list[str] = []
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=viewport)
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def inspect_request(request: object) -> None:
            url = request.url
            parsed = urlparse(url)
            if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost"}:
                remote_requests.append(url)

        page.on("request", inspect_request)
        page.goto(f"{site_url}/elements/tet4/", wait_until="networkidle")
        page.wait_for_selector("mjx-container", timeout=15_000)
        assert page.locator(".doc-control").count() == 1
        assert page.locator(".md-tabs__link").count() >= 8
        assert page.locator("img").count() >= 2
        assert page.eval_on_selector_all("img", "els => els.every(e => e.complete && e.naturalWidth > 50)")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert page.locator("main table").count() >= 1

        if viewport["width"] >= 800:
            page.get_by_label("Rechercher").click()
            search = page.locator("input.md-search__input")
            page.wait_for_timeout(300)
            search.fill("")
            search.press_sequentially("MITC4", delay=25)
            page.wait_for_selector(".md-search-result__item", state="attached", timeout=10_000)
            assert page.locator(".md-search-result__item").count() >= 1

        page.goto(f"{site_url}/demonstrations/dynamique/", wait_until="networkidle")
        assert page.locator("img").count() >= 2
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

        page.goto(f"{site_url}/demonstrations/benchmarks/cantilever/", wait_until="networkidle")
        assert page.locator("img").count() >= 3
        assert page.locator("main table").count() >= 2
        assert page.eval_on_selector_all(
            "img.result-figure",
            "els => els.length >= 3 && els.every(e => e.complete && e.naturalWidth > 300)",
        )
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

        page.goto(f"{site_url}/verification/formules/", wait_until="networkidle")
        assert page.locator("main table").count() >= 2
        formula_count = len(json.loads(FORMULA_REGISTRY.read_text(encoding="utf-8"))["formulas"])
        assert page.get_by_text(f"{formula_count}/{formula_count}", exact=True).count() >= 1
        assert page.get_by_text("BLOCKED", exact=True).count() >= 2
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()

    assert remote_requests == []
    assert page_errors == []
    assert console_errors == []
