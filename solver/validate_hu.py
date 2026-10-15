"""Validate the solver on the heads-up no-ante game against HoldemResources' published Nash data.

Inputs
  data/solutions/hu_noante.json                       our solutions (python -m solver.run_all --n 2 ...)
  research/hu_nash.json                               HR "hune" chart (max push / call stack per hand)
  research/hu_nash_raw/hr_equilibrium_extracted/*.csv HR raw equilibrium frequencies (0.05bb grid)
Prints a summary and writes data/validation/hu.json
"""
import csv
import json
import os

import numpy as np

from solver.cards import CLASS_INDEX, CLASS_NCOMBOS

ROOT = os.path.join(os.path.dirname(__file__), "..")


def load_hr_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    head = [h.strip() for h in rows[0]]
    hands = head[1:]
    out = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        s = round(float(r[0]), 2)
        v = np.zeros(169)
        for h, x in zip(hands, r[1:]):
            h = h.strip()
            if h:
                v[CLASS_INDEX[h]] = float(x)
        out[s] = v
    return out


def pct(freq):
    return float((freq * CLASS_NCOMBOS).sum() / 1326 * 100)


def chart_action(entry, stack, gaps=None):
    if gaps:
        for iv in gaps["push_intervals_bb"]:
            lo = iv["from"] if iv["from"] is not None else 0.0
            if lo <= stack <= iv["to"]:
                return True
        return False
    if isinstance(entry, str):
        return True  # '20+'
    return stack <= float(entry)


def main():
    ours = json.load(open(os.path.join(ROOT, "data", "solutions", "hu_noante.json"), encoding="utf-8"))
    chart = json.load(open(os.path.join(ROOT, "research", "hu_nash.json"), encoding="utf-8"))
    rawdir = os.path.join(ROOT, "research", "hu_nash_raw", "hr_equilibrium_extracted")
    hr_push = load_hr_csv(os.path.join(rawdir, "holdemresources_hu_push.csv"))
    hr_call = load_hr_csv(os.path.join(rawdir, "holdemresources_hu_call.csv"))
    gaps = chart.get("push_gaps", {})
    rows = []
    tot = {"raw_push": 0, "raw_call": 0, "chart_push": 0, "chart_call": 0, "cells": 0}
    mismatches = []
    for spot in ours["spots"]:
        S = round(spot["stack"], 2)
        p = np.array(spot["push"]["freq"])
        c = np.array(spot["call"]["BB"]["freq"])
        rp, rc = hr_push.get(S), hr_call.get(S)
        row = {"stack": S, "push_pct": round(pct(p), 2), "call_pct": round(pct(c), 2)}
        if rp is not None:
            row["hr_push_pct"] = round(pct(rp), 2)
            row["hr_call_pct"] = round(pct(rc), 2)
            # combos whose pure action differs (frequency on opposite sides of 1/2)
            dp = np.nonzero((p >= 0.5) != (rp >= 0.5))[0]
            dc = np.nonzero((c >= 0.5) != (rc >= 0.5))[0]
            row["raw_push_diff_hands"] = [chart_name(i) for i in dp]
            row["raw_call_diff_hands"] = [chart_name(i) for i in dc]
            tot["raw_push"] += len(dp)
            tot["raw_call"] += len(dc)
            row["push_freq_l1"] = round(float(np.abs(p - rp) @ CLASS_NCOMBOS / 1326 * 100), 3)
            row["call_freq_l1"] = round(float(np.abs(c - rc) @ CLASS_NCOMBOS / 1326 * 100), 3)
        cp = np.array([chart_action(chart["push"][chart_name(i)], S, gaps.get(chart_name(i))) for i in range(169)])
        cc = np.array([chart_action(chart["call"][chart_name(i)], S) for i in range(169)])
        dp = np.nonzero((p >= 0.5) != cp)[0]
        dc = np.nonzero((c >= 0.5) != cc)[0]
        row["chart_push_diff_hands"] = [chart_name(i) for i in dp]
        row["chart_call_diff_hands"] = [chart_name(i) for i in dc]
        tot["chart_push"] += len(dp)
        tot["chart_call"] += len(dc)
        tot["cells"] += 169
        for i in dp:
            mismatches.append(("push", S, chart_name(i), round(float(p[i]), 3), chart["push"][chart_name(i)]))
        for i in dc:
            mismatches.append(("call", S, chart_name(i), round(float(c[i]), 3), chart["call"][chart_name(i)]))
        rows.append(row)
    # how far from the chart threshold are the mismatches?
    dist = []
    for kind, S, h, f, entry in mismatches:
        if isinstance(entry, (int, float)):
            dist.append(abs(S - float(entry)))
        elif h in gaps and kind == "push":
            ends = [x for iv in gaps[h]["push_intervals_bb"] for x in (iv["from"], iv["to"]) if x is not None]
            dist.append(min(abs(S - e) for e in ends))
        else:
            dist.append(float("nan"))
    dist = np.array(dist)
    summary = {
        "stacks_compared": len(rows),
        "hand_cells": tot["cells"],
        "raw_equilibrium": {"push_action_mismatches": tot["raw_push"], "call_action_mismatches": tot["raw_call"],
                            "max_abs_push_pct_diff": max(abs(r["push_pct"] - r["hr_push_pct"]) for r in rows if "hr_push_pct" in r),
                            "max_abs_call_pct_diff": max(abs(r["call_pct"] - r["hr_call_pct"]) for r in rows if "hr_call_pct" in r)},
        "chart": {"push_mismatches": tot["chart_push"], "call_mismatches": tot["chart_call"],
                  "mismatch_distance_to_chart_threshold_bb": {
                      "median": float(np.nanmedian(dist)) if len(dist) else 0.0,
                      "p95": float(np.nanpercentile(dist, 95)) if len(dist) else 0.0,
                      "max": float(np.nanmax(dist)) if len(dist) else 0.0}},
    }
    os.makedirs(os.path.join(ROOT, "data", "validation"), exist_ok=True)
    json.dump({"summary": summary, "rows": rows, "chart_mismatches": mismatches},
              open(os.path.join(ROOT, "data", "validation", "hu.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r["stack"] in (2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 19.0):
            print(f"{r['stack']:>5}bb push {r['push_pct']:5.1f}% (HR {r.get('hr_push_pct', '-')})  "
                  f"call {r['call_pct']:5.1f}% (HR {r.get('hr_call_pct', '-')})  "
                  f"raw diffs P{r.get('raw_push_diff_hands')} C{r.get('raw_call_diff_hands')}  "
                  f"chart diffs P{r['chart_push_diff_hands']} C{r['chart_call_diff_hands']}")


def chart_name(i):
    from solver.cards import CLASS_NAMES
    return CLASS_NAMES[i]


if __name__ == "__main__":
    main()
