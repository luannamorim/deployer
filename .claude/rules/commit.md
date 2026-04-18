# Commit Rules

- Use Conventional Commits for ALL commit messages
- Format: `type(scope): description` — scope is optional but encouraged
- Allowed types: feat, fix, test, docs, ci, refactor, chore
- Description must be lowercase, imperative mood, no period at the end
- Examples:
  - `feat(middleware): add Redis-backed sliding window rate limiter`
  - `test(llm): add unit tests for token counter and cost calculator`
  - `docs: add README with architecture and quickstart`
  - `ci: add GitHub Actions workflow for lint and test`

- Every commit must leave the project in a working state — no broken commits
- Never accumulate work and commit everything at the end
- Each commit represents ONE logical unit of work
- Tests for a feature are committed in the same phase as the feature, not deferred
- Follow the commit plan in docs/SPEC.md phase by phase

- Before committing, always run: `make lint` and `make test`
- If either fails, fix before committing
- Never use `git add .` blindly — review staged files first with `git status`
