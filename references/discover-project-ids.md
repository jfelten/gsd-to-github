# Discovering Project Board IDs

GitHub Projects V2 uses opaque node IDs for fields and options. You must discover these before configuring the scripts.

## Step 1: Find the Project Node ID

For an **organization** project:
```bash
gh api graphql -f query='
{
  organization(login: "OWNER") {
    projectV2(number: PROJECT_NUMBER) {
      id
    }
  }
}'
```

For a **user** project:
```bash
gh api graphql -f query='
{
  user(login: "OWNER") {
    projectV2(number: PROJECT_NUMBER) {
      id
    }
  }
}'
```

## Step 2: Get Field and Option IDs

```bash
gh api graphql -f query='
{
  organization(login: "OWNER") {
    projectV2(number: PROJECT_NUMBER) {
      id
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
            options { id name }
          }
        }
      }
    }
  }
}'
```

Look for the **Status** field in the output. Record:
- `STATUS_FIELD_ID` — the `id` of the Status field
- `TODO_OPTION_ID` — the `id` of the option named "Todo"
- `IN_PROGRESS_OPTION_ID` — the `id` of the option named "In Progress"
- `DONE_OPTION_ID` — the `id` of the option named "Done"

## Step 3: List Items (verify setup)

```bash
gh project item-list PROJECT_NUMBER --owner OWNER --format json
```

## Quick Reference: Common Field Types

| Field Type | GraphQL Fragment |
|---|---|
| Single Select | `ProjectV2SingleSelectField` |
| Text | `ProjectV2Field` |
| Number | `ProjectV2Field` |
| Date | `ProjectV2Field` |
| Iteration | `ProjectV2IterationField` |

## Setting a Field Value (GraphQL Mutation)

```graphql
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PROJECT_NODE_ID"
    itemId: "ITEM_NODE_ID"
    fieldId: "FIELD_NODE_ID"
    value: { singleSelectOptionId: "OPTION_NODE_ID" }
  }) {
    projectV2Item { id }
  }
}
```
