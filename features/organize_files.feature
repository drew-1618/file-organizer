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

Scenario: File is moved and renamed with date modified prefixing
    Given a file of type "pdf" exists in the source directory
    When the organizer is run with the "--date-prefixing modified" flag(s)
    Then the "Documents" folder should exist
    And the file should be in the "Documents" folder with date "modified" prefixing
    
Scenario: File is moved and renamed with date created prefixing
    Given a file of type "pdf" exists in the source directory
    When the organizer is run with the "--date-prefixing created" flag(s)
    Then the "Documents" folder should exist
    And the file should be in the "Documents" folder with date "created" prefixing

Scenario: Multiple files of different types are moved to their correct categories
    Given a file of type "pdf" exists in the source directory
    And a file of type "jpg" exists in the source directory
    And a file of type "mp4" exists in the source directory
    When the organizer is run
    Then the "Documents" folder should exist
    And the "pdf" file should be in the "Documents" folder
    And the "Images" folder should exist
    And the "jpg" file should be in the "Images" folder
    And the "Videos" folder should exist
    And the "mp4" file should be in the "Videos" folder

Scenario: A file conflict is resolved by renaming the moved file
    Given a file of type "pdf" exists in the source directory
    And a "Documents" folder exists with a "pdf" file already in it
    When the organizer is run
    Then the "Documents" folder should exist
    And the "Documents" folder should contain two "pdf" files
