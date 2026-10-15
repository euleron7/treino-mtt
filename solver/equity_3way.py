"""Three-way preflop all-in equities between hand classes (for overcall / multiway pots).

For every unordered class triple (a <= b <= c) the valid (non-clashing) combo triples are
enumerated exactly (count N3) and the pot shares are estimated by stratified Monte Carlo:
each valid combo triple receives the same number of random boards.

Recorded per triple, on the same boards:
  main share of each player in the 3-way pot (ties split),
  pairwise share between each pair of players with the third hand's cards dead (side pots).

Expanded to ordered tensors (data/eq3.npz), all (169, 169, 169):
  N3[x, y, z]  number of valid (combo x, combo y, combo z) triples
  E3[x, y, z]  share of x in a 3-way pot against y and z
  P3[x, y, z]  share of x in a pot contested only by x and y (z's cards removed)
"""
import os
import sys
import time

import numba as nb
import numpy as np

from solver.cards import CLASS_COMBOS, CLASS_NCOMBOS
from solver.evaluator import FLUSH, FLUSH_SUIT, NONFLUSH, RANK_KEYS, SUIT_KEYS

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "eq3.npz")


@nb.njit(cache=True, inline="always")
def _next(state):
    # xorshift64*
    x = state[0]
    x ^= x >> np.uint64(12)
    x ^= x << np.uint64(25)
    x ^= x >> np.uint64(27)
    state[0] = x
    return x * np.uint64(2685821657736338717)


@nb.njit(cache=True, inline="always")
def _val(k, s, m, nonflush, flush, flush_suit):
    fs = flush_suit[s]
    if fs >= 0:
        return flush[(m >> (16 * fs)) & 0x1FFF]
    return nonflush[k]


@nb.njit(parallel=True, cache=True)
def mc_kernel(triples, class_combos, class_n, n_samples, seed,
              nonflush, flush, flush_suit, rank_keys, suit_keys):
    T = triples.shape[0]
    shares = np.zeros((T, 3), np.float64)
    pairs = np.zeros((T, 3), np.float64)
    counts = np.zeros(T, np.int64)
    RK = np.empty(52, np.int64)
    SK = np.empty(52, np.int64)
    MB = np.empty(52, np.int64)
    for c in range(52):
        RK[c] = rank_keys[c >> 2]
        SK[c] = suit_keys[c & 3]
        MB[c] = np.int64(1) << ((c & 3) * 16 + (c >> 2))
    for t in nb.prange(T):
        a, b, c = triples[t, 0], triples[t, 1], triples[t, 2]
        valid = np.empty((1728, 6), np.int64)
        nv = 0
        for i in range(class_n[a]):
            x1, x2 = class_combos[a, i, 0], class_combos[a, i, 1]
            for j in range(class_n[b]):
                y1, y2 = class_combos[b, j, 0], class_combos[b, j, 1]
                if y1 == x1 or y1 == x2 or y2 == x1 or y2 == x2:
                    continue
                for k in range(class_n[c]):
                    z1, z2 = class_combos[c, k, 0], class_combos[c, k, 1]
                    if z1 == x1 or z1 == x2 or z2 == x1 or z2 == x2:
                        continue
                    if z1 == y1 or z1 == y2 or z2 == y1 or z2 == y2:
                        continue
                    valid[nv, 0] = x1
                    valid[nv, 1] = x2
                    valid[nv, 2] = y1
                    valid[nv, 3] = y2
                    valid[nv, 4] = z1
                    valid[nv, 5] = z2
                    nv += 1
        counts[t] = nv
        if nv == 0:
            continue
        st = np.empty(1, np.uint64)
        z = np.uint64(seed) + np.uint64(t + 1) * np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        st[0] = (z ^ (z >> np.uint64(31))) | np.uint64(1)
        m0 = 0.0
        m1 = 0.0
        m2 = 0.0
        p01 = 0.0
        p02 = 0.0
        p12 = 0.0
        for s in range(n_samples):
            v = s % nv
            h0, h1, h2, h3, h4, h5 = valid[v, 0], valid[v, 1], valid[v, 2], valid[v, 3], valid[v, 4], valid[v, 5]
            used = MB[h0] | MB[h1] | MB[h2] | MB[h3] | MB[h4] | MB[h5]
            kb = 0
            sb = 0
            mb = 0
            got = 0
            while got < 5:
                card = np.int64(_next(st) >> np.uint64(58))  # 0..63
                if card >= 52:
                    continue
                bit = MB[card]
                if used & bit:
                    continue
                used |= bit
                kb += RK[card]
                sb += SK[card]
                mb |= bit
                got += 1
            va = _val(kb + RK[h0] + RK[h1], sb + SK[h0] + SK[h1], mb | MB[h0] | MB[h1], nonflush, flush, flush_suit)
            vb = _val(kb + RK[h2] + RK[h3], sb + SK[h2] + SK[h3], mb | MB[h2] | MB[h3], nonflush, flush, flush_suit)
            vc = _val(kb + RK[h4] + RK[h5], sb + SK[h4] + SK[h5], mb | MB[h4] | MB[h5], nonflush, flush, flush_suit)
            best = va
            if vb > best:
                best = vb
            if vc > best:
                best = vc
            nw = (va == best) + (vb == best) + (vc == best)
            inc = 1.0 / nw
            if va == best:
                m0 += inc
            if vb == best:
                m1 += inc
            if vc == best:
                m2 += inc
            if va > vb:
                p01 += 1.0
            elif va == vb:
                p01 += 0.5
            if va > vc:
                p02 += 1.0
            elif va == vc:
                p02 += 0.5
            if vb > vc:
                p12 += 1.0
            elif vb == vc:
                p12 += 0.5
        shares[t, 0] = m0 / n_samples
        shares[t, 1] = m1 / n_samples
        shares[t, 2] = m2 / n_samples
        pairs[t, 0] = p01 / n_samples
        pairs[t, 1] = p02 / n_samples
        pairs[t, 2] = p12 / n_samples
    return shares, pairs, counts


@nb.njit(parallel=True, cache=True)
def exact_combo_triples(combos6, nonflush, flush, flush_suit, rank_keys, suit_keys):
    """Exact 3-way main shares for explicit combo triples (rows of 6 cards), all C(46,5) boards."""
    T = combos6.shape[0]
    out = np.zeros((T, 3), np.float64)
    for t in nb.prange(T):
        h = combos6[t]
        deck = np.empty(46, np.int64)
        n = 0
        for card in range(52):
            ok = True
            for q in range(6):
                if h[q] == card:
                    ok = False
            if ok:
                deck[n] = card
                n += 1
        vals = np.empty(3, np.int64)
        m0 = 0.0
        m1 = 0.0
        m2 = 0.0
        tot = 0
        for i1 in range(42):
            for i2 in range(i1 + 1, 43):
                for i3 in range(i2 + 1, 44):
                    for i4 in range(i3 + 1, 45):
                        for i5 in range(i4 + 1, 46):
                            for p in range(3):
                                kk = rank_keys[h[2 * p] >> 2] + rank_keys[h[2 * p + 1] >> 2]
                                ss = suit_keys[h[2 * p] & 3] + suit_keys[h[2 * p + 1] & 3]
                                mm = (np.int64(1) << ((h[2 * p] & 3) * 16 + (h[2 * p] >> 2))) | \
                                     (np.int64(1) << ((h[2 * p + 1] & 3) * 16 + (h[2 * p + 1] >> 2)))
                                for d in (deck[i1], deck[i2], deck[i3], deck[i4], deck[i5]):
                                    kk += rank_keys[d >> 2]
                                    ss += suit_keys[d & 3]
                                    mm |= np.int64(1) << ((d & 3) * 16 + (d >> 2))
                                vals[p] = _val(kk, ss, mm, nonflush, flush, flush_suit)
                            best = max(vals[0], max(vals[1], vals[2]))
                            nw = (vals[0] == best) + (vals[1] == best) + (vals[2] == best)
                            if vals[0] == best:
                                m0 += 1.0 / nw
                            if vals[1] == best:
                                m1 += 1.0 / nw
                            if vals[2] == best:
                                m2 += 1.0 / nw
                            tot += 1
        out[t, 0] = m0 / tot
        out[t, 1] = m1 / tot
        out[t, 2] = m2 / tot
    return out


def all_triples():
    a, b, c = np.meshgrid(np.arange(169), np.arange(169), np.arange(169), indexing="ij")
    m = (a <= b) & (b <= c)
    return np.stack([a[m], b[m], c[m]], axis=1).astype(np.int64)


PERM6 = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]


def expand(triples, shares, pairs, counts):
    n = 169
    N3 = np.zeros((n, n, n), np.int32)
    Es = np.zeros((n, n, n), np.float64)
    Ps = np.zeros((n, n, n), np.float64)
    W = np.zeros((n, n, n), np.float64)

    def pshare(i, j):  # share of player i vs player j
        if (i, j) == (0, 1):
            return pairs[:, 0]
        if (i, j) == (0, 2):
            return pairs[:, 1]
        if (i, j) == (1, 2):
            return pairs[:, 2]
        return 1.0 - pshare(j, i)

    for (i, j, k) in PERM6:
        x, y, z = triples[:, i], triples[:, j], triples[:, k]
        N3[x, y, z] = counts
        np.add.at(Es, (x, y, z), shares[:, i])
        np.add.at(Ps, (x, y, z), pshare(i, j))
        np.add.at(W, (x, y, z), 1.0)
    E3 = np.where(W > 0, Es / np.maximum(W, 1), 0.0)
    P3 = np.where(W > 0, Ps / np.maximum(W, 1), 0.0)
    E3[N3 == 0] = 0.0
    P3[N3 == 0] = 0.0
    return N3, E3.astype(np.float32), P3.astype(np.float32)


def compute(n_samples=6000, seed=20261015, limit=None):
    tri = all_triples()
    if limit:
        tri = tri[:limit]
    t0 = time.perf_counter()
    shares, pairs, counts = mc_kernel(tri, CLASS_COMBOS, CLASS_NCOMBOS, n_samples, seed,
                                      NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS)
    dt = time.perf_counter() - t0
    print(f"{len(tri)} class triples x {n_samples} samples in {dt:.1f}s", flush=True)
    if limit:
        return tri, shares, pairs, counts
    N3, E3, P3 = expand(tri, shares, pairs, counts)
    np.savez_compressed(OUT, N3=N3, E3=E3, P3=P3, n_samples=n_samples, seed=seed)
    print("saved", OUT, flush=True)
    return N3, E3, P3


if __name__ == "__main__":
    ns = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    compute(ns, limit=lim)
