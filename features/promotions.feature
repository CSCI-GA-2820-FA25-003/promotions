# features/promotions.feature
Feature: Promotions Admin UI
  As an eCommerce manager
  I want to manage promotions through a web interface
  So that I can create, update, and track promotional campaigns

  Scenario: Load the admin UI page
    When I visit the "Home Page"
    Then I should see "Promotions Admin" in the title

  Scenario: Create a promotion from the UI
    When I visit the "Home Page"
    And I set the "Name" to "SpringSale"
    And I set the "Promotion Type" to "PERCENT"
    And I set the "Value" to "10"
    And I set the "Product ID" to "1001"
    And I set the "Start Date" to "2025-01-01"
    And I set the "End Date" to "2025-12-31"
    And I press the "Create Promotion" button
    Then I should see the message "Success"
    And I should see "SpringSale" in the results

  Scenario: Delete a promotion from the UI
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Summer Sale | PERCENT        | 15    | 1002       | 2025-06-01 | 2025-08-31 |
    When I visit the "Home Page"
    And I retrieve the promotion named "Summer Sale"
    Then I should see "Summer Sale" in the "Name" field
    When I press the "Delete" button
    Then I should see the message "Promotion has been Deleted!"
    And I should not see "Summer Sale" in the results

  Scenario: Create a promotion from v2 modal
    Given the server is running
    When I go to "/v2"
    And I click "Create"
    And I fill the create form with:
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Winter Sale | PERCENT        | 50    | 9999       | 2030-11-12 | 2030-11-30 |
    And I submit the create form
    Then I should see the promotions table updated with "Winter Sale"

  Scenario: Delete a promotion from v2
    Given the following promotions
      | Name        | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Summer Sale | PERCENT        | 20    | 2001       | 2030-06-01 | 2030-08-31 |
    When I go to "/v2"
    Then I should see the promotions table updated with "Summer Sale"
    When I click the delete button for "Summer Sale"
    Then I should see the delete confirmation modal
    When I confirm the deletion
    Then I should not see "Summer Sale" in the promotions table

  Scenario: Edit a promotion from v2
    Given the following promotions
      | Name       | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Flash Sale | DISCOUNT       | 100   | 3001       | 2030-01-01 | 2030-01-31 |
    When I go to "/v2"
    Then I should see the promotions table updated with "Flash Sale"
    When I click the edit button for "Flash Sale"
    Then I should see the edit modal
    When I fill the edit form with:
      | Name               | Promotion Type | Value | Product ID | Start Date | End Date   |
      | Flash Sale Updated | PERCENT        | 25    | 3002       | 2030-02-01 | 2030-02-28 |
    And I submit the edit form
    Then I should see the promotions table updated with "Flash Sale Updated"
