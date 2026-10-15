"""Cards, the 1326 hole-card combos and the 169 hand classes.

Card encoding: c = rank * 4 + suit, rank 0..12 = 2..A, suit 0..3 = c d h s.
Hand classes live on the usual 13x13 grid (row/col 0 = Ace ... 12 = Two):
pairs on the diagonal, suited above it (row < col), offsuit below it (row > col).
Class index = row * 13 + col.
"""
from itertools import combinations

import numpy as np

RANKS = "23456789TJQKA"
SUITS = "cdhs"
GRID_RANKS = "AKQJT98765432"


def card_str(c):
    return RANKS[c // 4] + SUITS[c % 4]


def parse_card(s):
    return RANKS.index(s[0].upper()) * 4 + SUITS.index(s[1].lower())


def class_name(i):
    r, c = divmod(i, 13)
    if r == c:
        return GRID_RANKS[r] * 2
    if r < c:
        return GRID_RANKS[r] + GRID_RANKS[c] + "s"
    return GRID_RANKS[c] + GRID_RANKS[r] + "o"


CLASS_NAMES = [class_name(i) for i in range(169)]
CLASS_INDEX = {n: i for i, n in enumerate(CLASS_NAMES)}


def combo_class(c1, c2):
    g1, g2 = 12 - c1 // 4, 12 - c2 // 4
    if g1 == g2:
        return g1 * 13 + g1
    hi, lo = min(g1, g2), max(g1, g2)
    if c1 % 4 == c2 % 4:
        return hi * 13 + lo
    return lo * 13 + hi


COMBOS = np.array(list(combinations(range(52), 2)), dtype=np.int64)  # (1326, 2)
COMBO_CLASS = np.array([combo_class(a, b) for a, b in COMBOS], dtype=np.int64)
CLASS_NCOMBOS = np.bincount(COMBO_CLASS, minlength=169).astype(np.int64)
COMBO_INDEX = {(int(a), int(b)): i for i, (a, b) in enumerate(COMBOS)}

# (169, 12, 2) card pairs per class, padded with -1
CLASS_COMBOS = -np.ones((169, 12, 2), dtype=np.int64)
_fill = np.zeros(169, dtype=np.int64)
for _i, (_a, _b) in enumerate(COMBOS):
    _k = COMBO_CLASS[_i]
    CLASS_COMBOS[_k, _fill[_k]] = (_a, _b)
    _fill[_k] += 1
assert (_fill == CLASS_NCOMBOS).all()
assert CLASS_NCOMBOS.sum() == 1326


def class_type(i):
    r, c = divmod(i, 13)
    return "pair" if r == c else ("suited" if r < c else "offsuit")


def expand_range(text):
    """Expand range notation ('22+, A2s+, KTo+, 65s, T9s-76s, AKo') into a set of class names."""
    out = set()
    for raw in text.replace(";", ",").split(","):
        tok = raw.strip()
        if not tok:
            continue
        if "-" in tok:
            a, b = (t.strip() for t in tok.split("-"))
            out |= _span(a, b)
        elif tok.endswith("+"):
            out |= _plus(tok[:-1])
        else:
            out |= _single(tok)
    return out


def _single(tok):
    if len(tok) == 2 and tok[0] == tok[1]:
        return {tok}
    if len(tok) == 2:
        hi, lo = sorted(tok, key=GRID_RANKS.index)
        return {hi + lo + "s", hi + lo + "o"}
    hi, lo = sorted(tok[:2], key=GRID_RANKS.index)
    return {hi + lo + tok[2]}


def _plus(tok):
    if len(tok) == 2 and tok[0] == tok[1]:
        g = GRID_RANKS.index(tok[0])
        return {GRID_RANKS[i] * 2 for i in range(0, g + 1)}
    hi, lo = tok[0], tok[1]
    suf = tok[2:] or None
    gh, gl = GRID_RANKS.index(hi), GRID_RANKS.index(lo)
    res = set()
    for i in range(gh + 1, gl + 1):
        if suf:
            res.add(hi + GRID_RANKS[i] + suf)
        else:
            res |= {hi + GRID_RANKS[i] + "s", hi + GRID_RANKS[i] + "o"}
    return res


def _span(a, b):
    if len(a) == 2 and a[0] == a[1]:
        ga, gb = sorted((GRID_RANKS.index(a[0]), GRID_RANKS.index(b[0])))
        return {GRID_RANKS[i] * 2 for i in range(ga, gb + 1)}
    suf = a[2:] if len(a) > 2 else None
    if a[0] == b[0]:  # A2s-A5s style
        g1, g2 = sorted((GRID_RANKS.index(a[1]), GRID_RANKS.index(b[1])))
        hands = [a[0] + GRID_RANKS[i] for i in range(g1, g2 + 1)]
    else:  # T9s-76s connector style
        d = GRID_RANKS.index(a[1]) - GRID_RANKS.index(a[0])
        g1, g2 = sorted((GRID_RANKS.index(a[0]), GRID_RANKS.index(b[0])))
        hands = [GRID_RANKS[i] + GRID_RANKS[i + d] for i in range(g1, g2 + 1)]
    res = set()
    for h in hands:
        if suf:
            res.add(h + suf)
        else:
            res |= {h + "s", h + "o"}
    return res
