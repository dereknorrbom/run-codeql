Feature: CLI output modes
  As an AI agent consuming rcql output,
  I want predictable stdout/stderr output and exit codes,
  So that I can reliably parse results and decide next steps.

  Scenario: Report-only with findings exits non-zero
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only"
    Then the exit code is non-zero

  Scenario: Report-only with no findings exits zero
    Given an empty Python SARIF report exists
    When I run rcql with "--report-only"
    Then the exit code is zero

  Scenario: --no-fail forces exit zero even with findings
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail"
    Then the exit code is zero

  Scenario: Report-only output includes language block
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "[python]"

  Scenario: Report-only output includes finding count
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "Total: 3"

  Scenario: Verbose mode includes rule IDs
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --verbose --no-fail"
    Then stdout contains "py/sql-injection"

  Scenario: Quiet mode suppresses log lines from stdout
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --quiet --no-fail"
    Then stdout does not contain "[codeql-local]"

  Scenario: Quiet mode prints mode message to stderr
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --quiet --no-fail"
    Then stderr contains "quiet mode"

  Scenario: Missing SARIF reports exit non-zero with helpful message
    Given no SARIF reports exist
    When I run rcql with "--report-only"
    Then the exit code is non-zero
    And stderr contains "No SARIF files found"

  Scenario: --lang filter shows only requested language
    Given a Python SARIF report with findings exists
    And an empty Rust SARIF report exists
    When I run rcql with "--report-only --lang=python --no-fail"
    Then stdout contains "[python]"
    And stdout does not contain "[rust]"
