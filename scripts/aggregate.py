#!/usr/bin/env python3
"""
aggregate.py — deterministic counts over outputs/dataset.jsonl.

Writes outputs/aggregates.md with:
  - RCA-quality split (overall and by cause_type)
  - symptom_category and cause_type and resolution_type frequencies
  - repeat customers and repeat devices (top N)
  - recurrence: same customer + same symptom_category more than once
  - resolved-but-unexplained: resolution_type in {fixed,no-action} AND rca_quality insufficient
  - tickets referencing other tickets

Standard library only. Run after build_dataset.py:  python3 scripts/aggregate.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATASET = OUT / "dataset.jsonl"
TOP_N = 15


def load():
    if not DATASET.exists():
        raise SystemExit(f"No {DATASET}. Run build_dataset.py first.")
    recs = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            recs.append(json.loads(line))
    return recs


def counter_table(counter: Counter, header, total):
    lines = [f"| {header} | Count | % |", "|---|---:|---:|"]
    for k, v in counter.most_common():
        pct = f"{100*v/total:.0f}%" if total else "0%"
        lines.append(f"| {k} | {v} | {pct} |")
    return "\n".join(lines)


def main():
    recs = load()
    n = len(recs)
    md = ["# SVCENG issue_device — aggregates", "", f"Total tickets analysed: **{n}**", ""]

    # RCA overall
    rca = Counter(r.get("rca_quality", "unknown") for r in recs)
    md += ["## RCA quality (overall)", counter_table(rca, "rca_quality", n), ""]

    # RCA by cause_type
    by_cause_rca = defaultdict(Counter)
    for r in recs:
        by_cause_rca[r.get("cause_type", "unknown")][r.get("rca_quality", "unknown")] += 1
    md += ["## RCA quality by cause_type",
           "| cause_type | sufficient | partial | insufficient | total |",
           "|---|---:|---:|---:|---:|"]
    for cause in sorted(by_cause_rca, key=lambda c: -sum(by_cause_rca[c].values())):
        c = by_cause_rca[cause]
        tot = sum(c.values())
        md.append(f"| {cause} | {c.get('sufficient',0)} | {c.get('partial',0)} | "
                  f"{c.get('insufficient',0)} | {tot} |")
    md.append("")

    # Symptom categories
    cats = Counter(r.get("symptom_category", "unknown") for r in recs)
    md += ["## Symptom categories", counter_table(cats, "symptom_category", n), ""]

    # Cause types
    causes = Counter(r.get("cause_type", "unknown") for r in recs)
    md += ["## Cause types", counter_table(causes, "cause_type", n), ""]

    # Resolution types
    res = Counter(r.get("resolution_type", "unknown") for r in recs)
    md += ["## Resolution types", counter_table(res, "resolution_type", n), ""]

    # Repeat customers
    cust = Counter(r.get("customer", "unknown") for r in recs
                   if r.get("customer") not in (None, "", "unknown"))
    repeat_cust = Counter({k: v for k, v in cust.items() if v > 1})
    md += ["## Repeat customers (more than one ticket)",
           f"Distinct customers: {len(cust)}  |  with >1 ticket: {len(repeat_cust)}", ""]
    if repeat_cust:
        md.append("| Customer | Tickets |")
        md.append("|---|---:|")
        for k, v in repeat_cust.most_common(TOP_N):
            md.append(f"| {k} | {v} |")
    md.append("")

    # Repeat devices
    dev = Counter(r.get("device_id", "unknown") for r in recs
                  if r.get("device_id") not in (None, "", "unknown"))
    repeat_dev = Counter({k: v for k, v in dev.items() if v > 1})
    md += ["## Repeat devices (same device_id, more than one ticket)",
           f"Distinct devices with an id: {len(dev)}  |  with >1 ticket: {len(repeat_dev)}", ""]
    if repeat_dev:
        md.append("| device_id | Tickets |")
        md.append("|---|---:|")
        for k, v in repeat_dev.most_common(TOP_N):
            md.append(f"| {k} | {v} |")
    md.append("")

    # Device models
    models = Counter(r.get("device_model", "unknown") for r in recs
                     if r.get("device_model") not in (None, "", "unknown"))
    if models:
        md += ["## Device models", counter_table(models, "device_model", n), ""]

    # Recurrence: same customer + same symptom_category > 1
    combo = Counter()
    for r in recs:
        c = r.get("customer")
        s = r.get("symptom_category")
        if c not in (None, "", "unknown") and s not in (None, "", "unknown"):
            combo[(c, s)] += 1
    recurring = [(c, s, v) for (c, s), v in combo.items() if v > 1]
    recurring.sort(key=lambda x: -x[2])
    md += ["## Recurrence — same customer hit by the same symptom more than once",
           f"Recurring (customer, symptom) pairs: {len(recurring)}", ""]
    if recurring:
        md.append("| Customer | Symptom | Times |")
        md.append("|---|---|---:|")
        for c, s, v in recurring[:TOP_N]:
            md.append(f"| {c} | {s} | {v} |")
    md.append("")

    # Resolved but unexplained
    unexplained = [r for r in recs
                   if r.get("resolution_type") in {"fixed", "no-action"}
                   and r.get("rca_quality") == "insufficient"]
    md += ["## Resolved but unexplained (latent repeats)",
           "Tickets closed as fixed/no-action but with insufficient RCA — a resolved symptom "
           "with no diagnosed cause.",
           f"Count: **{len(unexplained)}** ({100*len(unexplained)/n:.0f}% of all tickets)", ""]
    if unexplained:
        md.append("Examples: " + ", ".join(r.get("ticket_key", "?")
                                            for r in unexplained[:20]))
    md.append("")

    # Cross-references
    refs = [r for r in recs if r.get("related_tickets")]
    md += ["## Tickets referencing other tickets",
           f"Count: {len(refs)}", ""]
    if refs:
        md.append("| Ticket | References |")
        md.append("|---|---|")
        for r in refs[:TOP_N]:
            md.append(f"| {r.get('ticket_key','?')} | "
                      f"{', '.join(r.get('related_tickets', []))} |")
    md.append("")

    # Signals
    sig = Counter()
    for r in recs:
        for s in (r.get("signals") or []):
            sig[s.split(":")[0]] += 1
    if sig:
        md += ["## Signals", counter_table(sig, "signal", n), ""]

    (OUT / "aggregates.md").write_text("\n".join(md), encoding="utf-8")
    print(f"aggregates.md written for {n} tickets")
    print(f"  RCA: sufficient={rca.get('sufficient',0)} "
          f"partial={rca.get('partial',0)} insufficient={rca.get('insufficient',0)}")
    print(f"  resolved-but-unexplained: {len(unexplained)}")


if __name__ == "__main__":
    main()
