# Complete Current Task

Mark the current plan task as Done, push its branch, and clean up.

<required_reading>
- `references/gh-projects-v2.md` — context file format and API patterns
</required_reading>

<process>

1. **Parse `.plan-context.md`** — extract issue number, repo, branch name, plan name, and title using the header comment patterns.

2. **Ensure correct branch** — check `git rev-parse --abbrev-ref HEAD`:
   - If already on the right branch, continue
   - If branch exists locally, switch to it
   - If branch doesn't exist, create it with `git checkout -b`

3. **Push the branch** — `git push -u origin BRANCH` with `GH_TOKEN` in environment.
   - If push fails, warn but continue to mark the board item Done

4. **Mark project board item as Done:**
   a. Get project node ID via GraphQL
   b. Find item ID by scanning `gh project item-list` for matching issue number
   c. Set status to "Done" via GraphQL mutation with `DONE_OPTION_ID`

5. **Clean up** — delete `.plan-context.md`.

6. **Report** — confirm task completion with issue number and branch name.

</process>

<optional_steps>
- **Create a PR** — after pushing, optionally create a draft PR:
  ```bash
  gh pr create --draft --title "ISSUE_TITLE" --body "Closes #ISSUE_NUMBER" --repo REPO
  ```
  Only do this if the user asks or if the plan task specifies PR creation.
</optional_steps>

<success_criteria>
- Branch is pushed to origin
- Project board item is in "Done" column
- `.plan-context.md` is cleaned up
- If branch push fails, board status is still updated (non-blocking)
</success_criteria>
