"""Kaart 7: Zonne-opwek, alleen de toename. Type C: N = extra jaaropwek, E = deel van het jaar op deze dag, Σ v = −1.

N = resterende dakpotentie van de buurt (alle daken, Zonnedakje) × benutting (%). E = I_ref ÷ I_jaar: de opwek volgt
de instraling. De huidige zon telt in kaart 1 (woningen) en kaart 6 (bedrijven).
"""
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, checks_standaard, instraling_dag, nl, p_kw, zonvorm


def opwek_dag(p, dag) -> tuple[np.ndarray, float, float, np.ndarray]:
    """Instraling, I_ref, deel van de jaaropwek op deze dag en verloop; gedeeld door kaart 1, 7 en 8."""
    I = dag["I"].to_numpy(float)
    i_ref = instraling_dag(I)
    return I, i_ref, i_ref / p["i_jaar"], zonvorm(I)


@dataclass
class Resultaat:
    N: float         # extra jaaropwek in de buurt, kWh/jaar
    potentie: float  # resterende dakpotentie, kWh/jaar
    benutting: float  # % van de potentie
    I: np.ndarray
    i_ref: float
    E: float         # deel van de jaaropwek op deze dag
    v: np.ndarray
    P: np.ndarray
    per_kwp: np.ndarray  # kW per kWp (negatief = opwek), voor de thuisbatterij
    checks: list[Check]


def bereken(b, p, dag) -> Resultaat:
    potentie, benutting = float(b["zon_potentie_kwh_jaar"]), float(b["zon_benutting_pct"])
    N = potentie * benutting / 100
    I, i_ref, E, v = opwek_dag(p, dag)
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, -1) + [
        Check("Deel van de jaaropwek op deze dag tussen 0 en 100 %", f"{nl(E * 100, 3)} %", "0 tot 100",
              -TOL <= E <= 1 + TOL),
    ]
    return Resultaat(N, potentie, benutting, I, i_ref, E, v, P, p_kw(p["zon_opbrengst"], E, v), checks)
