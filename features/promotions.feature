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
