"""Solve every (stack, pusher position) subgame of a push/fold configuration in parallel.

Usage:
  python -m solver.run_all                       # 9-max, BB ante 1bb, stacks 5..15, up to 2 callers
  python -m solver.run_all --max-callers 1 --tag mc1
  python -m solver.run_all --n 2 --ante-type none --ante 0 --stacks 1:20:0.5 --tag hu
Writes data/solutions/<tag>.json
"""
import argparse
import json
import os
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

from multiprocessing import Pool  # noqa: E402

import numpy as np  # noqa: E402

from solver.cards import CLASS_NAMES  # noqa: E402

POSITIONS = {
    2: ["SB", "BB"],
    3: ["BTN", "SB", "BB"],
    4: ["CO", "BTN", "SB", "BB"],
    5: ["HJ", "CO", "BTN", "SB", "BB"],
    6: ["LJ", "HJ", "CO", "BTN", "SB", "BB"],
    7: ["UTG", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
    8: ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
    9: ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
    10: ["UTG", "UTG+1", "UTG+2", "UTG+3", "LJ", "HJ", "CO", "BTN", "SB", "BB"],
}

_EQ = None


def _init(with3):
    global _EQ
    from solver.nash import Equity
    _EQ = Equity(with3=with3)


def _r(a, nd):
    return [None if (x is None or not np.isfinite(x)) else round(float(x), nd) for x in a]


def _solve(task):
    from solver.nash import Game, PusherSubgame, range_pct
    gp, j, iters = task
    g = Game(**gp)
    sg = PusherSubgame(_EQ, g, j)
    t0 = time.perf_counter()
    sol = sg.solve(iters=iters, tol=5e-7, check_every=250)
    rep = sg.report(sol)
    pos = POSITIONS[g.n]
    out = {
        "stack": gp["stack"], "pusher": pos[j], "iters": sol["iters"],
        "exploitability": sol["exploitability"], "seconds": round(time.perf_counter() - t0, 1),
        "push": {"freq": _r(rep["push"]["freq"], 4), "dev": _r(rep["push"]["dev"], 4),
                 "pct": round(range_pct(rep["push"]["freq"]), 2)},
        "call": {pos[k]: {"freq": _r(v["freq"], 4), "dev": _r(v["dev"], 4), "pct": round(range_pct(v["freq"]), 2)}
                 for k, v in rep["call"].items()},
        "overcall": {f"{pos[k]}>{pos[m]}": {"freq": _r(v["freq"], 4), "dev": _r(v["dev"], 4),
                                            "pct": round(range_pct(v["freq"]), 2)}
                     for (k, m), v in rep["overcall"].items()},
    }
    return out


def refine(args):
    path = os.path.join("data", "solutions", f"{args.tag}.json")
    d = json.load(open(path, encoding="utf-8"))
    m = d["meta"]
    todo = [i for i, sp in enumerate(d["spots"]) if sp["exploitability"] > args.refine]
    print(f"refining {len(todo)} of {len(d['spots'])} spots with {args.iters} iterations", flush=True)
    tasks = []
    for i in todo:
        sp = d["spots"][i]
        gp = dict(n=m["players"], stack=sp["stack"], ante_type=m["ante_type"], ante=m["ante"],
                  max_callers=m["max_callers"])
        tasks.append((gp, m["positions"].index(sp["pusher"]), args.iters))
    with3 = m["max_callers"] >= 2 and m["players"] >= 3
    with Pool(args.procs, initializer=_init, initargs=(with3,)) as pool:
        for i, r in zip(todo, pool.imap(_solve, tasks)):
            old = d["spots"][i]["exploitability"]
            if r["exploitability"] < old:
                d["spots"][i] = r
            print(f"{r['stack']}bb {r['pusher']}: expl {old:.1e} -> {r['exploitability']:.1e}", flush=True)
    with open(path, "w") as f:
        json.dump(d, f, separators=(",", ":"))
    print("patched", path)


def parse_stacks(s):
    if ":" in s:
        a, b, step = (float(x) for x in s.split(":"))
        return [round(float(x), 4) for x in np.arange(a, b + 1e-9, step)]
    return [float(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=9)
    ap.add_argument("--ante-type", default="bb")
    ap.add_argument("--ante", type=float, default=1.0)
    ap.add_argument("--max-callers", type=int, default=2)
    ap.add_argument("--stacks", default="5:15:1")
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--tag", default="9max_bbante")
    ap.add_argument("--refine", type=float, default=None,
                    help="re-solve, with --iters iterations, only the spots of an existing <tag>.json "
                         "whose exploitability is above this value, and patch the file")
    args = ap.parse_args()
    if args.refine is not None:
        return refine(args)
    stacks = parse_stacks(args.stacks)
    with3 = args.max_callers >= 2 and args.n >= 3
    tasks = []
    for S in stacks:
        gp = dict(n=args.n, stack=S, ante_type=args.ante_type, ante=args.ante, max_callers=args.max_callers)
        for j in range(args.n - 1):
            tasks.append((gp, j, args.iters))
    # biggest subgames first so the pool stays busy
    tasks.sort(key=lambda t: t[1])
    t0 = time.perf_counter()
    results = []
    with Pool(args.procs, initializer=_init, initargs=(with3,)) as pool:
        for i, r in enumerate(pool.imap_unordered(_solve, tasks)):
            results.append(r)
            print(f"[{i + 1}/{len(tasks)}] {r['stack']}bb {r['pusher']}: push {r['push']['pct']}% "
                  f"expl {r['exploitability']:.1e} it {r['iters']} ({r['seconds']}s)", flush=True)
    results.sort(key=lambda r: (r["stack"], POSITIONS[args.n].index(r["pusher"])))
    out = {
        "meta": {"players": args.n, "positions": POSITIONS[args.n], "sb": 0.5, "bb": 1.0,
                 "ante_type": args.ante_type, "ante": args.ante, "max_callers": args.max_callers,
                 "model": "chip EV push/fold Nash, equal stacks (bb before posting)",
                 "hand_order": CLASS_NAMES, "elapsed_s": round(time.perf_counter() - t0, 1)},
        "spots": results,
    }
    os.makedirs(os.path.join("data", "solutions"), exist_ok=True)
    path = os.path.join("data", "solutions", f"{args.tag}.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("saved", path, f"in {out['meta']['elapsed_s']}s")


if __name__ == "__main__":
    main()
