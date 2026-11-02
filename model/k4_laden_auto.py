"""Kaart 4: Laden personenauto's. v = (1 − a) × v_ongestuurd + a × v_slim."""
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, checks_standaard, nl, p_kw, vorm


def n_ev_huidig(b, p) -> float:
    """Huidige BEV in de buurt: gemeentetotaal naar aandeel personenauto's."""
    return p["ev_gemeente_huidig"] * b["personenautos"] / p["autos_gemeente"]


def e_ev_thuis_huidig(b, p) -> float:
    """Jaarenergie van het huidige thuisladen (correctie op kaart 1)."""
    return n_ev_huidig(b, p) * p["ev_jaarenergie"] * p["ev_aandeel_thuis"] / 100


@dataclass
class Resultaat:
    N: float
    n_huidig: float
    n_extra: float
    E: float
    a: float
    v_ongestuurd: np.ndarray
    v_slim: np.ndarray
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    n_huidig = n_ev_huidig(b, p)
    n_extra = b["ev_toename_pct"] / 100 * b["personenautos"]  # toename per buurt, % van de huidige personenauto's
    N = n_huidig + n_extra
    E = p["ev_e_dag"]
    a = p["slim_aandeel"] / 100
    vo, vs = vorm(prof["ev_ongestuurd"]), vorm(prof["ev_slim"])
    v = (1 - a) * vo + a * vs
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Σ v_ongestuurd = 1", nl(vo.sum(), 6), "1", abs(vo.sum() - 1) <= TOL),
        Check("Σ v_slim = 1", nl(vs.sum(), 6), "1", abs(vs.sum() - 1) <= TOL),
        Check("N ≤ personenauto's buurt", nl(N), f"≤ {nl(b['personenautos'])}", N <= b["personenautos"]),
    ]
    return Resultaat(N, n_huidig, n_extra, E, a, vo, vs, v, P, checks)
