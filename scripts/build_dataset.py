#!/usr/bin/env python3
"""
build_dataset.py — merge per-batch extraction files into one dataset.

Reads every outputs/batches/batch-*.md, pulls the fenced ```json array out of each,
validates each record against the frozen schema, dedupes by ticket_key, and writes:

  outputs/dataset.jsonl     one JSON record per line (machine-readable source of truth)
  outputs/extraction.md     a human-readable merged view
  outputs/dataquality.md    coverage vs. outputs/ticket-index.md + any validation problems

Standard library only. Run from the repo root:  python3 scripts/build_dataset.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
BATCH_DIR = OUT / "batches"
INDEX = OUT / "ticket-index.md"

REQUIRED_FIELDS = [
    "ticket_key", "created_date", "status", "customer", "device_id", "device_model",
    "firmware_version", "symptom_category", "symptom_summary", "cause_type",
    "stated_root_cause", "rca_quality", "action_taken", "resolution_type",
    "signals", "related_tickets", "source_fields_used",
]
CAUSE_TYPES = {"hardware", "firmware", "connectivity", "config",
               "data-pipeline", "user-error", "unknown"}
RESOLUTION_TYPES = {"fixed", "workaround", "no-action", "pending", "cannot-reproduce"}
RCA_QUALITY = {"sufficient", "partial", "insufficient"}

JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.DOTALL)
KEY_LINE = re.compile(r"(SVCENG-\d+)")


def load_batch_records(path: Path):
    """Extract the JSON array from one batch markdown file. Returns (records, error)."""
    text = path.read_text(encoding="utf-8")
    m = JSON_BLOCK.search(text)
    if not m:
        return [], f"{path.name}: no ```json block found"
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return [], f"{path.name}: invalid JSON ({e})"
    if not isinstance(data, list):
        return [], f"{path.name}: json block is not a list"
    return data, None


def validate(rec: dict, source: str):
    problems = []
    for f in REQUIRED_FIELDS:
        if f not in rec:
            problems.append(f"{source}: {rec.get('ticket_key', '?')} missing field '{f}'")
    if rec.get("cause_type") not in CAUSE_TYPES:
        problems.append(f"{source}: {rec.get('ticket_key','?')} bad cause_type "
                        f"'{rec.get('cause_type')}'")
    if rec.get("resolution_type") not in RESOLUTION_TYPES:
        problems.append(f"{source}: {rec.get('ticket_key','?')} bad resolution_type "
                        f"'{rec.get('resolution_type')}'")
    if rec.get("rca_quality") not in RCA_QUALITY:
        problems.append(f"{source}: {rec.get('ticket_key','?')} bad rca_quality "
                        f"'{rec.get('rca_quality')}'")
    return problems


def indexed_keys():
    if not INDEX.exists():
        return None
    return set(KEY_LINE.findall(INDEX.read_text(encoding="utf-8")))


def main():
    if not BATCH_DIR.exists():
        sys.exit(f"No batches directory at {BATCH_DIR}")

    batch_files = sorted(BATCH_DIR.glob("batch-*.md"))
    if not batch_files:
        sys.exit(f"No batch-*.md files in {BATCH_DIR}")

    records = {}          # ticket_key -> record (last wins on dedupe)
    duplicates = []
    problems = []
    load_errors = []

    for bf in batch_files:
        recs, err = load_batch_records(bf)
        if err:
            load_errors.append(err)
            continue
        for rec in recs:
            problems.extend(validate(rec, bf.name))
            key = rec.get("ticket_key")
            if not key:
                continue
            if key in records:
                duplicates.append(f"{key} (also in {bf.name})")
            records[key] = rec

    # Write dataset.jsonl
    ordered = [records[k] for k in sorted(records)]
    with (OUT / "dataset.jsonl").open("w", encoding="utf-8") as fh:
        for rec in ordered:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Write human-readable extraction.md
    lines = ["# SVCENG issue_device — merged extraction",
             "",
             f"Records: {len(ordered)}  |  Batch files: {len(batch_files)}",
             ""]
    for rec in ordered:
        lines.append(f"## {rec.get('ticket_key','?')} — {rec.get('symptom_category','?')}")
        lines.append(f"- Customer: {rec.get('customer','?')}  |  "
                     f"Device: {rec.get('device_model','?')} / {rec.get('device_id','?')}  |  "
                     f"FW: {rec.get('firmware_version','?')}")
        lines.append(f"- Created: {rec.get('created_date','?')}  |  "
                     f"Status: {rec.get('status','?')}  |  "
                     f"Resolution: {rec.get('resolution_type','?')}")
        lines.append(f"- Symptom: {rec.get('symptom_summary','')}")
        lines.append(f"- Cause type: {rec.get('cause_type','?')}  |  "
                     f"RCA: {rec.get('rca_quality','?')}")
        lines.append(f"- Root cause: {rec.get('stated_root_cause','')}")
        lines.append(f"- Action: {rec.get('action_taken','')}")
        sig = rec.get("signals") or []
        rel = rec.get("related_tickets") or []
        if sig:
            lines.append(f"- Signals: {', '.join(sig)}")
        if rel:
            lines.append(f"- Related: {', '.join(rel)}")
        lines.append("")
    (OUT / "extraction.md").write_text("\n".join(lines), encoding="utf-8")

    # Write dataquality.md
    idx = indexed_keys()
    dq = ["# Data quality report", ""]
    dq.append(f"- Extracted records: {len(ordered)}")
    if idx is not None:
        extracted = set(records)
        missing = sorted(idx - extracted)
        extra = sorted(extracted - idx)
        dq.append(f"- Keys in index: {len(idx)}")
        dq.append(f"- Missing (in index, not extracted): {len(missing)}")
        dq.append(f"- Extra (extracted, not in index): {len(extra)}")
        dq.append("")
        if missing:
            dq.append("## Missing keys — re-run the batch(es) containing these")
            dq += [f"- {k}" for k in missing]
            dq.append("")
        if extra:
            dq.append("## Extra keys (not in index)")
            dq += [f"- {k}" for k in extra]
            dq.append("")
        coverage_ok = not missing
    else:
        dq.append("- (No outputs/ticket-index.md found — cannot check coverage.)")
        coverage_ok = None

    if load_errors:
        dq.append("## Batch load errors")
        dq += [f"- {e}" for e in load_errors]
        dq.append("")
    if duplicates:
        dq.append("## Duplicate ticket_keys across batches (last one kept)")
        dq += [f"- {d}" for d in duplicates]
        dq.append("")
    if problems:
        dq.append("## Schema / vocabulary problems")
        dq += [f"- {p}" for p in problems]
        dq.append("")

    verdict = "COMPLETE" if coverage_ok else ("UNKNOWN" if coverage_ok is None else "INCOMPLETE")
    if load_errors or problems:
        verdict += " (with validation issues — see above)"
    dq.insert(1, f"\n**Status: {verdict}**\n")
    (OUT / "dataquality.md").write_text("\n".join(dq), encoding="utf-8")

    print(f"dataset.jsonl: {len(ordered)} records")
    print(f"coverage: {verdict}")
    if load_errors:
        print(f"load errors: {len(load_errors)} (see dataquality.md)")
    if problems:
        print(f"validation problems: {len(problems)} (see dataquality.md)")


if __name__ == "__main__":
    main()
