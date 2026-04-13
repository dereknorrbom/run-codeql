Feature: Repository configuration
  As an AI agent working in a repo with a .rcql.json config,
  I want rcql to honour the repo config as a baseline
  and let CLI flags override it,
  So that repo-level defaults don't require flags on every invocation.

  Scenario: Repo config files filter is applied automatically
    Given a Python SARIF report with findings exists
    And the repo config sets files to "src/utils.py"
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "Shown: 2"
    And stdout contains "matched: 2"

  Scenario: CLI --files overrides repo config files filter
    Given a Python SARIF report with findings exists
    And the repo config sets files to "src/db.py"
    When I run rcql with "--report-only --no-fail --files src/utils.py"
    Then stdout contains "Shown: 2"
    And stdout contains "matched: 2"

  Scenario: Repo config exclude_files is applied automatically
    Given a SARIF report exists with findings in "src/app.py" and "src/generated/foo.py"
    And the repo config sets exclude_files to "src/generated/**"
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "Total: 1"

  Scenario: Repo config include_third_party opt-in
    Given a SARIF report exists with findings in "src/app.py" and "node_modules/pkg/index.py"
    And the repo config sets include_third_party to true
    When I run rcql with "--report-only --no-fail"
    Then stdout contains "Total: 2"

  Scenario: Missing config file is silently ignored
    Given no repo config file exists
    And a Python SARIF report with findings exists
    When I run rcql with "--report-only --no-fail"
    Then the exit code is zero
    And stdout contains "[python]"

  Scenario: --config empty string disables config loading
    Given a Python SARIF report with findings exists
    And the repo config sets files to "src/db.py"
    When I run rcql with "--report-only --no-fail --config ''"
    Then stdout contains "Total: 3"
