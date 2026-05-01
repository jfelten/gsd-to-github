# Pull Next Actionable Task

Claim the next actionable task from a plan on the GitHub project board.

<required_reading>
- `references/gh-projects-v2.md` — API patterns and context file format
</required_reading>

<process>

1. **Get the plan name** — either from the user or from the most recent `.plan-context.md`.

2. **List all project items** — `gh project item-list NUMBER --owner OWNER --format json`

3. **Categorize items by status:**
   - Collect all "Done" issue numbers into a set
   - Collect all "Todo" items as candidates

4. **Filter to plan members** — for each Todo candidate:
   a. Fetch issue body: `gh issue view NUMBER --repo REPO --json body,title,url,labels`
   b. Check for `**Plan:** {plan_name}` in the body
   c. Extract dependency issue numbers from `- [ ] #(\d+)` patterns

5. **Find first actionable task** — iterate candidates in order, pick the first one where all dependency issue numbers appear in the Done set.

6. **Claim the task:**
   a. Set status to "In Progress" via GraphQL mutation with `IN_PROGRESS_OPTION_ID`
   b. Assign to current user: `gh issue edit NUMBER --repo REPO --add-assignee $(gh api user --jq '.login')`

7. **Derive branch name** — slugify the issue title: lowercase, replace non-alphanumeric with hyphens, trim to 60 chars, prefix with `feat/`.

8. **Write `.plan-context.md`** with issue number, repo, branch name, URL, plan name, and full issue body.

9. **Report** — print the claimed task, branch name, and any resolved dependencies.

</process>

<exit_codes>
- **0** — Task claimed, `.plan-context.md` written
- **1** — Error (missing args, API failure)
- **2** — No actionable tasks (all done, in progress, or blocked on dependencies)
</exit_codes>

<success_criteria>
- Only tasks whose dependencies are ALL Done are eligible
- Claimed task moves to "In Progress" on the board
- `.plan-context.md` contains all information needed by `complete-plan`
- If no tasks are actionable, reports which tasks are blocked and on what
</success_criteria>
