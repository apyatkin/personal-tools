---
name: jira
description: Use when working with Jira — issues, sprints, boards, jira CLI, or any Jira-related task
---

# Jira

## Company Context

To get company-specific Jira settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Use `apps.jira` section — reads `host`, `project`, `email`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Issues

```bash
jira issue list -q "project=<PROJECT> AND sprint in openSprints()"
jira issue view <KEY>-123
jira issue create -t Task -s "title" -b "description" -P <PROJECT>
jira issue move <KEY>-123 "In Progress"
jira issue comment add <KEY>-123 "comment text"
jira issue assign <KEY>-123 "username"
```

### Sprint

```bash
jira sprint list --board <board-id>
jira sprint list --board <board-id> --state active
```

### Search (JQL)

```bash
jira issue list -q "project=<PROJECT> AND assignee=currentUser() AND status != Done"
jira issue list -q "project=<PROJECT> AND type=Bug AND priority=High"
jira issue list -q "project=<PROJECT> AND updated >= -7d"
```

## Runbooks

### Create Task from Plan

1. Extract title and description from the plan
2. Create: `jira issue create -t Task -s "<title>" -b "<description>" -P <PROJECT>`
3. Move to In Progress: `jira issue move <KEY> "In Progress"`
4. Add implementation notes as comments

### Triage a Bug

1. Search for duplicates: `jira issue list -q "project=<PROJECT> AND type=Bug AND text ~ '<keywords>'"`
2. If duplicate exists, link to it and close as duplicate
3. If new: set priority, assign, add to current sprint
4. Add reproduction steps as a comment

### Close Sprint

1. List incomplete issues: `jira issue list -q "project=<PROJECT> AND sprint in openSprints() AND status != Done"`
2. For each incomplete issue: move to next sprint or backlog
3. Close the sprint via the web UI (no CLI support for sprint close)
