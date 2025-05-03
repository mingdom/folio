# Project Rules
- Unless asked by the user, you should NOT write code. See the "When to NOT edit code" section below.
- When the user says "STOP" - stop editing immediately and give the user a summary of your progress.
- Maintain strict separation of concerns: Business logic MUST reside in the core library (`src/folio/`), not in interface layers in either `src/cli/` or `src/folio`.
- Use `.refs/` for temporary documentation such as project plans or logs
- All application, test and lint logs are in `logs/`

# When to NOT edit code
- Unless explicitly asked by the user, you should NOT produce code changes.
- When the user asks a question, fully analyze, write out your thoughts, then answer.
- Example of questions that should not produce code edits:
  - "qq: how does the portfolio simulator work?"
  - "what's the best way to implement DCF calculator in our app?"
  - "investigate `make test` failures"

# When Making Code Changes
Use the code edit tools at most once per turn.
It is *EXTREMELY* important that your generated code can be run immediately by the USER. To ensure this, follow these instructions carefully:
- Group edits: Always group together edits to the same file in a single edit file tool call, instead of multiple calls.
- Read before edit: Unless you are appending some small easy to apply edit to a file, or creating a new file, you MUST read the the contents or section of what you're editing before editing it.
- Lint: If you've introduced (linter) errors, run `make lint` first to see if it can fix the errors. If not, fix the errors manually.
- 3-strike-rule: Do not make uneducated guesses. And DO NOT loop more than 3 times on fixing errors on the same file. On the third time, you should stop and ask the user what to do next.

# When to STOP and ask the user
STOP and ASK for help if:
- If you are making repeated edits to the same file without resolving the issue
- If you exceed 3 tries at any task

# Prohibited actions
- Do not run `make folio`. This is for the user to run only.
- Do not use `git` commands unless explicitly asked.

# Encouraged Actions
- `make lint`: Run this all the time to catch lint issues early
- `make test`: Unit tests

# References
- Prior to generating any code, carefully read the project conventions
  - Read [project-design.md](docs/project-design.md) to understand the codebase
  - Read [project-conventions.md](docs/project-conventions.md) to understand _how_ to write code for the codebase
