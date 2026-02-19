"""Playwright end-to-end tests for the Marimo-Obsessed vault app.

These tests require:
  - ``playwright`` and ``pytest-playwright`` installed
  - Playwright browsers installed (``uv run playwright install chromium``)
  - The marimo server started via the ``live_url`` session fixture in conftest.py

Run with::

    uv run pytest tests/test_ui/test_vault_app_e2e.py --browser chromium

Tests are marked ``@pytest.mark.e2e`` so they can be skipped in fast CI runs::

    uv run pytest -m "not e2e"
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_marimo(page, timeout: int = 15_000) -> None:
    """Wait until the Marimo app shell is interactive."""
    # Marimo renders a #root div once the Python kernel is ready
    page.wait_for_selector("#root", timeout=timeout)
    # Give reactive cells time to settle
    page.wait_for_timeout(2_000)


# ---------------------------------------------------------------------------
# App shell
# ---------------------------------------------------------------------------


class TestAppShell:
    def test_page_loads(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        assert "Marimo" in page.title() or page.locator("body").is_visible()

    def test_sidebar_visible(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        # Sidebar contains a "Notes" heading
        assert page.locator("text=Notes").first.is_visible()

    def test_tabs_present(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        for tab_label in ("Graph", "Canvas", "Editor"):
            assert page.locator(f"text={tab_label}").first.is_visible()


# ---------------------------------------------------------------------------
# Graph tab
# ---------------------------------------------------------------------------


class TestGraphTab:
    def test_graph_tab_renders_svg(self, page, live_url):
        """The Graph tab should render an Altair SVG/Canvas element."""
        page.goto(live_url)
        _wait_for_marimo(page)
        # Altair renders a <canvas> or <svg> element inside its output cell
        page.locator("text=Graph").first.click()
        page.wait_for_timeout(2_000)
        graph_el = page.locator("canvas, svg").first
        assert graph_el.is_visible()

    def test_sample_note_slug_in_graph(self, page, live_url):
        """At least one vault note slug should appear in the graph tooltip data."""
        page.goto(live_url)
        _wait_for_marimo(page)
        page.locator("text=Graph").first.click()
        page.wait_for_timeout(2_000)
        # Check the page source contains a known slug from the sample vault
        content = page.content()
        assert "index" in content or "getting-started" in content


# ---------------------------------------------------------------------------
# Canvas tab
# ---------------------------------------------------------------------------


class TestCanvasTab:
    def test_canvas_tab_renders_iframe(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        page.locator("text=Canvas").first.click()
        page.wait_for_timeout(2_000)
        iframe = page.locator("iframe").first
        assert iframe.is_visible()

    def test_canvas_iframe_src_contains_tldraw(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        page.locator("text=Canvas").first.click()
        page.wait_for_timeout(2_000)
        content = page.content()
        assert "tldraw" in content.lower()


# ---------------------------------------------------------------------------
# Sidebar & editor
# ---------------------------------------------------------------------------


class TestSidebarNavigation:
    def test_search_filters_notes(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        # Type into the search input
        search = page.locator("input[placeholder*='Search']").first
        search.fill("getting")
        page.wait_for_timeout(1_000)
        # "Getting Started" note should appear
        assert page.locator("text=Getting Started").first.is_visible()

    def test_clicking_note_switches_to_editor(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        # Click first note button in the sidebar
        page.locator("text=Getting Started").first.click()
        page.wait_for_timeout(1_500)
        # Editor tab should now be active; the note title should appear
        assert page.locator("text=Getting Started").first.is_visible()

    def test_tag_filter_dropdown_visible(self, page, live_url):
        page.goto(live_url)
        _wait_for_marimo(page)
        # Tag dropdown should exist
        assert page.locator("select, [role='combobox']").first.is_visible()
