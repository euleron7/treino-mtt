"""Compare multiway solver output with published push/fold charts (research/*.json).

Each comparison names one of our solution files (data/solutions/<tag>.json) solved with the
reference's exact parameters, the reference source, and a seat mapping. For every
(position, stack) cell we report both range sizes and the hand classes on which the pure
action differs (our frequency >= 0.5 vs. the reference's hand list).

Writes data/validation/multiway.json and prints a summary table.
"""
import json
import os
from collections import defaultdict

import numpy as np

from solver.cards import CLASS_INDEX, CLASS_NAMES, CLASS_NCOMBOS

ROOT = os.path.join(os.path.dirname(__file__), "..")
PC10 = {"UTG": "UTG+1", "UTG+1": "UTG+2", "UTG+2": "UTG+3", "LJ": "LJ", "HJ": "HJ", "CO": "CO",
        "BTN": "BTN", "SB": "SB", "BB": "BB"}
PC_RAW = {"UTG": "UTG", "UTG + 1": "UTG+1", "UTG + 2": "UTG+2", "UTG + 3": "UTG+3", "Lojack": "LJ",
          "Hijack": "HJ", "Cutoff": "CO", "Button": "BTN", "Small Blind": "SB", "Big Blind": "BB"}
SAME = {p: p for p in ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"]}


def load_solution(tag):
    path = os.path.join(ROOT, "data", "solutions", f"{tag}.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    spots = {}
    for s in d["spots"]:
        spots[(round(s["stack"], 2), s["pusher"])] = s
    return spots


def pct_of(hands):
    return sum(CLASS_NCOMBOS[CLASS_INDEX[h]] for h in hands) / 1326 * 100


def compare(our_freq, ref_hands, ref_mixed=None, our_dev=None):
    f = np.array(our_freq)
    ours = {CLASS_NAMES[i] for i in range(169) if f[i] >= 0.5}
    ref = set(ref_hands)
    only_ours = sorted(ours - ref, key=CLASS_INDEX.get)
    only_ref = sorted(ref - ours, key=CLASS_INDEX.get)
    # hands that the reference itself plays mixed (or that we play mixed) are "boundary" hands
    mixed_ours = {CLASS_NAMES[i] for i in range(169) if 0.02 < f[i] < 0.98}
    mixed_ref = set((ref_mixed or {}).keys())
    soft = mixed_ours | mixed_ref
    hard = [h for h in only_ours + only_ref if h not in soft]
    return {
        "our_pct": round(float(f @ CLASS_NCOMBOS / 1326 * 100), 2),
        "our_pure_pct": round(pct_of(ours), 2),
        "ref_pct": round(pct_of(ref), 2),
        "only_ours": only_ours, "only_ref": only_ref,
        "n_diff": len(only_ours) + len(only_ref),
        "combo_diff_pct": round(pct_of(only_ours) + pct_of(only_ref), 2),
        "hard_diff": hard,
        "diff_dev": {h: (None if our_dev is None or our_dev[CLASS_INDEX[h]] is None else round(our_dev[CLASS_INDEX[h]], 4))
                     for h in only_ours + only_ref},
    }


def push_cases():
    pc = json.load(open(os.path.join(ROOT, "research", "push_charts.json"), encoding="utf-8"))
    srcs = pc["sources"]
    cases = []

    def by(cond):
        return [s for s in srcs if cond(s)]
    hrc = by(lambda s: "card-bunching" in s["url"] and "monte carlo" not in json.dumps(s["params"]).lower())
    for s in hrc:
        cases.append(("HRC blog 9-max 7.5bb, ante 0.1/player (no bunching)", "val_hrc_9max_7p5", SAME, s))
    for s in srcs:
        u = s.get("params", {}).get("underlying_computation") or {}
        if "pokercoaching" in s["url"] and u.get("app_table") == 1 and "BB ante" in s["params"].get("ante_type", ""):
            cases.append(("PokerCoaching app table 1 (10-handed, ante 0.1/player)", "val_pc10_ante01", PC10, s))
            cases.append(("PROXY: PokerCoaching 'BB ante' chart vs our true 9-max BB ante", "9max_bbante_mc2", SAME, s))
        if "pokercoaching" in s["url"] and u.get("app_table") == 0:
            cases.append(("PokerCoaching app table 0 (10-handed, no ante)", "val_pc10_noante", PC10, s))
        if "888poker" in s["url"]:
            cases.append(("888poker / ICMIZER 9-max 12bb, ante 0.125/player", "val_888_12bb", SAME, s))
    return cases


def call_cases():
    cc = json.load(open(os.path.join(ROOT, "research", "call_charts.json"), encoding="utf-8"))
    out = []
    for s in cc["sources"]:
        if "pokercoaching.com/push-fold" not in s["url"]:
            continue
        ante = json.dumps(s["params"]).lower()
        tag = "val_pc10_noante" if "none (table index 0)" in ante else "val_pc10_ante01"
        label = ("PokerCoaching app table 0 (10-handed, no ante)" if tag == "val_pc10_noante"
                 else "PokerCoaching app table 1 (10-handed, ante 0.1/player)")
        out.append((label, tag, "10h", s))
        if tag == "val_pc10_ante01":
            out.append(("PROXY: PokerCoaching 'BB ante' chart vs our true 9-max BB ante", "9max_bbante_mc2", "9h", s))
    for s in cc["sources"]:
        if "card-bunching-effects" in s["url"]:
            out.append(("HRC blog 9-max 7.5bb, ante 0.1/player (no bunching)", "val_hrc_9max_7p5", "9h", s))
    return out


def main():
    report = {"push": defaultdict(list), "call": defaultdict(list)}
    cache = {}
    for label, tag, seatmap, src in push_cases():
        sol = cache.setdefault(tag, load_solution(tag))
        if sol is None:
            print("missing solution", tag)
            continue
        for r in src["ranges"]:
            key = (round(float(r["stack_bb"]), 2), seatmap[r["position"]])
            if key not in sol:
                continue
            res = compare(sol[key]["push"]["freq"], r["hands"], r.get("mixed_freq"), sol[key]["push"]["dev"])
            res.update(position=r["position"], stack=r["stack_bb"], ref_stated_pct=r.get("percent"))
            report["push"][label].append(res)
    for label, tag, mode, src in call_cases():
        sol = cache.setdefault(tag, load_solution(tag))
        if sol is None:
            print("missing solution", tag)
            continue
        for r in src["ranges"]:
            if "card-bunching" in src["url"] and "no-bunching" not in r.get("notes", ""):
                continue
            if mode == "10h" and "source_positions_10handed" in r:
                pusher = PC_RAW[r["source_positions_10handed"]["pusher"]]
                caller = PC_RAW[r["source_positions_10handed"]["caller"]]
            else:
                pusher, caller = r["pusher"], r["caller"]
            key = (round(float(r["stack_bb"]), 2), pusher)
            if key not in sol or caller not in sol[key]["call"]:
                continue
            res = compare(sol[key]["call"][caller]["freq"], r["hands"], r.get("mixed_frequencies"),
                          sol[key]["call"][caller]["dev"])
            res.update(pusher=r["pusher"], caller=r["caller"], stack=r["stack_bb"], ref_stated_pct=r.get("percent"))
            report["call"][label].append(res)
    summary = {}
    for kind in ("push", "call"):
        for label, rows in report[kind].items():
            nd = np.array([x["n_diff"] for x in rows])
            hard = sum(len(x["hard_diff"]) for x in rows)
            pd = np.array([abs(x["our_pure_pct"] - x["ref_pct"]) for x in rows])
            summary[f"{kind}: {label}"] = {
                "cells": len(rows), "cells_identical": int((nd == 0).sum()),
                "mean_hand_diffs_per_cell": round(float(nd.mean()), 2), "max_hand_diffs": int(nd.max()),
                "hard_diffs_total": hard,
                "mean_abs_pct_diff": round(float(pd.mean()), 2), "max_abs_pct_diff": round(float(pd.max()), 2)}
    os.makedirs(os.path.join(ROOT, "data", "validation"), exist_ok=True)
    json.dump({"summary": summary, "push": report["push"], "call": report["call"]},
              open(os.path.join(ROOT, "data", "validation", "multiway.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    return report


if __name__ == "__main__":
    main()
