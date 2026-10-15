"""7-card hand evaluator (numba) built from lookup tables generated here.

Hand value: integer 1..7462, higher is better (all distinct 5-card hand classes).
Non-flush hands: value = NONFLUSH[sum of RANK_KEYS over the 7 cards].
Flush hands: value = FLUSH[13-bit rank mask of the flush suit].
Suit counting: sum of SUIT_KEYS (3 bits per suit); FLUSH_SUIT[sum] gives the flush suit or -1.
A 7-card hand that contains a flush can never contain quads or a full house, so the flush
value is always the best five.
"""
import os
from itertools import combinations

import numba as nb
import numpy as np

RANK_KEYS = np.array([0, 1, 5, 22, 98, 453, 2031, 8698, 22854, 83661, 262349, 636345, 1479181],
                     dtype=np.int64)
SUIT_KEYS = np.array([1, 8, 64, 512], dtype=np.int64)

CATEGORY_NAMES = ["Carta alta", "Par", "Dois pares", "Trinca", "Sequência", "Flush",
                  "Full house", "Quadra", "Straight flush"]


def _straight_high(rankset):
    for h in range(12, 3, -1):
        if all((h - i) in rankset for i in range(5)):
            return h
    if {12, 0, 1, 2, 3} <= rankset:
        return 3
    return None


def value_tuple_from_counts(counts):
    """Best non-flush 5-card hand from rank counts (ranks 0..12 = 2..A)."""
    desc = [r for r in range(12, -1, -1) if counts[r] > 0]
    quads = [r for r in desc if counts[r] == 4]
    trips = [r for r in desc if counts[r] == 3]
    pairs = [r for r in desc if counts[r] == 2]
    if quads:
        q = quads[0]
        return (7, q, max(r for r in desc if r != q))
    if trips and (len(trips) >= 2 or pairs):
        t = trips[0]
        return (6, t, max(trips[1:] + pairs))
    st = _straight_high(set(desc))
    if st is not None:
        return (4, st)
    if trips:
        t = trips[0]
        return (3, t, *[r for r in desc if r != t][:2])
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        return (2, p1, p2, [r for r in desc if r not in (p1, p2)][0])
    if pairs:
        p = pairs[0]
        return (1, p, *[r for r in desc if r != p][:3])
    return (0, *desc[:5])


def value_tuple_from_flush_mask(mask):
    ranks = [r for r in range(12, -1, -1) if mask >> r & 1]
    st = _straight_high(set(ranks))
    if st is not None:
        return (8, st)
    return (5, *ranks[:5])


def value_tuple_5(cards):
    """Reference (slow) value tuple of exactly 5 cards."""
    counts = [0] * 13
    for c in cards:
        counts[c // 4] += 1
    suits = {c % 4 for c in cards}
    if len(suits) == 1:
        mask = 0
        for c in cards:
            mask |= 1 << (c // 4)
        return value_tuple_from_flush_mask(mask)
    return value_tuple_from_counts(counts)


def _rank_multisets(total, max_per_rank=4):
    def rec(r, left):
        if r < 0:
            if left == 0:
                yield ()
            return
        for k in range(min(left, max_per_rank) + 1):
            for rest in rec(r - 1, left - k):
                yield rest + (k,)
    for t in rec(12, total):
        yield list(t)  # index 0 = rank 0


def build_tables():
    tuples = {}
    nonflush_items = []
    for counts in _rank_multisets(7):
        key = int(sum(RANK_KEYS[r] * counts[r] for r in range(13)))
        vt = value_tuple_from_counts(counts)
        nonflush_items.append((key, vt))
        tuples[vt] = None
    flush_items = []
    for mask in range(1 << 13):
        if bin(mask).count("1") >= 5:
            vt = value_tuple_from_flush_mask(mask)
            flush_items.append((mask, vt))
            tuples[vt] = None
    # every 5-card hand class must be present (5-card tuples are a subset of 7-card tuples);
    # add 5-card-only tuples (e.g. 7-high no-pair) so the value scale is the standard 1..7462
    for counts in _rank_multisets(5):
        tuples[value_tuple_from_counts(counts)] = None
    order = sorted(tuples)
    index = {t: i + 1 for i, t in enumerate(order)}
    max_key = max(k for k, _ in nonflush_items)
    nonflush = np.zeros(max_key + 1, dtype=np.uint16)
    seen = {}
    for key, vt in nonflush_items:
        if key in seen and seen[key] != vt:
            raise RuntimeError("rank-key collision")
        seen[key] = vt
        nonflush[key] = index[vt]
    flush = np.zeros(1 << 13, dtype=np.uint16)
    for mask, vt in flush_items:
        flush[mask] = index[vt]
    flush_suit = -np.ones(7 * 512 + 1, dtype=np.int64)
    for s0 in range(8):
        for s1 in range(8):
            for s2 in range(8):
                for s3 in range(8):
                    if s0 + s1 + s2 + s3 > 7:
                        continue
                    key = s0 + 8 * s1 + 64 * s2 + 512 * s3
                    for s, n in enumerate((s0, s1, s2, s3)):
                        if n >= 5:
                            flush_suit[key] = s
    category_start = np.zeros(10, dtype=np.int64)
    for t in order:
        if category_start[t[0]] == 0:
            category_start[t[0]] = index[t]
    category_start[9] = len(order) + 1
    return nonflush, flush, flush_suit, len(order), category_start


_CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "eval_tables.npz")


def load_tables():
    if os.path.exists(_CACHE):
        z = np.load(_CACHE)
        return z["nonflush"], z["flush"], z["flush_suit"], z["category_start"]
    nonflush, flush, flush_suit, n, category_start = build_tables()
    assert n == 7462, n
    os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
    np.savez_compressed(_CACHE, nonflush=nonflush, flush=flush, flush_suit=flush_suit,
                        category_start=category_start)
    return nonflush, flush, flush_suit, category_start


NONFLUSH, FLUSH, FLUSH_SUIT, CATEGORY_START = load_tables()


@nb.njit(cache=True)
def eval7(cards, nonflush, flush, flush_suit, rank_keys, suit_keys):
    k = 0
    s = 0
    bits = 0
    for i in range(7):
        c = cards[i]
        k += rank_keys[c >> 2]
        s += suit_keys[c & 3]
        bits |= 1 << ((c & 3) * 16 + (c >> 2))
    fs = flush_suit[s]
    if fs >= 0:
        return np.int64(flush[(bits >> (16 * fs)) & 0x1FFF])
    return np.int64(nonflush[k])


def evaluate(cards):
    """Convenience wrapper: value of a 7-card hand (list of card ints)."""
    return int(eval7(np.asarray(cards, dtype=np.int64), NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS))


def category(value):
    return int(np.searchsorted(CATEGORY_START[:9], value, side="right") - 1)


def reference_value_tuple_7(cards):
    """Independent brute force: best of the 21 five-card subsets."""
    return max(value_tuple_5(sub) for sub in combinations(cards, 5))
