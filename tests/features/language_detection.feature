Feature: Language detection
  As an AI agent running rcql on a repository,
  I want rcql to automatically detect which languages are present,
  So that I don't need to know the repo's tech stack in advance.

  Scenario: Detects Python from .py files
    Given the repo contains "src/main.py"
    When I run language detection
    Then the detected languages include "python"

  Scenario: Detects Rust from .rs files
    Given the repo contains "src/main.rs"
    When I run language detection
    Then the detected languages include "rust"

  Scenario: Detects JavaScript/TypeScript from .ts files
    Given the repo contains "src/index.ts"
    When I run language detection
    Then the detected languages include "javascript-typescript"

  Scenario: Detects multiple languages
    Given the repo contains "app.py"
    And the repo contains "main.rs"
    When I run language detection
    Then the detected languages include "python"
    And the detected languages include "rust"

  Scenario: Detects GitHub Actions from workflow files
    Given the repo contains ".github/workflows/ci.yml"
    When I run language detection
    Then the detected languages include "actions"

  Scenario: Does not detect Actions without workflow directory
    Given the repo contains "src/app.py"
    When I run language detection
    Then the detected languages do not include "actions"

  Scenario: Ignores files inside node_modules
    Given the repo contains "node_modules/lib/index.js"
    And the repo contains "src/app.py"
    When I run language detection
    Then the detected languages include "python"
    And the detected languages do not include "javascript-typescript"

  Scenario: Empty repo detects no languages
    Given the repo is empty
    When I run language detection
    Then no languages are detected

  Scenario: Unknown file extensions are ignored
    Given the repo contains "README.md"
    And the repo contains "data.csv"
    When I run language detection
    Then no languages are detected

  Scenario: Detection results are sorted alphabetically
    Given the repo contains "a.rs"
    And the repo contains "b.py"
    And the repo contains "c.go"
    When I run language detection
    Then the detected languages are sorted alphabetically
