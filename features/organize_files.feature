Feature: File Organization Core Functionality
  As a user,
  I want the organizer to move files by extension
  So that I can clean up my messy folder

  Scenario: A single file is moved to its correct category
    Given a file of type "pdf" exists in the source directory
    When the organizer is run
    Then the "Documents" folder should exist
    And the "pdf" file should be in the "Documents" folder

Scenario: A dry run execution does not move files
    Given a file of type "pdf" exists in the source directory
    When the organizer is run with the "--dry-run" flag(s)
    Then the "Documents" folder should not exist
    And the "pdf" file should be in the source directory
    