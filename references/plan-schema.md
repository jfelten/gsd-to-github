# Plan JSON Schema

The plan JSON file is the input to `push-plans.py`. It defines a named plan with ordered tasks that become GitHub issues.

## Schema

```json
{
  "plan_name": "string — Human-readable name (e.g. 'Data Architecture v2')",
  "project": "string — GitHub org/project-number (e.g. 'ez-appsec/2')",
  "repository": "string — Target repo for issues (e.g. 'ez-appsec/ez-appsec')",
  "tasks": [
    {
      "title": "string — Short task title (becomes issue title)",
      "description": "string — Full Markdown body (becomes issue body)",
      "labels": ["string — GitHub labels (must exist on repo)"],
      "depends_on": [0]
    }
  ]
}
```

## Fields

| Field | Required | Description |
|---|---|---|
| `plan_name` | Yes | Identifies the plan. Used in issue bodies as `**Plan:** {name}` for filtering. |
| `project` | Yes | `owner/number` format. Used to locate the project board. |
| `repository` | Yes | `owner/repo` format. Where issues are created. |
| `tasks` | Yes | Ordered array. Execution order matches array order. |
| `tasks[].title` | Yes | Becomes the GitHub issue title. |
| `tasks[].description` | Yes | Markdown body. Should include goal, done criteria, file lists. |
| `tasks[].labels` | No | Array of label names. Labels must already exist on the repository. |
| `tasks[].depends_on` | No | Array of 0-based indices into the `tasks` array. References tasks that must complete first. |

## Dependency Model

Dependencies use **0-based array indices**, not issue numbers. When `push-plans.py` creates issues, it resolves indices to real issue numbers and writes them as a checklist:

```markdown
### Dependencies
This task depends on the following tasks completing first:

- [ ] #42 — Extract widget interface
- [ ] #43 — Define data model
```

`pull-plan.py` parses this checklist and checks whether each referenced issue is in the "Done" column before allowing the task to be claimed.

## Example

```json
{
  "plan_name": "Widget Refactor",
  "project": "ez-appsec/2",
  "repository": "ez-appsec/ez-appsec",
  "tasks": [
    {
      "title": "Extract widget interface",
      "description": "## Goal\nDefine the widget interface.\n\n## Done criteria\n- [ ] Interface defined in `widget.py`\n- [ ] Existing tests pass",
      "labels": ["enhancement"],
      "depends_on": []
    },
    {
      "title": "Implement concrete widget",
      "description": "## Goal\nBuild the concrete implementation.\n\n## Done criteria\n- [ ] Implementation in `concrete_widget.py`\n- [ ] Unit tests added",
      "labels": ["enhancement"],
      "depends_on": [0]
    }
  ]
}
```
