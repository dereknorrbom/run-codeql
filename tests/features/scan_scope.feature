Feature: Scan scope filtering
  As a developer iterating on a small set of files,
  I want rcql to optionally limit scan inputs to specific paths,
  So that local scans run faster than full-repo analysis.

  Scenario: --scan-files limits source inputs for analysis
    Given a repository with Python files in "src/app.py" and "src/other.py"
    When I run rcql with "--scan-files src/app.py --no-fail"
    Then the analyzer source root includes only "src/app.py"
    And the analyzer source root excludes "src/other.py"

  Scenario: --scan-files fails when nothing matches
    Given an empty repository
    When I run rcql with "--scan-files src/missing.py --no-fail"
    Then the exit code is non-zero
    And stderr contains "No files matched --scan-files patterns"

  Scenario: --scan-files cannot be combined with --report-only
    Given an empty repository
    When I run rcql with "--scan-files src/app.py --report-only"
    Then the exit code is non-zero
    And stderr contains "--scan-files cannot be used with --report-only"
