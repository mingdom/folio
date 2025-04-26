---
description: Rules to get the AI to behave
alwaysApply: true
---
# General rules for AI
- Prior to generating any code, carefully read the project conventions
  - Read [project-design.md](docs/project-design.md) to understand the codebase
  - Read [project-conventions.md](docs/project-conventions.md) to understand _how_ to write code for the codebase
- Run `make lint` and `make test` after every change. `lint` in particular can be run very frequently.
- When user starts a prompt with `QQ:` or `Question:`, just answer the question or prompt without producing code.
- Prefer small testable steps, after each step give a summary to the user and summarize the next step
- **Maintain strict separation of concerns**: Business logic MUST reside in the core library (`src/folio/`), not in interface layers (`src/focli/`). Interface layers should only handle user interaction, command parsing, and result presentation.

## Prohibited actions

- Do not run `make folio`. This is for the user to run only.
- Do not use `git` commands unless explicitly asked.
