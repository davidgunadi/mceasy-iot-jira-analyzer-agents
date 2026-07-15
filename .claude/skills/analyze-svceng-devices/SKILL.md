---
name: analyze-svceng-devices
description: >
  Start the SVCENG issue_device retrospective analysis. Invoke when the user wants to analyse
  the device tickets for patterns, RCA sufficiency, and recommendations. Runs indexer →
  per-batch extractors → aggregator → analyst, pausing to freeze the symptom taxonomy.
---

Greet the user and explain the pipeline before starting:

"I'll run a health-scan analysis over the SVCENG `issue_device` tickets (~169, this year) using
a multi-agent pipeline. Each heavy step runs in its own isolated context, so this stays
reliable across all the tickets:

1. 🗂️ **ticket-indexer** — lists every matching ticket key and slices them into batches
2. 🔎 **ticket-extractor** — run once per batch; reads each ticket's title, description **and
   comments**, and extracts a structured record
3. ⏸️ **You freeze the symptom categories** after batch 1, so every later batch stays consistent
4. 🧮 **aggregator** — merges the batches and computes all the counts in code
5. 🧠 **analyst** — writes the final report: patterns, RCA gaps, recommendations

Before we start:
- Confirm the **Atlassian/Jira connector is connected** in this Claude Code session (I need it
  to read the tickets).
- **Batch size?** Default is 30 (~6 batches). Smaller = lighter per-batch context.
- The JQL I'll use is `project = \"SVCENG\" AND labels = issue_device AND createdDate >= startOfYear()`.
  Tell me if that's not right."

Once the user confirms, run the pipeline in this strict order:

1. **@ticket-indexer** → writes `outputs/ticket-index.md`. Report the total count and number
   of batches. If the count is wildly off from ~169, pause and check with the user.

2. **@ticket-extractor (batch 1)** → writes `outputs/batches/batch-01.md` and returns a
   **proposed symptom-category vocabulary** with one-line definitions.

3. ⏸ **PAUSE — freeze the taxonomy.** Show the user the proposed `symptom_category` list.
   Let them add/rename/remove/merge categories. When they approve, write the final list to
   `outputs/taxonomy.md` (kebab-case values, each with a one-line definition). Do not proceed
   until this file exists. This is the consistency guardrail — never skip it.

4. **@ticket-extractor (batch 2 … N)** → one invocation per remaining batch, each reading the
   frozen `outputs/taxonomy.md`. Run them **sequentially** (not parallel) so any taxonomy edge
   cases surface early and connector rate limits stay comfortable. Each writes its own
   `outputs/batches/batch-NN.md`.

5. **@aggregator** → runs `scripts/build_dataset.py` then `scripts/aggregate.py`. If its
   `dataquality.md` check reports missing tickets, tell the user exactly which batch(es) to
   re-run (just re-invoke @ticket-extractor for that batch number), then re-run the aggregator.

6. **@analyst** → writes `outputs/report.md`.

7. ⏸ **Final review.** Summarise the 3–4 headline findings in chat and point the user to
   `outputs/report.md`. Ask whether they want to drill into any finding or re-run any batch.

Throughout: keep your own messages compact — rely on the subagents' returned summaries, and
let the files hold the detail. That's what keeps this whole run inside a small context.
