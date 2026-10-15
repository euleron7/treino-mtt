"""Build docs/ranges.js (data for the web app) from a solver output file.

Per spot we ship, for each of the 169 hand classes:
  dev  EV(push or call) - EV(fold) in 0.01 bb (integers)
  mix  {class index: frequency in %} for hands whose equilibrium frequency is not a clean 0/1
       (or whose EV difference rounds to zero), everything else is pure: freq = dev > 0
Usage: python -m solver.build_web [solution_tag]
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.join(os.path.dirname(__file__), "..")


def pack(entry):
    dev = [0 if d is None else int(round(d * 100)) for d in entry["dev"]]
    mix = {}
    for i, (f, d) in enumerate(zip(entry["freq"], dev)):
        pure = 1.0 if d > 0 else 0.0
        if abs(f - pure) > 0.02 or d == 0:
            mix[i] = int(round(f * 100))
    return {"dev": dev, "mix": mix, "pct": entry["pct"]}


def main(tag="9max_bbante_mc2"):
    src = json.load(open(os.path.join(ROOT, "data", "solutions", f"{tag}.json"), encoding="utf-8"))
    meta = src["meta"]
    pos = meta["positions"]
    push, call = {}, {}
    worst = 0.0
    for s in src["spots"]:
        st = str(int(s["stack"])) if float(s["stack"]).is_integer() else str(s["stack"])
        push.setdefault(st, {})[s["pusher"]] = pack(s["push"])
        call.setdefault(st, {})[s["pusher"]] = {k: pack(v) for k, v in s["call"].items()}
        worst = max(worst, s["exploitability"])
    val_path = os.path.join(ROOT, "data", "validation", "summary_for_app.json")
    validation = json.load(open(val_path, encoding="utf-8")) if os.path.exists(val_path) else None
    out = {
        "meta": {"players": meta["players"], "positions": pos, "sb": meta["sb"], "bb": meta["bb"],
                 "ante_type": meta["ante_type"], "ante": meta["ante"], "max_callers": meta["max_callers"],
                 "stacks": sorted({int(float(k)) for k in push}), "generated": date.today().isoformat(),
                 "max_exploitability_bb": round(worst, 7)},
        "push": push,
        "call": call,
        "validation": validation,
    }
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    path = os.path.join(ROOT, "docs", "ranges.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("// Gerado por solver/build_web.py - ranges Nash push/fold (chip EV)\n")
        f.write("window.PF_DATA=")
        json.dump(out, f, separators=(",", ":"))
        f.write(";\n")
    print("wrote", path, os.path.getsize(path) // 1024, "KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
