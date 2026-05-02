---
---

description: Guidance for the Copilot agent about when to load these instructions and how to behave in this repository
applyTo: '.github/instructions/\*\*'

---

Purpose
Provide concise, repository-specific guidance the AI should follow when generating code, reviewing changes, and answering developer questions.

When to load

- Load these instructions for tasks that modify repository code, tests, CI, or docs.
- Load when the user opens or edits files under `src/`, `server/`, `client/`, or `.github/`.

Coding conventions

- Language: Python 3.10+ (follow typing where reasonable).
- Formatting: apply `black` formatting and `isort` for imports.
- Linting: prefer `flake8`/`ruff` style rules; keep functions small and well-named.
- Docstrings: include short module/class/function docstrings for non-trivial code.

Tests and validation

- Add or update unit tests for any behavioral change; aim for clear, deterministic tests.
- Run existing test commands before proposing final changes.

Dependencies and secrets

- Add new Python dependencies to `requirements.txt` and explain why.
- Never add secrets or credentials to the repo; use environment variables and document required vars.

Commit and PR guidance

- Make small, focused commits with descriptive messages.
- For breaking changes, explain migration steps and update `readme.md` or relevant docs.

Interaction guidelines

- When a request is ambiguous, ask a clarifying question before making changes.
- When applying code fixes, prefer minimal, well-tested changes rather than large refactors unless requested.

Files and areas to review

- Core app: `src/`, `server/`, `client/`
- CI and automation: `.github/workflows/`, `docker-compose.yml`
- Packaging: `requirements.txt`, `readme.md`

If unsure

- Ask the developer for the intended behavior, target Python version, or any project-specific constraints.

Keep instructions concise and actionable. If the user asks for an implementation, produce runnable code and, when appropriate, a brief test or usage example.
