"""Kaart 2: Elektrisch koken. N = huishoudens × groei in penetratie, E is een dagwaarde."""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, nl, p_kw, vorm


@dataclass
class Resultaat:
    huishoudens: float
    N: float
    E: float
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    N = b["huishoudens"] * p["koken_penetratie_groei"] / 100
    E = p["koken_e_dag"]
    v = vorm(prof["koken"])
    P = p_kw(N, E, v)
    g = p["koken_penetratie_groei"]
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Extra aandeel tussen 0 en 100 %", f"{nl(g)} %", "0 tot 100", 0 <= g <= 100),
    ]
    return Resultaat(float(b["huishoudens"]), N, E, v, P, checks)
