---
description: Miscellaneous rules to get the AI to behave
globs: *
alwaysApply: true
---
# General rules for AI
- Prior to generating any code, carefully read the project conventions
  - Read [project-design.md](docs/project-design.md) to understand the codebase
  - Read [project-conventions.md](docs/project-conventions.md) to understand _how_ to write code for the codebase
- Run `make lint` and `make test` after every change. `lint` in particular can be run very frequently.

## Prohibited actions

- Do not run `make folio`. This is for the user to run only.
- Do not use `git` commands unless explicitly asked.
