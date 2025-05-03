---
date: 2025-05-03
---
# Development Workflow
- User prefers creating project plans before implementation, dividing projects into phases with checklists in @docs/plans/ directory as markdown files with WHY/WHAT/HOW format.
- If the user ask a question, answer it without producing code. Especially when prefixed with 'QQ:', user wants analysis rather than implementation, documented in @docs/plans/.
- User prefers documenting implementation status in @docs/folib-planning/-status.md, planning next phases in @docs/folib-planning/-next.md, and documenting implementation differences in @docs/folib-planning/ directory.
- User prefers documenting implementation progress and differences in @docs/folib-planning/-handoff.md files and including test instructions in documentation.
- User is working on making folib calculations match the old folio implementation, with progress tracked in handoff documentation files.
- User prefers completing started work before moving to new tasks.
- User prefers focusing on one task at a time rather than working on multiple scripts simultaneously.
- Run `make lint` frequently to fix import declaration issues, and run `make test` after every change.
- User prefers consolidating test scripts.
- User prefers thorough documentation of test commands and scripts with explicit instructions, assuming future engineers will have no context.
- User is developing a CLI tool that should utilize existing folib features for portfolio analysis, load a default portfolio from @private-data/portfolios/portfolio-default.csv when none is specified, and avoid implementing simulation features as they're incomplete in folib.
- User prefers testing the CLI by using direct command-line mode for E2E tests with output validation and interactive mode for exploratory testing, prioritizing these approaches before unit testing, while keeping all business logic in folib and the CLI focused purely on interface and display.
- User prefers E2E test scripts that validate CLI output for issues like '$nan' values, with systematic testing of both command-line (direct mode) and interactive mode interfaces.
- User prefers testing the CLI according to the test plan before reporting progress in @.refs/ directory.
- User requires running 'make lint' and 'make test' to ensure code quality, adding unit tests for any changes to folib (like the to_dict() conversions), and conducting thorough exploratory testing to identify issues like the SPAXX** cash position parsing problem.
- User prefers having a 'make cli' command in the Makefile as the entrypoint to the CLI's interactive mode, which should load the portfolio summary view by default.
- User prefers downgrading unknown symbol warnings to INFO level and wants portfolio breakdown by type functionality with proper separation of concerns between folio and CLI.
- User prefers implementing generic filtering for portfolio listing (like 'portfolio list type=cash' or 'portfolio list symbol=GOOGL') rather than using specific commands like --focus.
- User prefers CLI tests to be in the @tests/ folder for consistency, with a dedicated 'cli' subdirectory, and wants a 'make test-cli' command to run these tests.
- User prefers running 'make lint' frequently to catch code style issues early.
- User wants documentation of supported CLI commands in a README.md file.
- After making changes, run 'make lint' and 'make test-cli' to verify code quality, and commit changes if tests pass.
- User prefers running tests before committing changes, and only committing if tests pass.
- User prefers development plans with sections: 1) Goal and outcome, 2) File references, 2b) Modification needs, 3) Solution outline, 4) Alignment with coding guidelines, 5) Final plan documented in @.refs/ with markdown and front matter.
- User prefers thorough investigation of code changes by comparing against main branch and analyzing all differences before drawing conclusions.
- User prefers writing proper tests that reproduce issues before fixing them (test-driven development), specifically requesting tests for pending activity value parsing that handle different CSV formats, and disapproves of modifying test scripts to hardcode fixes.
- User prefers not to modify the compare_portfolio_implementations.py file.
- User prefers documenting development plans in @.refs/ directory.
- User wants to ensure refactoring patterns are consistent across the codebase and is concerned about broader impacts of architectural changes.
- User prefers keeping basic data cleaning in loader.py while moving business logic to portfolio_service.py, with a focus on applying cleaning logic broadly rather than having special cases.
- User prefers making internal utility functions public when they provide useful functionality that should be tested.
- User prefers keeping implementation details out of comparison scripts and wants business logic to be encapsulated in service modules rather than duplicated elsewhere.
- User prefers writing tests for pending activity value parsing in test_portfolio_service.py that verify the function can extract values from multiple columns in the raw data.
- User wants to eliminate legacy compatibility code like 'create_portfolio_groups' and related supporting functions in favor of using folib's own data model exclusively.
- Don't modify focli as it will be deleted and replaced by the new cli project.
- User prefers to eliminate src/folib/calculations/portfolio.py and move its functions into src/folib/services/portfolio_service.py if needed.
- User updated PortfolioSummary class with new fields including beta_adjusted_exposure (sum of all positions' beta adjusted exposures) and wants to refactor by removing the calculations module for portfolio and consolidating all summary logic in portfolio_service.py.
- User prefers having unit test coverage before refactoring code to verify the changes don't break existing functionality.

# Coding Principles
- User strongly adheres to FAIL FAST principle, preferring explicit failures over silent fallbacks or generic exception handling.
- User prefers returning None instead of default values when calculations fail, allowing callers to handle these cases explicitly.
- User prefers strong type hints, early validation with explicit errors, and composition over inheritance.
- Follow KISS, DRY, and YAGNI principles with intention-revealing names and small, focused functions.
- User prefers atomic, reusable functions with interfaces designed to last over the long term.
- User prefers centralizing validation logic in a single method to maximize code reuse.
- User prefers descriptive function names and wants caching logic centralized in a dedicated cache.py module.
- User prefers maintaining sign information in values rather than using abs() and special logic for long vs short positions, as negative numbers have meaningful semantics in the codebase.
- User prefers exposure functions to handle sign inversion for short positions rather than modifying delta calculations to account for position direction.
- User prefers folib objects to have dictionary conversion capabilities for easier display in CLI.

# Code Style
- User prefers code to be structured with imports at the top of files and organized properly.
- User prefers imports to be at the top of files and wants to enforce this with a ruff linting rule. User identified imports in the middle of src/folib/services/portfolio_service.py (around line 126) as an example of the import organization issue they want to fix.
- User prefers enforcing imports to be at the top of files and is open to using ruff or other tooling to achieve this.
- User prefers gathering all imports a file needs first, analyzing what the correct imports should be, then replacing the entire imports section rather than making piecemeal changes.

# API Updates
- The calculate_option_delta function signature has been updated to remove the quantity parameter and make volatility optional, requiring updates to all consumers of this function.

# CLI Display Preferences
- User prefers displaying negative numbers in brackets (XX) instead of with a minus sign -XX in financial reporting for the CLI.
- User prefers setting 'N/A' instead of defaults in formatters to clearly indicate errors, wants E2E tests to verify proper values are displayed, and strongly opposes using abs() as negative numbers have meaningful semantics in the codebase.
- When parsing position symbols like SPAXX**, remove special characters (like **) at the end and just parse the base symbol.
---
