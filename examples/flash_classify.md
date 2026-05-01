# Flash: Inbox Triage

```
Classify these items into urgent / today / this-week / archive.
Return a markdown table with columns: item, tag, reason.

- "Server down in prod — AWS us-east-1, 5xx errors since 14:32"
- "Q3 planning doc ready for review"
- "Expense report for March needs approval"
- "New team member onboarding checklist"
- "Old design mockups from 2024 project"
```

Expected shape:

| item | tag | reason |
|------|-----|--------|
| Server down in prod | urgent | active outage |
| Q3 planning doc | this-week | needs review but not blocking |
| Expense report | today | approval pending |
| Onboarding checklist | today | new hire starts soon |
| Old design mockups | archive | no current use |
