# Changelog

All notable changes to this repo are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-07-15

### Added

- Agents: `ticket-indexer`, `ticket-extractor`, `aggregator`, `analyst` in `.claude/agents/`.
- Skill `/analyze-svceng-devices` in `.claude/skills/` orchestrating the full pipeline.

### Changed

- JQL is now user-supplied at runtime (skill prompts for it); no hardcoded query. The
  pipeline works with any JQL. `ticket-indexer` receives JQL + batch size from the
  orchestrator instead of reading them from `CLAUDE.md`.
- Default `BATCH_SIZE` increased from 30 to 50.
- `build_dataset.py` now deletes `outputs/batches/batch-*.md` after a successful merge,
  leaving `outputs/` clean. Batch files remain on disk during the run for re-run safety.

## [1.0.0] - 2026-07-15

### Added

- Initial pipeline scaffold for the SVCENG `issue_device` retrospective analysis.
- Agents: `ticket-indexer`, `ticket-extractor` (invoked per batch), `aggregator`, `analyst`.
- Skill `/analyze-svceng-devices` orchestrating the full pipeline with two human pause points
  (freeze symptom-category vocabulary after batch 1; review final report).
- Frozen record schema and controlled vocabularies (`cause_type`, `resolution_type`,
  `rca_quality` with a moderate RCA bar) defined in `CLAUDE.md`.
- Scripts `build_dataset.py` (merge batch files → `dataset.jsonl` + `extraction.md` +
  `dataquality.md`) and `aggregate.py` (deterministic counts → `aggregates.md`).
- `.claude/settings.json` allow-listing the Atlassian MCP tools, file tools, and Python.
- `README.md` with setup, the Jira-connector prerequisite, and the tweak-and-repeat workflow.
