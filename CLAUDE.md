# McEasy SVCENG Device-Ticket Analysis

This project uses Claude Code's multi-agent system to run a retrospective, health-scan
analysis over SVCENG Jira tickets labelled `issue_device`, created since the start of the
year (~169 tickets). It answers three questions at once:

1. **Patterns** — repeat customers, repeat devices, recurring symptom categories.
2. **RCA discipline** — do tickets contain a sufficient root-cause analysis, or do they
   close on the symptom disappearing?
3. **Recommendations** — what to actually do, prioritised.

The pipeline is designed so that the heavy work (fetching full ticket bodies + comments)
happens **inside subagents**, whose contexts are isolated from the orchestrator. The
orchestrator only ever sees compact summaries, so the main context stays small even across
~169 tickets. Each batch is re-runnable in isolation ("tweak and repeat").

---

## Agents

Agents live in `.claude/agents/`. Each is a markdown file with a YAML frontmatter header.

| Agent | Model | Role |
|---|---|---|
| `ticket-indexer` | sonnet | Runs the JQL once, lists all matching ticket keys, partitions them into batches. Writes `outputs/ticket-index.md`. |
| `ticket-extractor` | sonnet | Invoked **once per batch**. Fetches each ticket's title + description + comments, extracts one structured record per ticket against the frozen schema below. Writes `outputs/batches/batch-NN.md`. |
| `aggregator` | sonnet | Runs the scripts in `./scripts/` to merge batch files and compute all counts deterministically (repeat customers/devices, category frequencies, RCA rates). Writes `outputs/aggregates.md`. |
| `analyst` | opus | Reads the merged dataset + aggregates and writes the final insight report: patterns, RCA gaps, prioritised recommendations. Writes `outputs/report.md`. |

---

## Skills (Slash Commands)

| Command | What it triggers |
|---|---|
| `/analyze-svceng-devices` | Runs the full pipeline end to end, pausing at defined points for human review. |

---

## Pipeline Order

```
/analyze-svceng-devices
      ↓
@ticket-indexer            → outputs/ticket-index.md  (all keys, sliced into batches)
      ↓
@ticket-extractor (batch 1)→ outputs/batches/batch-01.md  (+ proposes symptom categories)
      ↓
⏸ PAUSE — human reviews the proposed symptom categories and freezes them
          → outputs/taxonomy.md   (the controlled vocabulary for symptom_category)
      ↓
@ticket-extractor (batch 2 … N)  → outputs/batches/batch-NN.md   [reads frozen taxonomy]
      ↓
scripts/build_dataset.py   → outputs/dataset.jsonl + outputs/extraction.md + outputs/dataquality.md
      ↓
@aggregator (runs build_dataset.py then aggregate.py) → outputs/aggregates.md
      ↓
@analyst                   → outputs/report.md
      ↓
⏸ Final report for human review
```

**Why batch 1 pauses:** the `symptom_category` vocabulary is derived from real tickets in
batch 1, then **frozen**. Every later batch must categorise against that frozen list so the
final counts are consistent instead of counting synonyms as different categories. This pause
is the single most important quality guardrail in the pipeline — do not skip it.

---

## Batch configuration

- `BATCH_SIZE = 30` (default). ~169 tickets → 6 batches (last batch ~19).
- Tune `BATCH_SIZE` down if a single extractor run gets large or slow; the pipeline is
  correct for any batch size. Batches are sliced deterministically by the indexer
  (`ORDER BY key ASC`), so slices never overlap and re-running one batch is safe.

### The JQL (source of truth)

```
project = "SVCENG" AND labels = issue_device AND createdDate >= startOfYear() ORDER BY key ASC
```

---

## Frozen record schema

Every extractor invocation emits **one JSON object per ticket** using exactly these fields.
Do not add, rename, or drop fields. `outputs/batches/batch-NN.md` contains a single fenced
```json array of these objects (this block is the machine-readable source of truth; the
scripts parse it).

```json
{
  "ticket_key": "SVCENG-1234",
  "created_date": "2026-02-11",
  "status": "Done",
  "customer": "PT Contoh Logistik",
  "device_id": "GT06-889900",
  "device_model": "GT06N",
  "firmware_version": "2.3.1",
  "symptom_category": "no-gps-fix",
  "symptom_summary": "One line, plain description of the reported problem.",
  "cause_type": "firmware",
  "stated_root_cause": "Plain-text root cause if one is given, else \"none\".",
  "rca_quality": "sufficient",
  "action_taken": "What was done to resolve it, else \"none\".",
  "resolution_type": "fixed",
  "signals": ["reopened"],
  "related_tickets": ["SVCENG-1190"],
  "source_fields_used": ["description", "comments"]
}
```

### Controlled vocabularies (do not invent values outside these)

- **`cause_type`**: `hardware` | `firmware` | `connectivity` | `config` | `data-pipeline` | `user-error` | `unknown`
- **`resolution_type`**: `fixed` | `workaround` | `no-action` | `pending` | `cannot-reproduce`
- **`rca_quality`** (moderate bar — a plausible root cause need NOT be verified):
  - `sufficient` — names a plausible **mechanism** beyond the symptom (e.g. "SIM deregistered by carrier", "harness corrosion", "cold-boot buffer overflow in fw 2.3.1").
  - `partial` — gestures at a cause but stays at symptom level or is pure speculation ("device seems faulty", "maybe network").
  - `insufficient` — no cause given; closed because the symptom vanished, or "device replaced" with no *why*.
- **`symptom_category`**: **frozen** in `outputs/taxonomy.md` after batch 1. If a ticket does
  not fit any frozen category, set it to `uncovered` and add a `signals` entry
  `"needs-category-review"` rather than inventing a new category.
- **`signals`** (free list; use these where they apply): `reopened`, `escalated`,
  `sla-breach`, `needs-category-review`, `multiple-devices`, `references:SVCENG-XXXX`.

### Missing data

If a field genuinely isn't present in the ticket, use `"unknown"` for strings and `[]` for
lists — never guess. `device_id`/`device_model`/`firmware_version` are often absent; that's
expected. Never fabricate a customer name, root cause, or resolution.

---

## Rules

- All output files must be saved to `./outputs/` — never write to the repo root.
- Per-batch extractor output goes to `./outputs/batches/batch-NN.md` (zero-padded). An
  extractor **overwrites** its own batch file on re-run; it never appends to a shared file.
- Any script invoked by an agent while running must live in `./scripts/` — never write
  scripts to the repo root.
- All counting/aggregation is done by the scripts in `./scripts/`, never by an agent reading
  rows and tallying by hand. LLM hand-counting across ~169 rows is unreliable.
- Subagents return only a **compact summary** (counts, anomalies, file path) to the
  orchestrator — never the full extracted data. This is what keeps the orchestrator context
  small.
- Comments are a **required** source, not optional. If the connector's search result does not
  include comments, fetch them per issue before extracting.
- Write in English.

---

## Versioning

This repo uses [CHANGELOG.md](CHANGELOG.md) (Keep a Changelog format) and Semantic
Versioning (`MAJOR.MINOR.PATCH`).

**What counts as a functional change** (requires a version bump — this is a pipeline repo, so
"functional" means it changes what happens when someone clones and runs it):

- `.claude/agents/*.md` — adding, removing, or changing an agent's behaviour, model, or tools
- `.claude/skills/**/SKILL.md` — adding or changing the pipeline a slash command runs
- `scripts/*.py` — changing how the dataset is built or aggregated
- `.claude/settings.json` — permission or hook changes
- Root `CLAUDE.md` — changes to the schema, vocabularies, pipeline order, or rules above this section

**Not a functional change** (no bump): README prose, `.gitignore`, comments, typo fixes in docs.

**Version bump rules:**
- **MAJOR** — breaking or workflow-changing (renamed/removed agent or skill, changed pipeline order, schema field change)
- **MINOR** — new capability (new agent, new script, new vocabulary value)
- **PATCH** — fix or tweak to existing behaviour

**On every commit with a functional change**, proactively (without being asked):
1. Add an entry under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md) (Added/Changed/Fixed/Removed), then move it under a new version heading dated with the commit date.
2. Bump the version in `CHANGELOG.md` and in the `**Version:**` line in `README.md` — keep both in sync.

---

## Context (McEasy domain grounding)

- McEasy is a B2B SaaS telematics + logistics platform (Indonesia) serving fleet operators,
  3PL logistics companies, and transport vendors. Customers are companies (`PT …`), not
  individuals.
- Devices are IoT telematics units: GPS/GNSS trackers, OBD-II readers, fuel-level sensors,
  and related hardware installed in vehicles. Common real-world failure modes seen in SVCENG:
  device not reporting / offline, GPS drift or no fix, fuel-level or fuel-report mismatches,
  OBD fuel-calculation errors, trip-history mismatches, SIM/connectivity loss, firmware
  regressions after updates, and installation/wiring faults.
- A ticket's device problem can be **hardware** (the unit), **firmware** (software on the
  unit), **connectivity** (SIM/network/carrier), **config** (wrong settings/calibration),
  **data-pipeline** (ingestion/processing on McEasy's side), or **user-error**. Use
  `cause_type` to capture which.
- "Good output" for the analyst means: evidence-tied (cite ticket keys), honest about
  uncertainty, and prioritised by impact — not a generic list of best practices.
