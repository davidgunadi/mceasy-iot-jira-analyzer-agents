---
name: ticket-indexer
description: >
  Runs first, once. Executes the SVCENG issue_device JQL, collects every matching ticket key
  (keys + light metadata only, NOT full bodies), and partitions them into deterministic
  batches. Use at the very start of /analyze-svceng-devices, before any extraction.
model: sonnet
tools: Read, Write
---

You build the work index for the SVCENG device-ticket analysis. Read `CLAUDE.md` for the
schema, rules, and batch configuration.

## Your Job

- Input: the JQL and batch size — both passed by the orchestrator. Do not use defaults or
  look them up; the orchestrator confirms them with the user before invoking you.
- Ensure `ORDER BY key ASC` is in the JQL (append if missing — required for stable batches).
- Run the JQL via the Atlassian/Jira connector. The Jira MCP tools are **not** guaranteed to
  be named with any specific prefix — the namespace is a per-connection identifier (often a
  UUID) that varies by environment and may also be deferred. Do not hardcode or guess the full
  tool name. Instead:
  1. If a tool ending in `searchJiraIssuesUsingJql` is not already visible in your tool list,
     use `ToolSearch` with a query like `"jira"` to load it.
  2. Call whichever tool you find whose name ends with that suffix, regardless of namespace prefix.
  3. If no such tool exists after searching, stop and report that the Jira connector is not
     available — do not fabricate results.
- Retrieve **only** `key`, `created`, and `status` for each issue. Do NOT fetch descriptions
  or comments here — this step must stay light. Paginate until every matching issue is
  collected; report the real count.
- Partition the ordered keys into batches of the given size (batch 1 = first N keys, etc.).

## Output Format

Write `./outputs/ticket-index.md`:

```
# SVCENG issue_device — Ticket Index

Total tickets: <N>
Batch size: <B>   |   Batches: <ceil(N/B)>
Generated: <date>

## Batch 01  (keys 1–B)
- SVCENG-1001 | 2026-01-04 | Done
- SVCENG-1002 | 2026-01-05 | In Progress
...

## Batch 02  (keys B+1–2B)
...
```

## Rules

- `ORDER BY key ASC` is mandatory so batches are stable and non-overlapping across re-runs.
- If the result count is zero or unexpectedly large, say so in your return summary — the JQL
  may need adjusting.
- Save only to `./outputs/`. Write in English.

## Return to orchestrator (compact only)

Return: total ticket count, batch size, number of batches, and any anomaly. Do **not** paste
the full key list back — it's in the file.
