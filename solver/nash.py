"""Push/fold Nash equilibrium (chip EV) for an N-handed table, hand-class strategies.

Game
  * Everyone starts the hand with the same stack S (big blinds, before posting).
  * Posts: SB, BB and antes - none, classic (every player) or BB ante (the big blind pays it).
    Antes are dead money; a player's live stack (max contribution, blind included) is S - ante paid,
    so with a BB ante the big blind is effectively S - ante deep.
  * Folded to position j: push all-in or fold. Players behind act in order: call or fold.
    Up to `max_callers` callers (1 or 2); once that many have called, everyone else folds.

Because only "folded to j" matters for j's decision, every pusher position is an independent
subgame: pusher j + callers behind. Each subgame is solved by fictitious play with linearly
weighted averaging (best responses against the running-average strategies, iteration t weighted
by t) until the exploitability is tiny.

Card removal: every conditional hand distribution uses exact combo counts (N2 for two players,
N3 for three). Calling decisions of different players are treated as independent given the
hero's hand, and folded players' cards are ignored - the standard simplifications of
push/fold Nash calculators.
"""
import os
from dataclasses import dataclass

import numpy as np

from solver.cards import CLASS_NCOMBOS

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


@dataclass
class Game:
    n: int = 9
    stack: float = 10.0
    sb: float = 0.5
    bb: float = 1.0
    ante_type: str = "bb"  # 'none' | 'classic' | 'bb'
    ante: float = 1.0      # classic: per player; bb: paid by the big blind
    max_callers: int = 2

    def __post_init__(self):
        n = self.n
        self.SB, self.BB = n - 2, n - 1
        self.blind = np.zeros(n)
        self.blind[self.SB] = self.sb
        self.blind[self.BB] = self.bb
        self.ante_paid = np.zeros(n)
        if self.ante_type == "classic":
            self.ante_paid[:] = self.ante
        elif self.ante_type == "bb":
            self.ante_paid[self.BB] = self.ante
        elif self.ante_type != "none":
            raise ValueError(self.ante_type)
        self.live = self.stack - self.ante_paid
        assert (self.live > self.blind).all(), "stack too short for this model"
        self.fold_value = self.stack - self.ante_paid - self.blind
        self.total_antes = float(self.ante_paid.sum())

    def dead(self, parts):
        return self.total_antes + sum(self.blind[i] for i in range(self.n) if i not in parts)

    def steal_value(self, j):
        """Final stack of pusher j when everybody folds."""
        return self.live[j] + self.dead((j,))

    def two_way(self, a, b):
        """(returned, pot) for each of the two all-in players."""
        m = min(self.live[a], self.live[b])
        pot = 2 * m + self.dead((a, b))
        return (self.live[a] - m, pot), (self.live[b] - m, pot)

    def three_way(self, parts):
        """Per role: (returned, main pot, side pot, role of the side-pot opponent or None)."""
        L = [self.live[i] for i in parts]
        order = sorted(range(3), key=lambda r: (L[r], r))
        l1, l2, l3 = (L[r] for r in order)
        main = 3 * l1 + self.dead(parts)
        side = 2 * (l2 - l1)
        out = []
        for r in range(3):
            ret = (l3 - l2) if r == order[2] else 0.0
            if r == order[0]:
                out.append((ret, main, 0.0, None))
            else:
                out.append((ret, main, side, order[2] if r == order[1] else order[1]))
        return out


class Equity:
    def __init__(self, with3=True, eq3_file="eq3.npz"):
        z = np.load(os.path.join(DATA, "eq2.npz"))
        self.N2 = z["N2"].astype(np.float64)
        self.EQ2 = np.nan_to_num(z["EQ2"])
        self.nh = CLASS_NCOMBOS.astype(np.float64)
        self.Pv = self.N2 / (self.nh[:, None] * 1225.0)  # P(villain class | hero class)
        self.with3 = with3
        if with3:
            z3 = np.load(os.path.join(DATA, eq3_file))
            N3 = z3["N3"].astype(np.float32)  # symmetric under any permutation of its axes
            # sanity: given two hands, the third comes from the C(48,2) = 1128 combos of the remaining cards
            assert np.array_equal(z3["N3"].sum(2, dtype=np.int64), z["N2"].astype(np.int64) * 1128)
            N3E = N3 * z3["E3"]               # [x, y, z]: x's share of the 3-way pot
            N3P = N3 * z3["P3"]               # [x, y, z]: x's share vs y, z's cards dead
            # layouts with the contracted class on the first axis (contiguous gathers + BLAS):
            self.N3 = N3                                                   # [z, x, y]
            self.TEx = np.ascontiguousarray(N3E.transpose(2, 0, 1))        # [z, x, y] = N3E[x, y, z]
            self.TEy = np.ascontiguousarray(N3E.transpose(2, 1, 0))        # [z, x, y] = N3E[y, x, z]
            self.TP = np.ascontiguousarray(N3P.transpose(2, 0, 1))         # [z, x, y] = N3P[x, y, z]
            # P(z | x, y) = N3[x, y, z] / (N2[x, y] * C(48, 2)): the third player's combos come from the
            # 48 cards left after the two known hands
            with np.errstate(divide="ignore"):
                self.inv_N2_1128 = np.where(self.N2 > 0, 1.0 / (self.N2 * 1128.0), 0.0)
        # hand strength vs a random hand, used only for the initial strategies
        self.strength = (self.N2 * self.EQ2).sum(1) / (self.nh * 1225.0)


def _support(s, eps=1e-9):
    return np.nonzero(s > eps)[0]


def _contract(T, w):
    """sum_z w(z) T[z] over the first axis, skipping zero weights (float64 result)."""
    S = _support(w)
    if len(S) == 0:
        return np.zeros(T.shape[1:])
    return np.tensordot(w[S].astype(np.float32), T[S], 1).astype(np.float64)


class _Running:
    """Keeps val[i] = sum_z w(z) T_i[z] while w is updated as w <- (1 - a) w + a * br (br 0/1).
    The sum over the best-response set is itself updated incrementally, so an iteration only
    touches the tensor slices of hands that entered or left the best response."""

    def __init__(self, tensors, w):
        self.T = tensors
        self.reset(w)

    def reset(self, w):
        self.val = [_contract(T, w) for T in self.T]
        self.br = None
        self.brsum = None

    def update(self, a, br):
        b = br > 0.5
        if self.br is None:
            self.brsum = [_contract(T, b.astype(np.float64)) for T in self.T]
        else:
            add = np.nonzero(b & ~self.br)[0]
            rem = np.nonzero(~b & self.br)[0]
            for i, T in enumerate(self.T):
                if len(add):
                    self.brsum[i] += T[add].sum(0, dtype=np.float64)
                if len(rem):
                    self.brsum[i] -= T[rem].sum(0, dtype=np.float64)
        self.br = b
        self.val = [(1.0 - a) * v + a * bs for v, bs in zip(self.val, self.brsum)]


class PusherSubgame:
    """Pusher position j and all players behind it."""

    def __init__(self, eq, game, j):
        self.eq, self.g, self.j = eq, game, j
        self.K = list(range(j + 1, game.n))
        self.mc = game.max_callers if (len(self.K) >= 2 and eq.with3) else 1
        self.pairs = [(k, m) for a, k in enumerate(self.K) for m in self.K[a + 1:]] if self.mc >= 2 else []
        g = game
        self.hu = {k: g.two_way(j, k) for k in self.K}
        self.tw = {(k, m): g.three_way((j, k, m)) for (k, m) in self.pairs}
        for (k, m), coefs in self.tw.items():
            # side pots can only be contested by pusher and first caller (BB-ante short BB is always last)
            assert coefs[2][2] == 0.0, "unsupported side-pot layout"
            if coefs[0][2] > 0:
                assert coefs[0][3] == 1 and coefs[1][3] == 0

    def init_strategies(self):
        order = np.argsort(-self.eq.strength)
        cum = np.cumsum(self.eq.nh[order]) / 1326.0

        def top(frac):
            s = np.zeros(169)
            s[order[cum <= frac]] = 1.0
            s[order[0]] = 1.0
            return s
        p = top(0.35)
        c1 = {k: top(0.15) for k in self.K}
        c2 = {km: top(0.04) for km in self.pairs}
        return p, c1, c2

    def contractions(self, c1, c2):
        """From scratch: G[km] = sum_z c2[km](z) T[z] for T in (N3, TEx, TEy, TP), and
        M[k] = sum_y c1[k](y) T[y] for T in (N3, TEx) (second-caller weights)."""
        eq = self.eq
        G = {km: tuple(_contract(T, c2[km]) for T in (eq.N3, eq.TEx, eq.TEy, eq.TP)) for km in self.pairs}
        M = {k: tuple(_contract(T, c1[k]) for T in (eq.N3, eq.TEx)) for k in self.K if self.pairs}
        return G, M

    def evs(self, p, c1, c2, G=None, M=None):
        eq, g, j, K = self.eq, self.g, self.j, self.K
        N2, EQ2, Pv = eq.N2, eq.EQ2, eq.Pv
        if self.pairs and (G is None or M is None):
            G, M = self.contractions(c1, c2)
        inner_push = {}
        inner_call = {}
        for k in K:
            (ret_j, pot), (ret_k, _) = self.hu[k]
            B = np.ones((169, 169))
            acc_p = np.zeros((169, 169))
            acc_c = np.zeros((169, 169))
            for m in (K if self.pairs else ()):
                if m <= k:
                    continue
                Gc, GEx, GEy, GP = G[(k, m)]
                gprob = Gc * eq.inv_N2_1128
                (rj, mainj, sidej, _), (rk, maink, sidek, _), _ = self.tw[(k, m)]
                tp = (rj * Gc + mainj * GEx + sidej * GP) * eq.inv_N2_1128
                tc = (rk * Gc + maink * GEy + sidek * (Gc - GP)) * eq.inv_N2_1128
                acc_p += B * tp
                acc_c += B * tc
                B = B * (1.0 - gprob)
            inner_push[k] = B * (ret_j + pot * EQ2) + acc_p          # pusher x (rows) vs caller y (cols)
            inner_call[k] = B * (ret_k + pot * (1.0 - EQ2)) + acc_c  # caller y's value, same layout
        # --- pusher
        A = np.ones(169)
        ev_push = np.zeros(169)
        for k in K:
            f = Pv @ c1[k]
            term = (inner_push[k] * Pv * c1[k][None, :]).sum(1)
            ev_push += A * term
            A = A * (1.0 - f)
        ev_push += A * g.steal_value(j)
        # --- first callers
        ev_c1 = {}
        wp = p[:, None] * N2  # [x, y]
        Z = wp.sum(0)
        for k in K:
            num = (wp * inner_call[k]).sum(0)
            with np.errstate(invalid="ignore", divide="ignore"):
                ev_c1[k] = np.where(Z > 0, num / np.maximum(Z, 1e-300), -1e9)
        # --- second callers
        ev_c2 = {}
        if self.pairs:
            for k in K:
                ms = [m for m in K if m > k]
                if not ms:
                    continue
                MW, ME = M[k]
                W = MW @ p   # sum_x,y p(x) c1(y) N3[z, x, y]
                E = ME @ p   # ... times z's 3-way share
                for m in ms:
                    _, _, (rm, mainm, sidem, _) = self.tw[(k, m)]
                    assert sidem == 0.0
                    with np.errstate(invalid="ignore", divide="ignore"):
                        ev_c2[(k, m)] = np.where(W > 0, rm + mainm * E / np.maximum(W, 1e-300), -1e9)
        return ev_push, ev_c1, ev_c2

    def solve(self, iters=3000, tol=1e-4, check_every=100, verbose=False, init=None):
        g, j, K, eq = self.g, self.j, self.K, self.eq
        p, c1, c2 = init if init is not None else self.init_strategies()
        p = p.copy()
        c1 = {k: v.copy() for k, v in c1.items()}
        c2 = {k: v.copy() for k, v in c2.items() if k in self.pairs}
        for km in self.pairs:
            c2.setdefault(km, np.zeros(169))
        # running contractions, kept equal to sum_z avg(z) T[z] by applying the same updates
        lin2 = {km: _Running((eq.N3, eq.TEx, eq.TEy, eq.TP), c2[km]) for km in self.pairs}
        lin1 = {k: _Running((eq.N3, eq.TEx), c1[k]) for k in K} if self.pairs else {}
        hist = []
        t = 0
        for t in range(1, iters + 1):
            G = {km: lin2[km].val for km in self.pairs}
            M = {k: lin1[k].val for k in lin1}
            ev_p, ev_1, ev_2 = self.evs(p, c1, c2, G=G, M=M)
            a = 2.0 / (t + 2)
            p += a * ((ev_p > g.fold_value[j]).astype(float) - p)
            for k in K:
                br = (ev_1[k] > g.fold_value[k]).astype(float)
                c1[k] += a * (br - c1[k])
                if k in lin1:
                    lin1[k].update(a, br)
            for (k, m) in self.pairs:
                br = (ev_2[(k, m)] > g.fold_value[m]).astype(float)
                c2[(k, m)] += a * (br - c2[(k, m)])
                lin2[(k, m)].update(a, br)
            if t % 200 == 0:  # wash out floating-point drift
                for km, r in lin2.items():
                    r.reset(c2[km])
                for k, r in lin1.items():
                    r.reset(c1[k])
            if t % check_every == 0 or t == iters:
                expl = self.exploitability(p, c1, c2)
                hist.append((t, expl))
                if verbose:
                    print(f"  it {t}: exploitability {expl:.6f}", flush=True)
                if expl < tol:
                    break
        return dict(p=p, c1=c1, c2=c2, iters=t, history=hist,
                    exploitability=self.exploitability(p, c1, c2))

    def exploitability(self, p, c1, c2):
        """Max over decisions of the gain (bb, weighted by hand frequency) from best-responding."""
        g, j = self.g, self.j
        ev_p, ev_1, ev_2 = self.evs(p, c1, c2)
        w = self.eq.nh / 1326.0

        def gain(s, ev, fold):
            ev = np.where(ev < -1e8, fold, ev)
            best = np.maximum(ev, fold)
            cur = s * ev + (1 - s) * fold
            return float((w * (best - cur)).sum())
        out = [gain(p, ev_p, g.fold_value[j])]
        out += [gain(c1[k], ev_1[k], g.fold_value[k]) for k in self.K]
        out += [gain(c2[km], ev_2[km], g.fold_value[km[1]]) for km in ev_2]
        return max(out)

    def report(self, sol):
        """Strategies plus EV(action) - EV(fold) per class against the final strategies."""
        g, j = self.g, self.j
        ev_p, ev_1, ev_2 = self.evs(sol["p"], sol["c1"], sol["c2"])
        out = {"push": {"freq": sol["p"], "dev": ev_p - g.fold_value[j]},
               "call": {k: {"freq": sol["c1"][k], "dev": np.where(ev_1[k] < -1e8, np.nan, ev_1[k] - g.fold_value[k])}
                        for k in self.K},
               "overcall": {km: {"freq": sol["c2"][km], "dev": np.where(ev_2[km] < -1e8, np.nan, ev_2[km] - g.fold_value[km[1]])}
                            for km in ev_2}}
        return out


def range_pct(freq):
    return float((freq * CLASS_NCOMBOS).sum() / 1326.0 * 100.0)
