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
    # First wait for flash_message element to be present
    element = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, "flash_message"))
    )

    # Wait for the message to change from initial "Ready..." state
    import time
    time.sleep(0.5)  # Give AJAX time to complete

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
    """Fill the create form with data from table (horizontal format with headers)"""
    import time

    # Map column headers to input IDs in the v2 modal
    field_map = {
        'Name':            'inputName',
        'Promotion Type':  'inputType',
        'Value':           'inputValue',
        'Product ID':      'inputProductId',
        'Start Date':      'inputStart',
        'End Date':        'inputEnd'
    }

    # Process the first (and typically only) data row
    for row in context.table:
        for header in context.table.headings:
            element_id = field_map.get(header)
            if not element_id:
                raise AssertionError(f"Unknown field header: {header}")

            field_value = row[header]
            element = WebDriverWait(context.browser, context.wait_seconds).until(
                expected_conditions.presence_of_element_located((By.ID, element_id))
            )

            # Handle different field types
            if header == 'Promotion Type':
                # Use Select for dropdown
                select = Select(element)
                select.select_by_value(field_value)
            elif header in ['Start Date', 'End Date']:
                # For date inputs, use JavaScript to set value directly
                context.browser.execute_script(
                    "arguments[0].value = arguments[1];", element, field_value
                )
            else:
                # For text and number inputs, use standard clear + send_keys
                element.clear()
                element.send_keys(field_value)

            time.sleep(0.1)


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


##################################################################
# V2 Delete Steps
##################################################################


@when('I click the delete button for "{name}"')
def step_impl(context: Any, name: str) -> None:
    """Click the delete button for a specific promotion by name"""
    import time

    # Find all delete buttons
    delete_buttons = context.browser.find_elements(By.CLASS_NAME, "delete-btn")

    # Find the button with matching name in data-name attribute
    for button in delete_buttons:
        button_name = button.get_attribute("data-name")
        if button_name == name:
            # Scroll element into view before clicking
            context.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(0.3)  # Wait for scroll to complete
            button.click()
            time.sleep(0.5)  # Wait for modal to appear
            return

    raise AssertionError(f"Delete button for '{name}' not found")


@then('I should see the delete confirmation modal')
def step_impl(context: Any) -> None:
    """Verify the delete confirmation modal is visible"""
    modal = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.visibility_of_element_located((By.ID, "deleteModal"))
    )
    assert modal.is_displayed(), "Delete confirmation modal is not visible"

    # Verify the modal shows the correct promotion name
    modal_name = context.browser.find_element(By.ID, "deletePromotionName").text
    logging.info(f"Delete modal is showing for: {modal_name}")


@when('I confirm the deletion')
def step_impl(context: Any) -> None:
    """Click the confirm delete button in the modal"""
    import time

    confirm_button = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.element_to_be_clickable((By.ID, "confirmDelete"))
    )
    confirm_button.click()

    # Wait for modal to close
    WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.invisibility_of_element_located((By.ID, "deleteModal"))
    )

    # Wait for table to update
    time.sleep(1.0)


@then('I should not see "{name}" in the promotions table')
def step_impl(context: Any, name: str) -> None:
    """Verify the promotion is no longer in the table"""
    import time
    time.sleep(0.5)  # Give table time to update

    table = context.browser.find_element(By.ID, "promotions_table")
    table_text = table.text

    assert name not in table_text, f"Promotion '{name}' is still visible in the table"


##################################################################
# V2 Edit Steps
##################################################################


@when('I click the edit button for "{name}"')
def step_impl(context: Any, name: str) -> None:
    """Click the edit button for a specific promotion by name"""
    import time

    # Find all edit buttons
    edit_buttons = context.browser.find_elements(By.CLASS_NAME, "edit-btn")

    # Find the button with matching promotion data
    for button in edit_buttons:
        promotion_json = button.get_attribute("data-promotion")
        if promotion_json:
            import json
            try:
                promotion = json.loads(promotion_json)
                if promotion.get('name') == name:
                    # Scroll element into view before clicking
                    context.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.3)  # Wait for scroll to complete
                    button.click()
                    time.sleep(0.5)  # Wait for modal to appear
                    return
            except json.JSONDecodeError:
                continue

    raise AssertionError(f"Edit button for '{name}' not found")


@then('I should see the edit modal')
def step_impl(context: Any) -> None:
    """Verify the edit modal is visible"""
    modal = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.visibility_of_element_located((By.ID, "editModal"))
    )
    assert modal.is_displayed(), "Edit modal is not visible"

    # Verify the modal has the correct title
    modal_title = context.browser.find_element(By.ID, "editModalLabel").text
    logging.info(f"Edit modal is showing with title: {modal_title}")


@when('I fill the edit form with:')
def step_impl(context: Any) -> None:
    """Fill the edit form with data from table (key-value pairs)"""

    # Map field names to input IDs in the v2 edit modal
    field_map = {
        'name': 'editName',
        'promotion_type': 'editType',
        'value': 'editValue',
        'product_id': 'editProductId',
        'start_date': 'editStart',
        'end_date': 'editEnd'
    }

    for row in context.table:
        
        # Now, iterate over all the HEADERS from the Gherkin table
        for header in context.table.headings:
            
            # 1. Normalize the header to match the field_map keys
            #    e.g., "Promotion Type" -> "promotion_type"
            field_key = header.lower().replace(' ', '_')

            # 2. Get the value from the current row using the header
            #    e.g., row["Promotion Type"] -> "PERCENT"
            field_value = row[header]
            
            # 3. Find the corresponding element ID from our map
            element_id = field_map.get(field_key)

            if not element_id:
                raise AssertionError(f"Unknown field: Gherkin header '{header}' (normalized to '{field_key}') not in field_map")

            # 4. Find the element
            element = WebDriverWait(context.browser, context.wait_seconds).until(
                expected_conditions.presence_of_element_located((By.ID, element_id))
            )

            # 5. Fill the element using the robust methods
            if field_key == 'promotion_type':
                # Use Select for dropdown
                select = Select(element)
                select.select_by_value(field_value)
            else:
                # Use JavaScript to set value for all text/date/number fields
                # This is much more reliable than element.clear() + send_keys()
                context.browser.execute_script(
                    "arguments[0].value = arguments[1];", element, field_value
                )


@when('I submit the edit form')
def step_impl(context: Any) -> None:
    """Submit the edit form"""
    submit_button = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.element_to_be_clickable((By.ID, "editSubmit"))
    )
    submit_button.click()

    # Wait for the modal to disappear
    modal_element = context.browser.find_element(By.ID, "editModal")
    WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.invisibility_of_element(modal_element)
    )


##################################################################
# V2 Filter Steps
##################################################################


@when('I click the "{text}" filter pill')
def step_impl(context: Any, text: str) -> None:
    """Click a filter pill by text"""
    import time

    # Find all filter pills
    pills = context.browser.find_elements(By.CLASS_NAME, "filter-pill")

    for pill in pills:
        if pill.text.strip() == text:
            pill.click()
            time.sleep(0.5)  # Wait for filter to apply
            return

    raise AssertionError(f"Filter pill '{text}' not found")


@when('I search for "{text}"')
def step_impl(context: Any, text: str) -> None:
    """Enter text in the search box"""
    import time

    search_input = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, "searchInput"))
    )
    search_input.clear()
    search_input.send_keys(text)

    # Wait for debounce and filter to apply
    time.sleep(0.5)


@when('I select "{value}" in the Type filter')
def step_impl(context: Any, value: str) -> None:
    """Select a value in the Type dropdown"""
    import time

    type_select = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, "filterType"))
    )
    select = Select(type_select)
    select.select_by_value(value)

    # Wait for filter to apply
    time.sleep(0.5)


@when('I filter by product ID "{product_id}"')
def step_impl(context: Any, product_id: str) -> None:
    """Enter product ID in the filter input"""
    import time

    product_input = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, "filterProductId"))
    )
    product_input.clear()
    product_input.send_keys(product_id)

    # Wait for debounce and filter to apply
    time.sleep(0.5)


@when('I click the Clear filters button')
def step_impl(context: Any) -> None:
    """Click the Clear filters button"""
    import time

    clear_button = WebDriverWait(context.browser, context.wait_seconds).until(
        expected_conditions.element_to_be_clickable((By.ID, "btnClearFilters"))
    )
    clear_button.click()

    # Wait for filters to clear
    time.sleep(0.5)


@then('the URL should contain "{text}"')
def step_impl(context: Any, text: str) -> None:
    """Verify the URL contains specific text"""
    import time
    time.sleep(0.3)  # Give URL time to update

    current_url = context.browser.current_url
    assert text in current_url, f"Expected URL to contain '{text}', but got: {current_url}"


@then('the URL should not contain parameters')
def step_impl(context: Any) -> None:
    """Verify the URL does not contain query parameters"""
    import time
    time.sleep(0.3)  # Give URL time to update

    current_url = context.browser.current_url
    assert '?' not in current_url, f"Expected URL without parameters, but got: {current_url}"
