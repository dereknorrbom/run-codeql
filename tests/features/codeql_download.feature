Feature: CodeQL auto-download
  As a Windows developer running rcql locally,
  I want rcql to install the matching CodeQL CLI bundle automatically,
  So that I can scan repositories without manually installing CodeQL first.

  Scenario: Windows auto-download uses the Windows bundle and executable
    Given no CodeQL executable is already installed
    And the operating system is "Windows"
    When CodeQL is resolved for rcql
    Then the Windows CodeQL bundle is downloaded
    And the resolved CodeQL executable is "codeql.exe"
