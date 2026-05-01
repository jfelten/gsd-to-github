# Push Plan to GitHub

Push a plan JSON file to GitHub as ordered issues on a project board.

<required_reading>
- `references/plan-schema.md` — understand the input format
- `references/gh-projects-v2.md` — understand the API patterns
- `references/discover-project-ids.md` — if project IDs aren't configured yet
</required_reading>

<process>

1. **Validate the plan JSON** against the schema in `references/plan-schema.md`. Check:
   - All required fields present (`plan_name`, `project`, `repository`, `tasks`)
   - Tasks array is non-empty
   - All `depends_on` indices are valid (within bounds of the tasks array)
   - All referenced labels exist on the target repository

2. **Load authentication** — read `GITHUB_ACCESS_TOKEN` from `~/git/.env` or use ambient `GH_TOKEN`.

3. **Get the project node ID** via GraphQL query to the org/user.

4. **Create issues in order** — for each task in array order:
   a. Build the issue body: prepend `**Plan:** {name}` and `**Repository:** {repo}`, append dependency checklist referencing already-created issue numbers
   b. Create the issue: `gh issue create --repo REPO --title TITLE --body BODY [--label LABEL]...`
   c. Add to project board: `gh project item-add NUMBER --owner OWNER --url URL --format json`
   d. Set status to "Todo": GraphQL mutation with `TODO_OPTION_ID`
   e. Record `(issue_number, title)` for dependency resolution in subsequent tasks

5. **Report results** — list all created issue numbers and confirm board status.

</process>

<success_criteria>
- Every task in the plan has a corresponding GitHub issue
- Each issue is on the project board with status "Todo"
- Dependency references use real issue numbers (not array indices)
- Labels are applied correctly
- No issues created without being added to the board
</success_criteria>
