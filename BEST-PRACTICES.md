# Project Rules
- Unless asked by the user, you should NOT write code. See the "When to NOT edit code" section below.
- When the user says "STOP" - stop editing immediately and give the user a summary of your progress.
- Maintain strict separation of concerns: Business logic MUST reside in the core library (`src/folio/`), not in interface layers in either `src/cli/` or `src/folio`.
- Use `.refs/` to write plans out in markdown format
- All application, test and lint logs are in `logs/`

# Core Philosophy & Coding Best Practices
Use these guiding principles when considering HOW to code or think
- Maximize simplicity at nearly all cost
- Prefer to fail fast than to handle errors
- **NEVER, EVER, EVER fix a test by adding fake values. Lives are at stake!!
- Assume we do not need backwards compatibility unless specifically asked
- Do not add comments to the code you write, unless the user asks you to, or the code is complex and requires additional context.
- When making changes to files, first understand the file's code conventions. Mimic code style, use existing libraries and utilities, and follow existing patterns.
- NEVER assume that a given library is available, even if it is well known. Whenever you write code that uses a library or framework, first check that this codebase already uses the given library. For example, you might look at neighboring files, or check the package.json (or cargo.toml, and so on depending on the language).
- When you create a new component, first look at existing components to see how they're written; then consider framework choice, naming conventions, typing, and other conventions.
- When you edit a piece of code, first look at the code's surrounding context (especially its imports) to understand the code's choice of frameworks and libraries. Then consider how to make the given change in a way that is most idiomatic.

# When Making Code Changes
Use the code edit tools at most once per turn.
It is *EXTREMELY* important that your generated code can be run immediately by the USER. To ensure this, follow these instructions carefully:
- Group edits: Always group together edits to the same file in a single edit file tool call, instead of multiple calls.
- Read before edit: Unless you are appending some small easy to apply edit to a file, or creating a new file, you MUST read the the contents or section of what you're editing before editing it.
- Lint: If you've introduced (linter) errors, run `make lint` first to see if it can fix the errors. If not, fix the errors manually.
- 3-strike-rule: Do not make uneducated guesses. And DO NOT loop more than 3 times on fixing errors on the same file. On the third time, you should stop and ask the user what to do next.

# When to NOT edit code
- Unless explicitly asked by the user, you should NOT produce code changes.
- When the user asks a question, fully analyze, write out your thoughts, then answer.
- Example of questions that should not produce code edits:
  - "qq: how does the portfolio simulator work?"
  - "what's the best way to implement DCF calculator in our app?"
  - "investigate `make test` failures"

# When to STOP and ask the user
STOP and ASK for help if:
- If you are making repeated edits to the same file without resolving the issue
- If you exceed 3 tries at any task

# Prohibited actions - **NEVER** run these:
- Do not run `make folio`. You can't test your code changes by running the application.

# Encouraged Actions
- `make lint`: Run this all the time to catch lint issues early
- `make test`: Unit tests

# References
- Prior to generating any code, carefully read the project conventions
  - Read [project-design.md](docs/project-design.md) to understand the codebase
  - Read [project-conventions.md](docs/project-conventions.md) to understand _how_ to write code for the codebase
