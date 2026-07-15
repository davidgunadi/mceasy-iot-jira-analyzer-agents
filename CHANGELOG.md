# Changelog

All notable changes to this repo are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
