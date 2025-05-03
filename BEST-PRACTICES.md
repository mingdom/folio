# Project Rules
- Unless asked by the user, you should NOT write code. See the "When to NOT edit code" section below.
- Maintain strict separation of concerns: Business logic MUST reside in the core library (`src/folio/`), not in interface layers in either `src/cli/` or `src/folio`.
- Use `.refs/` for temporary documentation such as project plans or logs

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
1. Group edits: Always group together edits to the same file in a single edit file tool call, instead of multiple calls.
2. Read before edit: Unless you are appending some small easy to apply edit to a file, or creating a new file, you MUST read the the contents or section of what you're editing before editing it.
3. Lint: If you've introduced (linter) errors, fix them if clear how to (or you can easily figure out how to). 4. 3-strike-rule: Do not make uneducated guesses. And DO NOT loop more than 3 times on fixing errors on the same file. On the third time, you should stop and ask the user what to do next.

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
