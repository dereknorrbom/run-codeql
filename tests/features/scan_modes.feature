Feature: Scan modes
  As an AI agent running CodeQL locally,
  I want to control which query suite is used for a scan,
  So that I can get consistent, reproducible findings regardless of repo config.

  Scenario: Default mode uses repo config query selector
    Given a repo config that selects the "code-quality" query suite
    When I run a Python scan in default mode
    Then the SARIF report is named "python-code-quality.sarif"

  Scenario: standard-findings mode ignores repo config and forces code-quality
    Given a repo config that selects the "security-and-quality" query suite
    When I run a Python scan in standard-findings mode
    Then the SARIF report is named "python-code-quality.sarif"
    And the database create command does not include "--codescanning-config"
    And the analyze command uses suite "codeql/python-queries:codeql-suites/python-code-quality.qls"

  Scenario: Default mode resolves security-and-quality suite when no config exists
    Given no repo config file exists
    When I run a Python scan in default mode
    Then the analyze command uses suite "codeql/python-queries:codeql-suites/python-security-and-quality.qls"
