"""Kaart 4: Laden personenauto's, alleen de extra EV's. v = (1 − a) × v_ongestuurd + a × v_slim.

Het laden van de huidige EV's zit in het netto verbruik van kaart 1 (woningen basis).
"""
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, checks_standaard, nl, p_kw, vorm


@dataclass
class Resultaat:
    N: float
    E: float
    a: float
    v_ongestuurd: np.ndarray
    v_slim: np.ndarray
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    N = float(b["ev_extra"])  # toename per buurt, aantal extra EV's (invoer)
    E = p["ev_e_dag"]
    a = p["slim_aandeel"] / 100
    vo, vs = vorm(prof["ev_ongestuurd"]), vorm(prof["ev_slim"])
    v = (1 - a) * vo + a * vs
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Ongestuurd verloop telt op tot 100 % (Σ v_ongestuurd)", nl(vo.sum(), 6), "1", abs(vo.sum() - 1) <= TOL),
        Check("Slim verloop telt op tot 100 % (Σ v_slim)", nl(vs.sum(), 6), "1", abs(vs.sum() - 1) <= TOL),
    ]
    return Resultaat(N, E, a, vo, vs, v, P, checks)
