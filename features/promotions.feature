# features/promotions.feature
Feature: Promotions Admin UI bootstrap
  As a service administrator
  I want a working BDD harness that drives the UI only
  So that I can validate the service behavior from the outside-in

  Background:
    Given the Promotions UI is available

  Scenario: UI smoke (open /ui and see the title)
    Then the page title contains "Promotions Admin"

  Scenario: Create a promotion
    When I create a promotion with:
      | name           | SpringSale  |
      | promotion_type | PERCENT     |
      | value          | 10          |
      | product_id     | 1001        |
      | start_date     | 2025-01-01  |
      | end_date       | 2025-12-31  |
    Then the status shows "Created id="
    And the results contain a row with name "SpringSale"
