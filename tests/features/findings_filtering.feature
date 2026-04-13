Feature: Findings filtering
  As an AI agent using rcql to investigate specific files or rules,
  I want to filter findings by file path, rule ID, and pagination,
  So that I can retrieve exactly the findings relevant to my current task.

  Scenario: --files filters to matching path
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --files src/db.py"
    Then stdout contains "Shown: 1"
    And stdout contains "matched: 1"

  Scenario: --files with glob matches multiple paths
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --files src/*.py"
    Then stdout contains "Shown: 3"

  Scenario: --files with no match suppresses language block
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --files nonexistent.py"
    Then stdout does not contain "[python]"

  Scenario: --rule filters to matching rule ID
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --rule py/unused-import"
    Then stdout contains "Shown: 2"
    And stdout contains "matched: 2"

  Scenario: --rule with glob matches all rules for a language
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --rule py/*"
    Then stdout contains "Shown: 3"

  Scenario: --rule with no match suppresses language block
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --rule js/something"
    Then stdout does not contain "[python]"

  Scenario: --files and --rule combined filter findings
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --files src/utils.py --rule py/unused-import"
    Then stdout contains "Shown: 2"

  Scenario: --limit caps the number of shown findings
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --limit 1"
    Then stdout contains "Shown: 1"
    And stdout contains "matched: 3"

  Scenario: --offset skips leading findings
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --offset 2"
    Then stdout contains "Shown: 1"
    And stdout contains "matched: 3"

  Scenario: Pagination - page one
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --limit 2 --offset 0"
    Then stdout contains "Shown: 2"
    And stdout contains "matched: 3"

  Scenario: Pagination - page two
    Given a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail --limit 2 --offset 2"
    Then stdout contains "Shown: 1"
    And stdout contains "matched: 3"

  Scenario: Default excludes suppress node_modules findings
    Given a SARIF report exists with findings in "src/app.py" and "app/node_modules/pkg/index.py"
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "Total: 1"
    And stdout does not contain "node_modules"

  Scenario: --include-third-party restores suppressed paths
    Given a SARIF report exists with findings in "src/app.py" and "node_modules/pkg/index.py"
    When I run rcql with "--report-only --no-fail --include-third-party"
    Then stdout contains "Total: 2"

  Scenario: --exclude-files hides matching paths
    Given a SARIF report exists with findings in "src/app.py" and "src/generated/foo.py"
    When I run rcql with "--report-only --no-fail --exclude-files src/generated/**"
    Then stdout contains "Total: 1"
