"""Cross-check the table evaluator against an independent brute-force (best of 21) evaluator."""
import random
import time

import numpy as np

from solver.evaluator import (FLUSH, FLUSH_SUIT, NONFLUSH, RANK_KEYS, SUIT_KEYS, category, eval7,
                              reference_value_tuple_7)


def main(n=60000, seed=1):
    rng = random.Random(seed)
    hands = []
    # random hands plus hands biased toward flushes/straights/full houses
    for i in range(n):
        if i % 3 == 0:
            s = rng.randrange(4)
            pool = [r * 4 + s for r in range(13)]
            k = rng.choice([5, 6, 7])
            cards = rng.sample(pool, k)
            rest = [c for c in range(52) if c not in cards]
            cards += rng.sample(rest, 7 - k)
        elif i % 3 == 1:
            ranks = rng.sample(range(13), 3)
            cards = []
            deck = list(range(52))
            rng.shuffle(deck)
            for c in deck:
                if c // 4 in ranks and len(cards) < 6:
                    cards.append(c)
            rest = [c for c in range(52) if c not in cards]
            cards += rng.sample(rest, 7 - len(cards))
        else:
            cards = rng.sample(range(52), 7)
        hands.append(cards)
    vals = [int(eval7(np.array(h, dtype=np.int64), NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS)) for h in hands]
    refs = [reference_value_tuple_7(h) for h in hands]
    # 1) same tuple <=> same value; ordering consistent
    by_tuple = {}
    for v, t in zip(vals, refs):
        if t in by_tuple and by_tuple[t] != v:
            raise AssertionError(f"tuple {t} maps to two values")
        by_tuple[t] = v
    items = sorted(by_tuple.items())
    for (t1, v1), (t2, v2) in zip(items, items[1:]):
        assert v1 < v2, (t1, v1, t2, v2)
    # 2) category agrees
    for v, t in zip(vals, refs):
        assert category(v) == t[0], (v, t)
    cats = np.bincount([t[0] for t in refs], minlength=9)
    print("ok:", len(hands), "hands,", len(by_tuple), "distinct values; categories:", cats.tolist())

    # speed
    arr = np.array(hands * 20, dtype=np.int64)
    from numba import njit

    @njit(cache=False)
    def bench(a, nf, f, fs, rk, sk):
        t = 0
        for i in range(a.shape[0]):
            t += eval7(a[i], nf, f, fs, rk, sk)
        return t
    bench(arr[:10], NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS)
    t0 = time.perf_counter()
    bench(arr, NONFLUSH, FLUSH, FLUSH_SUIT, RANK_KEYS, SUIT_KEYS)
    dt = time.perf_counter() - t0
    print(f"speed: {len(arr) / dt / 1e6:.1f} M evals/s (single thread, random hands)")


if __name__ == "__main__":
    main()
