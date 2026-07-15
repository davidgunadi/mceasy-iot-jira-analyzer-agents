# McEasy SVCENG Device-Ticket Analysis — Claude Agents

**Version:** 1.1.0 — see [CHANGELOG.md](CHANGELOG.md)

A Claude Code multi-agent pipeline that pulls Jira tickets matching a user-supplied JQL
query, extracts a structured record per ticket from its title, description **and** comments,
and produces a health-scan report: recurring patterns, whether tickets carry sufficient
root-cause analysis, and prioritised recommendations. The heavy fetching runs inside isolated
subagents so the analysis stays reliable across large ticket volumes without overflowing
context, and each batch can be re-run on its own.

---

## Prerequisites

Must have:

- [Claude Desktop](https://claude.com/download) / Claude Code
- [Git](https://git-scm.com/install/)
- [Python 3](https://www.python.org/downloads/) (standard library only — no extra packages)
- Claude Pro or Max account
- **The Atlassian / Jira connector configured inside Claude Code** (not just claude.ai). The
  `ticket-indexer` and `ticket-extractor` agents call it to read tickets. If it isn't
  connected, the pipeline can't fetch anything.

Optional:

- [GitHub Desktop](https://desktop.github.com/download/)
- [VSCode](https://code.visualstudio.com/download)

> **Connector permission note:** `.claude/settings.json` allow-lists the Atlassian MCP tools
> as `mcp__atlassian__*`. If your connected server has a different name, adjust that prefix to
> match — otherwise you'll be prompted to approve each Jira call manually (which still works,
> just noisier).

---

## Setup

### Option A: Terminal (CLI)

```bash
git clone https://github.com/[your-org]/mceasy-svceng-device-analysis.git
```

Open the folder in Claude Code. Agents and skills load automatically from `.claude/`.

### Option B: GitHub Desktop

1. **File → Clone Repository → URL**, paste the repo URL, choose a local path, **Clone**.
2. **Repository → Open in…** your Claude Code editor.

> The `.claude/` folder is hidden. On Mac press `Cmd + Shift + .` to show hidden files.

---

## How to use

In Claude Code, run:

```
/analyze-svceng-devices
```

Claude will ask you for the JQL query to run, then confirm the batch size before starting.
It then:

1. Indexes all matching ticket keys and slices them into batches.
2. Extracts batch 1, proposes a `symptom_category` vocabulary, and **pauses** so you can
   review and freeze it.
3. Extracts the remaining batches against the frozen vocabulary.
4. Builds the merged dataset and computes all counts with the scripts.
5. Writes the final report to `outputs/report.md` for your review.

### Tweak and repeat

Each batch writes its own file (`outputs/batches/batch-NN.md`) while the run is in progress,
so you can safely redo any single batch — re-invoke the extractor for that batch number and
it overwrites its file. Once `build_dataset.py` runs successfully, it merges all batch files
into `dataset.jsonl` and `extraction.md`, then deletes the batch files. The
`outputs/dataquality.md` report flags any tickets that are in the index but missing from the
extracted data, so you know exactly which batch to redo before the merge step.

---

## Folder structure

```
mceasy-svceng-device-analysis/
├── CLAUDE.md                          # Pipeline, frozen schema, rules — every agent reads this
├── README.md                          # This file
├── CHANGELOG.md
├── .gitignore
├── outputs/                           # All generated files (gitignored)
│   ├── ticket-index.md                #  ← ticket-indexer
│   ├── batches/
│   │   └── batch-NN.md                #  ← ticket-extractor (temporary; deleted after merge)
│   ├── taxonomy.md                    #  ← frozen symptom_category vocabulary
│   ├── dataset.jsonl                  #  ← build_dataset.py (merged, machine-readable)
│   ├── extraction.md                  #  ← build_dataset.py (merged, human-readable)
│   ├── dataquality.md                 #  ← build_dataset.py (coverage / gaps)
│   ├── aggregates.md                  #  ← aggregate.py (all counts)
│   └── report.md                      #  ← analyst (final insight report)
├── scripts/
│   ├── build_dataset.py               # merges batch files → dataset + readable view + QA, then deletes batch files
│   └── aggregate.py                   # deterministic counts → aggregates.md
└── .claude/
    ├── settings.json
    ├── agents/
    │   ├── ticket-indexer.md
    │   ├── ticket-extractor.md
    │   ├── aggregator.md
    │   └── analyst.md
    └── skills/
        └── analyze-svceng-devices/
            └── SKILL.md
```

---

## How the pieces fit

- **`CLAUDE.md`** is always loaded as project context. It holds the frozen record schema, the
  controlled vocabularies, the pipeline order, and the repo rules. Agents read it
  automatically — that's why the agent files themselves stay short.
- **Agents** (`.claude/agents/*.md`) are single-purpose roles. `ticket-extractor` is invoked
  once per batch; the others run once. Each runs in its own context.
- **The skill** (`.claude/skills/analyze-svceng-devices/SKILL.md`) is the orchestrator that
  runs the agents in order and manages the human pause points.
- **Scripts** (`scripts/*.py`) do all the counting, so numbers are deterministic.

---

## Questions

[Add your team contact here]
