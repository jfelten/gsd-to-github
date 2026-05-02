# Claim Plan Task (Bash)

Interactive workflow to claim a plan task from the ez-appsec GitHub project board. This script:
- Fetches issue details and creates a `.plan-context.md` handoff file
- Assigns the issue to the current user
- Moves it to "In Progress" on the project board
- Creates a git branch from the issue title
- Prints a ready-to-use AI assistant prompt

<required_reading>
- `references/gh-projects-v2.md` — API patterns and context file format
</required_reading>

<process>

The `claim-plan.sh` script is invoked interactively:

```bash
./claim-plan.sh <issue-number>
```

**Note:** This script is configured specifically for `ez-appsec/ez-appsec` with hardcoded project constants. For other repositories, use `workflows/pull-plan.md` instead or adapt the script constants.

**Prerequisites checked:**
- `gh` CLI is installed and authenticated
- Git config has user.name and user.email
- Python 3.10+ is available
- Docker is installed (for ez-appsec specific environment)

**Execution flow:**

1. **Load GitHub token** — reads `GITHUB_ACCESS_TOKEN` from `~/git/.env`

2. **List project items** — `gh project item-list --format json`

3. **Categorize items** — separate Done items from Todo candidates

4. **Find first actionable task** — iterate Todo items in order, find one where all dependencies are Done

5. **Fetch issue details** — `gh issue view NUMBER --json body,title,url,labels,assignees`

6. **Create `.plan-context.md`** with:
   - Plan name (extracted from issue body)
   - Issue number and title
   - Repository and URL
   - Branch name (slugified from title)
   - Full issue body

7. **Claim the task:**
   - Set status to "In Progress" via GraphQL mutation
   - Assign to current user via `gh issue edit --add-assignee`

8. **Create git branch** — `git checkout -b feat/slugified-title`

9. **Generate AI prompt** — prints a detailed prompt that includes task description, dependencies, and next steps

</process>

<exit_codes>
- **0** — Task claimed successfully
- **1** — Error (missing prerequisites, API failure, no token found)
- **2** — No actionable tasks available

</exit_codes>

<context_file>

`.plan-context.md` format (gitignored):

```markdown
# Plan Task Context
# Plan: Plan Name
# Issue: #42 — Task Title
# URL: https://github.com/owner/repo/issues/42
# Repository: owner/repo
# Branch: feat/task-slug
# DO NOT COMMIT this file — it is gitignored.

[full issue body]
```

</context_file>

<success_criteria>
- Script validates all prerequisites before execution
- Only tasks whose dependencies are all Done are claimed
- Issue moves to "In Progress" on the project board
- Git branch is created and checked out
- `.plan-context.md` contains all information needed by `complete-plan`
- AI prompt includes actionable next steps
</success_criteria>
