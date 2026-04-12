---
description: Review staged or recently changed files before committing
---

Review the current changes before committing.

1. Run `git diff --name-only` to identify changed files
2. If there are staged files, also run `git diff --cached --name-only`
3. Use the code-reviewer subagent to review all changed files
4. After the review, report:
   - CRITICAL issues (must fix before commit)
   - WARNING issues (should fix)
   - SUGGESTION (nice to have)
5. If there are CRITICAL issues, do NOT commit — list what needs fixing
6. If clean, confirm it is safe to commit
