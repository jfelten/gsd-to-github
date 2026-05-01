# GitHub Projects V2 — Patterns Used by This Skill

This reference covers the specific `gh` CLI and GraphQL patterns used by the push/pull/complete scripts.

## Authentication

Scripts read `GITHUB_ACCESS_TOKEN` from `~/git/.env`:

```
GITHUB_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The token is passed as `GH_TOKEN` environment variable to all `gh` commands. Required scopes: `repo`, `project`, `read:org`.

Alternative: if `GH_TOKEN` or `GITHUB_TOKEN` is already in the environment, the scripts will use that.

## gh CLI Commands Used

### Create Issue
```bash
gh issue create --repo OWNER/REPO --title "Title" --body "Body" --label "label1" --label "label2"
```
Returns the issue URL on the last line of stdout. Parse issue number from the URL.

### Add Issue to Project Board
```bash
gh project item-add PROJECT_NUMBER --owner OWNER --url ISSUE_URL --format json
```
Returns JSON with the item `id` (node ID used for field updates).

### List Project Items
```bash
gh project item-list PROJECT_NUMBER --owner OWNER --format json
```
Returns `{ "items": [...] }` where each item has:
- `id` — item node ID
- `status` — current status column name (e.g. "Todo", "In Progress", "Done")
- `content.number` — issue number
- `content.title` — issue title
- `content.repository` — repo slug

### View Issue
```bash
gh issue view ISSUE_NUMBER --repo OWNER/REPO --json body,title,url,labels
```

### Edit Issue (assign)
```bash
gh issue edit ISSUE_NUMBER --repo OWNER/REPO --add-assignee USERNAME
```

### Get Current User
```bash
gh api user --jq '.login'
```

## GraphQL Mutations

### Get Project Node ID
```graphql
query {
  organization(login: "OWNER") {
    projectV2(number: N) { id }
  }
}
```

### Update Item Status
```graphql
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PROJECT_NODE_ID"
    itemId: "ITEM_NODE_ID"
    fieldId: "STATUS_FIELD_NODE_ID"
    value: { singleSelectOptionId: "OPTION_NODE_ID" }
  }) {
    projectV2Item { id }
  }
}
```

Used with different option IDs for Todo, In Progress, and Done transitions.

## Issue Body Conventions

### Plan Marker
Every issue created by `push-plans.py` starts with:
```
**Plan:** Plan Name
**Repository:** owner/repo
```
This is how `pull-plan.py` identifies issues belonging to a specific plan.

### Dependency Checklist
Dependencies are appended at the bottom of the issue body:
```markdown
---
### Dependencies
This task depends on the following tasks completing first:

- [ ] #42 — Extract widget interface
- [ ] #43 — Define data model
```

`pull-plan.py` parses `- [ ] #(\d+)` and `- [x] #(\d+)` patterns. A task is actionable when all its dependency issues are in the "Done" column on the project board.

## Context File Format

`.plan-context.md` is written by `pull-plan.py` and read by `complete-plan.py`:

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

Parsed by regex: `# Issue: #(\d+)`, `# Repository: (\S+)`, `# Branch: (\S+)`, `# Plan: (.+)`.
