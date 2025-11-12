######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

# pylint: disable=function-redefined, missing-function-docstring
# flake8: noqa
"""
Web Steps

Steps file for web interactions with Selenium

For information on Waiting until elements are present in the HTML see:
    https://selenium-python.readthedocs.io/waits.html
"""
import re
import logging
from typing import Any
from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions

# Default ID prefix (used if no specific resource is detected)
DEFAULT_PREFIX = "promotion_"


######################################################################
# Helper: get ID prefix dynamically
######################################################################
def get_prefix(context: Any) -> str:
    """
    Determine whether the current scenario is testing promotion.
    Always returns 'promotion_' prefix for promotions service.
    """
    return DEFAULT_PREFIX


def save_screenshot(context: Any, filename: str) -> None:
    """Takes a snapshot of the web page for debugging and validation

    Args:
        context (Any): The session context
        filename (str): The message that you are looking for
    """
    # Remove all non-word characters (everything except numbers and letters)
    filename = re.sub(r"[^\w\s]", "", filename)
    # Replace all runs of whitespace with a single dash
    filename = re.sub(r"\s+", "-", filename)
    context.browser.save_screenshot(f"./captures/{filename}.png")


import requests

@given('the following promotions')
def step_impl(context):
    """
    Loads the promotions into the database
    """
    headers = {'Content-Type': 'application/json'}
    for row in context.table:
        payload = {
            "name": row['Name'],
            "promotion_type": row['Promotion Type'],
            "value": int(row['Value']),
            "product_id": int(row['Product ID']),
            "start_date": row['Start Date'],
            "end_date": row['End Date']
        }
        context.resp = requests.post(context.base_url + '/promotions', json=payload, headers=headers)
        assert context.resp.status_code == 201

@when('I retrieve the promotion named "{name}"')
def step_impl(context, name):
    """
    Retrieves a promotion by name and populates the form
    """
    headers = {'Content-Type': 'application/json'}
    context.resp = requests.get(context.base_url + '/promotions', params={'name': name}, headers=headers)
    assert context.resp.status_code == 200
    data = context.resp.json()
    assert len(data) > 0
    promotion = data[0]

    # Populate the form
    context.browser.find_element(By.ID, "promotion_id").send_keys(promotion['id'])
    context.browser.find_element(By.ID, "promotion_name").send_keys(promotion['name'])
    context.browser.find_element(By.ID, "promotion_promotion_type").send_keys(promotion['promotion_type'])
    context.browser.find_element(By.ID, "promotion_value").send_keys(promotion['value'])
    context.browser.find_element(By.ID, "promotion_product_id").send_keys(promotion['product_id'])
    context.browser.find_element(By.ID, "promotion_start_date").send_keys(promotion['start_date'])
    context.browser.find_element(By.ID, "promotion_end_date").send_keys(promotion['end_date'])

@when('I visit the "Home Page"')
def step_impl(context: Any) -> None:
    """Make a call to the base URL"""
    context.browser.get(context.base_url)
    # Uncomment next line to take a screenshot of the web page
    # save_screenshot(context, 'Home Page')


@then('I should see "{message}" in the title')
def step_impl(context: Any, message: str) -> None:
    """Check the document title for a message"""
    assert message in context.browser.title


@then('I should not see "{text_string}"')
def step_impl(context: Any, text_string: str) -> None:
    element = context.browser.find_element(By.TAG_NAME, "body")
    assert text_string not in element.text


@when('I set the "{element_name}" to "{text_string}"')
def step_impl(context: Any, element_name: str, text_string: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = context.browser.find_element(By.ID, element_id)
    element.clear()
    element.send_keys(text_string)


@when('I select "{text}" in the "{element_name}" dropdown')
def step_impl(context: Any, text: str, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = Select(context.browser.find_element(By.ID, element_id))
    element.select_by_visible_text(text)


@then('I should see "{text}" in the "{element_name}" dropdown')
def step_impl(context: Any, text: str, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = Select(context.browser.find_element(By.ID, element_id))
    assert element.first_selected_option.text == text


@then('the "{element_name}" field should be empty')
def step_impl(context: Any, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = context.browser.find_element(By.ID, element_id)
    assert element.get_attribute("value") == ""


##################################################################
# These two function simulate copy and paste
##################################################################
@when('I copy the "{element_name}" field')
def step_impl(context: Any, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, element_id))
    )
    context.clipboard = element.get_attribute("value")
    logging.info("Clipboard contains: %s", context.clipboard)


@when('I paste the "{element_name}" field')
def step_impl(context: Any, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, element_id))
    )
    element.clear()
    element.send_keys(context.clipboard)


##################################################################
# This code works because of the following naming convention:
# The buttons have an id in the html hat is the button text
# in lowercase followed by '-btn' so the Clear button has an id of
# id='clear-btn'. That allows us to lowercase the name and add '-btn'
# to get the element id of any button
##################################################################


@when('I press the "{button}" button')
def step_impl(context: Any, button: str) -> None:
    button_id = button.lower().replace(" ", "_") + "-btn"
    context.browser.find_element(By.ID, button_id).click()


@then('I should see "{name}" in the results')
def step_impl(context: Any, name: str) -> None:
    found = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element(
            (By.ID, "search_results"), name
        )
    )
    assert found


@then('I should not see "{name}" in the results')
def step_impl(context: Any, name: str) -> None:
    element = context.browser.find_element(By.ID, "search_results")
    assert name not in element.text


@then('I should see the message "{message}"')
def step_impl(context: Any, message: str) -> None:
    # Uncomment next line to take a screenshot of the web page for debugging
    # save_screenshot(context, message)

    # First wait for flash_message element to be present
    element = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, "flash_message"))
    )

    # Wait for the message to change from initial "Ready..." state
    import time
    time.sleep(0.5)  # Give AJAX time to complete

    # Debug: print actual message
    actual_message = element.text
    logging.info(f"Expected: '{message}', Actual: '{actual_message}'")

    try:
        found = WebDriverWait(context.browser, context.wait_seconds).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "flash_message"), message
            )
        )
        assert found
    except Exception as e:
        # Print actual message for debugging
        actual = context.browser.find_element(By.ID, "flash_message").text
        raise AssertionError(f"Expected message '{message}' but got '{actual}'")


##################################################################
# This code works because of the following naming convention:
# The id field for text input in the html is the element name
# prefixed by ID_PREFIX so the Name field has an id='pet_name'
# We can then lowercase the name and prefix with pet_ to get the id
##################################################################


@then('I should see "{text_string}" in the "{element_name}" field')
def step_impl(context: Any, text_string: str, element_name: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")

    # Add debug screenshot
    # save_screenshot(context, f"before_checking_{element_name}")  # ADD THIS

    found = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element_value(
            (By.ID, element_id), text_string
        )
    )
    assert found


@when('I change "{element_name}" to "{text_string}"')
def step_impl(context: Any, element_name: str, text_string: str) -> None:
    prefix = get_prefix(context)
    element_id = prefix + element_name.lower().replace(" ", "_")
    element = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, element_id))
    )
    element.clear()
    element.send_keys(text_string)


##################################################################
# V2 Modal Steps for BDD Testing
##################################################################


@given('the server is running')
def step_impl(context: Any) -> None:
    """Verify the server is accessible"""
    import requests
    try:
        response = requests.get(context.base_url, timeout=5)
        assert response.status_code in [200, 404, 302]
    except Exception as e:
        raise AssertionError(f"Server is not running at {context.base_url}: {e}")


@when('I go to "{path}"')
def step_impl(context: Any, path: str) -> None:
    """Navigate to a specific path"""
    context.browser.get(context.base_url + path)
    # Wait for page to load
    import time
    time.sleep(0.5)


@when('I click "{button_text}"')
def step_impl(context: Any, button_text: str) -> None:
    """Click a button by its text content"""
    # Try to find button by text (case-insensitive)
    buttons = context.browser.find_elements(By.TAG_NAME, "button")
    for button in buttons:
        if button.text.strip().lower() == button_text.lower():
            button.click()
            import time
            time.sleep(0.3)  # Wait for modal to appear
            return
    raise AssertionError(f"Button with text '{button_text}' not found")


@when('I fill the create form with:')
def step_impl(context: Any) -> None:
    """Fill the create form with data from table (key-value pairs)"""

    # Map field names to input IDs in the v2 modal
    field_map = {
        'name': 'inputName',
        'promotion_type': 'inputType',
        'value': 'inputValue',
        'product_id': 'inputProductId',
        'start_date': 'inputStart',
        'end_date': 'inputEnd'
    }

    # The table is in key-value format without headers
    # In behave, the first row is treated as headers, so we need to process it as data too
    import time

    def fill_field(field_name: str, field_value: str) -> None:
        """Fill a form field using appropriate Selenium method"""
        element_id = field_map.get(field_name)
        if not element_id:
            raise AssertionError(f"Unknown field: {field_name}")

        element = WebDriverWait(context.browser, context.wait_seconds).until(
            expected_conditions.presence_of_element_located((By.ID, element_id))
        )

        # Handle different field types
        if field_name == 'promotion_type':
            # Use Select for dropdown
            select = Select(element)
            select.select_by_value(field_value)
        elif field_name in ['start_date', 'end_date']:
            # For date inputs, send keys directly (don't clear)
            element.send_keys(field_value)
        else:
            # For text and number inputs, use standard clear + send_keys
            element.clear()
            element.send_keys(field_value)

        time.sleep(0.1)

    # Process the header row as the first data row
    if context.table.headings:
        field_name = context.table.headings[0]
        field_value = context.table.headings[1]
        fill_field(field_name, field_value)

    # Process the rest of the rows
    for row in context.table:
        field_name = row[0]
        field_value = row[1]
        fill_field(field_name, field_value)


@when('I submit the create form')
def step_impl(context: Any) -> None:
    """Submit the create form"""
    submit_button = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.element_to_be_clickable((By.ID, "createSubmit"))
    )
    submit_button.click()

    # Wait for the modal to disappear
    modal_element = context.browser.find_element(By.ID, "createModal")
    WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.invisibility_of_element(modal_element)
    )


@then('I should see the promotions table updated with "{name}"')
def step_impl(context: Any, name: str) -> None:
    """Verify the promotion appears in the table"""
    # Wait for table to update
    found = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element(
            (By.ID, "promotions_table"), name
        )
    )
    assert found, f"Promotion '{name}' not found in table"
