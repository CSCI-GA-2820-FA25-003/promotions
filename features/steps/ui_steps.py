"""Step definitions for the Admin UI BDD tests.

All interactions are performed via the browser (Selenium) against the UI
at /ui. No direct API calls are made in these steps, satisfying R4.
"""

import time
from behave import given, when, then
from selenium.webdriver.common.by import By


def _status_text(context) -> str:
    """Return the text content of the #status banner."""
    return context.browser.find_element(By.ID, "status").text


def _table_html(context) -> str:
    """Return the outerHTML of the #results table for simple assertions."""
    return context.browser.find_element(By.ID, "results").get_attribute("outerHTML")


def _table_to_dict(table) -> dict:
    """Convert a 2-column Gherkin table to a dictionary."""
    data = {}
    for row in table.rows:
        key = row.cells[0].strip()
        val = row.cells[1].strip()
        data[key] = val
    return data


def _wait_until(predicate, timeout=2.5, interval=0.1):
    """Poll predicate() until True or timeout, return bool."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


@given("the Promotions UI is available")
def step_ui_is_available(context):
    """Navigate to the /ui page and ensure basic content is present."""
    context.browser.get(context.base_url + "/ui")
    title = context.browser.title or ""
    page = context.browser.page_source or ""
    assert "Promotions Admin" in title or "Promotions Admin" in page


@then('the page title contains "{text}"')
def step_title_contains(context, text):
    """Assert document.title contains the expected text and H1 matches."""
    assert text in (context.browser.title or "")
    h1 = context.browser.find_element(By.ID, "title")
    assert text in h1.text


@when("I create a promotion with:")
def step_create_promotion(context):
    """Fill the Create form and submit via the UI."""
    data = _table_to_dict(context.table)
    b = context.browser
    b.find_element(By.ID, "c-name").clear()
    b.find_element(By.ID, "c-name").send_keys(data.get("name", ""))
    b.find_element(By.ID, "c-type").clear()
    b.find_element(By.ID, "c-type").send_keys(data.get("promotion_type", ""))
    b.find_element(By.ID, "c-value").clear()
    b.find_element(By.ID, "c-value").send_keys(data.get("value", ""))
    b.find_element(By.ID, "c-product").clear()
    b.find_element(By.ID, "c-product").send_keys(data.get("product_id", ""))
    b.find_element(By.ID, "c-start").clear()
    b.find_element(By.ID, "c-start").send_keys(data.get("start_date", ""))
    b.find_element(By.ID, "c-end").clear()
    b.find_element(By.ID, "c-end").send_keys(data.get("end_date", ""))
    b.find_element(By.ID, "btn-create").click()


@then('the status shows "{prefix}"')
def step_status_prefix(context, prefix):
    """Assert that the status banner starts with a specific prefix (with small wait)."""
    ok = _wait_until(lambda: _status_text(context).startswith(prefix), timeout=3.0, interval=0.1)
    assert ok, _status_text(context)


@then('the results contain a row with name "{name}"')
def step_results_has_name(context, name):
    """Assert that the results table contains the given name (with small wait)."""
    ok = _wait_until(lambda: name in _table_html(context), timeout=3.0, interval=0.1)
    assert ok, _table_html(context)
