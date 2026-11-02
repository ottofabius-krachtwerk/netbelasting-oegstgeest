"""Kaart 7: Zonne-opwek. Type C: E > 0, Σ v = −1. E = Y_jaar × I_ref ÷ I_jaar."""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, instraling_dag, nl, p_kw, zonvorm


def e_zon_bruto(b, p) -> float:
    """Bruto jaaropwek van de huidige zon bij woningen (correctie op kaart 1)."""
    return b["kwp_woningen"] * p["zon_opbrengst"]


@dataclass
class Resultaat:
    N: float
    n_huidig: float
    I: np.ndarray
    i_ref: float
    E: float
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, dag) -> Resultaat:
    n_huidig = float(b["kwp_woningen"])
    N = n_huidig * (1 + p["zon_groei"] / 100)
    I = dag["I"].to_numpy(float)
    i_ref = instraling_dag(I)
    E = p["zon_opbrengst"] * i_ref / p["i_jaar"]
    v = zonvorm(I)
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, -1) + [
        Check("E ≤ I_ref (PR ≤ 1)", f"{nl(E, 3)} kWh/kWp", f"≤ {nl(i_ref, 3)}", E <= i_ref),
    ]
    return Resultaat(N, n_huidig, I, i_ref, E, v, P, checks)
