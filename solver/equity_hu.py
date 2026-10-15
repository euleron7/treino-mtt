"""Exact heads-up preflop all-in equities for every pair of hole-card combos.

All C(48,5) = 1,712,304 boards are enumerated for one representative of each
suit-isomorphism class of matchups, then expanded to the full 1326 x 1326 matrix.

Outputs (data/eq2.npz):
  combo_share[i, j]  share of the pot won by combo i against combo j (ties split; NaN if cards clash)
  N2[h, v]           number of non-clashing (combo of class h, combo of class v) pairs
  EQ2[h, v]          average share of class h against class v over those pairs
"""
import os
import sys
import time
from itertools import permutations

import numba as nb
import numpy as np

from solver.cards import CLASS_NCOMBOS, COMBO_CLASS, COMBOS
from solver.evaluator import FLUSH, FLUSH_SUIT, NONFLUSH, RANK_KEYS, SUIT_KEYS

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "eq2.npz")
N_BOARDS = 1712304
PERMS = np.array(list(permutations(range(4))), dtype=np.int64)  # 24 suit permutations


@nb.njit(cache=True)
def _map(c, perm):
    return (c >> 2) * 4 + perm[c & 3]


@nb.njit(cache=True)
def canonical_pairs(combos, perms):
    n = combos.shape[0]
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            a1, a2, b1, b2 = combos[i, 0], combos[i, 1], combos[j, 0], combos[j, 1]
            if a1 != b1 and a1 != b2 and a2 != b1 and a2 != b2:
                total += 1
    ii = np.empty(total, np.int64)
    jj = np.empty(total, np.int64)
    keys = np.empty(total, np.int64)
    flip = np.empty(total, np.int64)
    t = 0
    for i in range(n):
        for j in range(i + 1, n):
            a1, a2, b1, b2 = combos[i, 0], combos[i, 1], combos[j, 0], combos[j, 1]
            if a1 == b1 or a1 == b2 or a2 == b1 or a2 == b2:
                continue
            best = np.int64(1) << 62
            bflip = 0
            for p in range(perms.shape[0]):
                x1, x2 = _map(a1, perms[p]), _map(a2, perms[p])
                y1, y2 = _map(b1, perms[p]), _map(b2, perms[p])
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1
                f = 0
                if (y1 < x1) or (y1 == x1 and y2 < x2):
                    x1, x2, y1, y2 = y1, y2, x1, x2
                    f = 1
                key = ((x1 * 52 + x2) * 52 + y1) * 52 + y2
                if key < best:
                    best = key
                    bflip = f
            ii[t] = i
            jj[t] = j
            keys[t] = best
            flip[t] = bflip
            t += 1
    return ii, jj, keys, flip


@nb.njit(parallel=True, cache=True)
def hu_kernel(reps, nonflush, flush, flush_suit, rank_keys, suit_keys):
    P = reps.shape[0]
    wins = np.zeros(P, np.int64)
    ties = np.zeros(P, np.int64)
    RK = np.empty(52, np.int64)
    SK = np.empty(52, np.int64)
    MB = np.empty(52, np.int64)
    for c in range(52):
        RK[c] = rank_keys[c >> 2]
        SK[c] = suit_keys[c & 3]
        MB[c] = np.int64(1) << ((c & 3) * 16 + (c >> 2))
    for p in nb.prange(P):
        a1, a2, b1, b2 = reps[p, 0], reps[p, 1], reps[p, 2], reps[p, 3]
        deck = np.empty(48, np.int64)
        n = 0
        for c in range(52):
            if c != a1 and c != a2 and c != b1 and c != b2:
                deck[n] = c
                n += 1
        ka = RK[a1] + RK[a2]
        kb = RK[b1] + RK[b2]
        sa = SK[a1] + SK[a2]
        sb = SK[b1] + SK[b2]
        ma = MB[a1] | MB[a2]
        mb = MB[b1] | MB[b2]
        w = 0
        t = 0
        for i1 in range(44):
            c = deck[i1]
            k1, s1, m1 = RK[c], SK[c], MB[c]
            for i2 in range(i1 + 1, 45):
                c = deck[i2]
                k2, s2, m2 = k1 + RK[c], s1 + SK[c], m1 | MB[c]
                for i3 in range(i2 + 1, 46):
                    c = deck[i3]
                    k3, s3, m3 = k2 + RK[c], s2 + SK[c], m2 | MB[c]
                    for i4 in range(i3 + 1, 47):
                        c = deck[i4]
                        k4, s4, m4 = k3 + RK[c], s3 + SK[c], m3 | MB[c]
                        for i5 in range(i4 + 1, 48):
                            c = deck[i5]
                            k = k4 + RK[c]
                            s = s4 + SK[c]
                            m = m4 | MB[c]
                            fs = flush_suit[s + sa]
                            if fs >= 0:
                                va = flush[((m | ma) >> (16 * fs)) & 0x1FFF]
                            else:
                                va = nonflush[k + ka]
                            fs = flush_suit[s + sb]
                            if fs >= 0:
                                vb = flush[((m | mb) >> (16 * fs)) & 0x1FFF]
                            else:
                                vb = nonflush[k + kb]
                            if va > vb:
                                w += 1
                            elif va == vb:
                                t += 1
        wins[p] = w
        ties[p] = t
    return wins, ties


def decode(key):
    y2 = key % 52
    key //= 52
    y1 = key % 52
    key //= 52
    x2 = key % 52
    x1 = key // 52
    return x1, x2, y1, y2


def compute(limit=None):
    t0 = time.perf_counter()
    ii, jj, keys, flip = canonical_pairs(COMBOS, PERMS)
    uniq, inv = np.unique(keys, return_inverse=True)
    print(f"{len(keys)} disjoint combo pairs -> {len(uniq)} canonical matchups "
          f"({time.perf_counter() - t0:.1f}s)", flush=True)
    reps = np.array([decode(int(k)) for k in uniq], dtype=np.int64)
    if limit:
        reps = reps[:limit]
    t0 = time.perf_counter()
    wins, ties = hu_kernel(reps, NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS)
    dt = time.perf_counter() - t0
    print(f"enumerated {len(reps)} matchups x {N_BOARDS} boards in {dt:.1f}s", flush=True)
    if limit:
        return reps, wins, ties
    share_rep = (wins + 0.5 * ties) / N_BOARDS  # share of the canonical first combo
    share = np.where(flip == 0, share_rep[inv], 1.0 - share_rep[inv])  # share of combo ii
    M = np.full((1326, 1326), np.nan, dtype=np.float64)
    M[ii, jj] = share
    M[jj, ii] = 1.0 - share
    N2 = np.zeros((169, 169), dtype=np.int64)
    S2 = np.zeros((169, 169), dtype=np.float64)
    ok = ~np.isnan(M)
    ci = COMBO_CLASS[:, None].repeat(1326, 1)
    cj = COMBO_CLASS[None, :].repeat(1326, 0)
    np.add.at(N2, (ci[ok], cj[ok]), 1)
    np.add.at(S2, (ci[ok], cj[ok]), M[ok])
    EQ2 = np.where(N2 > 0, S2 / np.maximum(N2, 1), np.nan)
    assert (N2.sum(1) == CLASS_NCOMBOS * 1225).all()
    np.savez_compressed(OUT, combo_share=M.astype(np.float32), N2=N2, EQ2=EQ2,
                        canon_keys=uniq, canon_wins=wins, canon_ties=ties)
    print("saved", OUT)
    return M, N2, EQ2


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    compute(lim)
