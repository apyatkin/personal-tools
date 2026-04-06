---
name: favro
description: Use when working with Favro — cards, boards, collections, task tracking, or any Favro-related task
---

# Favro

## Company Context

To get company-specific Favro settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Use `apps.favro` section — reads `organization_id`, `email`, `token_ref`

If no company is active, ask the user which company context to use.

Resolve the token: read `token_ref` from the config, then resolve via the appropriate secret backend (keychain or bitwarden).

## Commands

All Favro operations use the REST API. Set these variables from config:

```bash
FAVRO_ORG="<organization_id>"
FAVRO_EMAIL="<email>"
FAVRO_TOKEN="<resolved token>"
```

### List Collections

```bash
curl -s -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  "https://favro.com/api/v1/collections" | jq '.entities[].name'
```

### List Cards in Collection

```bash
curl -s -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  "https://favro.com/api/v1/cards?collectionId=<collection-id>" | jq '.entities[] | {name, columnId}'
```

### Move Card (Change Status)

```bash
curl -s -X PUT -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  -H "Content-Type: application/json" \
  -d '{"columnId":"<target-column-id>"}' \
  "https://favro.com/api/v1/cards/<card-id>"
```

### Add Comment to Card

```bash
curl -s -X POST -u "$FAVRO_EMAIL:$FAVRO_TOKEN" \
  -H "organizationId: $FAVRO_ORG" \
  -H "Content-Type: application/json" \
  -d '{"comment":"<comment text>"}' \
  "https://favro.com/api/v1/cards/<card-id>/comments"
```

## Runbooks

### List Cards in a Collection

1. First list collections to find the collection ID
2. Then list cards in that collection
3. Parse the response to show card names and statuses

### Move Card to Done

1. List cards to find the card ID by name
2. List columns (via widget API) to find the "Done" column ID
3. PUT to update the card with the target `columnId`

### Add Work Summary Comment

1. Find the card ID by searching cards
2. Format a comment summarizing the work done
3. POST the comment to the card
