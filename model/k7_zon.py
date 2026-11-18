"""Kaart 7: Zonne-opwek, alle opwek in de buurt. Type C: N = jaaropwek, E = deel van het jaar op deze dag, Σ v = −1.

N = huidige opwek + extra opwek, elk bij woningen en bij niet-woningen (overige daken). Extra = resterende
dakpotentie (Zonnedakje, apart voor woningen en niet-woningen) × benutting (%, apart instelbaar). E = I_ref ÷ I_jaar: de opwek volgt de instraling. Kaart 1
(woningen) en kaart 6 (bedrijven) bevatten alleen verbruik; de huidige zon is hier een vaste basis.
"""
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, checks_standaard, instraling_dag, nl, p_kw, zonvorm


def opwek_dag(p, dag) -> tuple[np.ndarray, float, float, np.ndarray]:
    """Instraling, I_ref, deel van de jaaropwek op deze dag en verloop."""
    I = dag["I"].to_numpy(float)
    i_ref = instraling_dag(I)
    return I, i_ref, i_ref / p["i_jaar"], zonvorm(I)


DELEN = ("huidig woningen", "huidig niet-woningen", "extra woningen", "extra niet-woningen")


@dataclass
class Resultaat:
    N: float         # totale jaaropwek in de buurt, kWh/jaar
    delen: dict      # onderdeel -> jaaropwek, kWh/jaar (zie DELEN)
    potentie: dict   # woningen / niet-woningen -> resterende dakpotentie, kWh/jaar
    benutting: dict  # woningen / niet-woningen -> % van de potentie
    I: np.ndarray
    i_ref: float
    E: float         # deel van de jaaropwek op deze dag
    v: np.ndarray
    P: np.ndarray
    per_kwp: np.ndarray  # kW per kWp (negatief = opwek), voor de thuisbatterij
    checks: list[Check]
    P_delen: dict = None  # onderdeel -> P[t]


def bereken(b, p, dag) -> Resultaat:
    potentie = {"woningen": float(b["zon_potentie_woningen_kwh_jaar"]),
                "niet-woningen": float(b["zon_potentie_overig_kwh_jaar"])}
    benutting = {"woningen": float(b["zon_benutting_woningen_pct"]), "niet-woningen": float(b["zon_benutting_overig_pct"])}
    delen = {DELEN[0]: float(b["zon_kwh_jaar"]), DELEN[1]: float(b["zon_bedrijven_kwh_jaar"]),
             **{f"extra {s}": potentie[s] * benutting[s] / 100 for s in potentie}}
    N = sum(delen.values())
    I, i_ref, E, v = opwek_dag(p, dag)
    P = p_kw(N, E, v)
    P_delen = {k: p_kw(n, E, v) for k, n in delen.items()}
    som = np.sum(list(P_delen.values()), axis=0)
    checks = checks_standaard(P, N, E, v, -1) + [
        Check("Deel van de jaaropwek op deze dag tussen 0 en 100 %", f"{nl(E * 100, 3)} %", "0 tot 100",
              -TOL <= E <= 1 + TOL),
        Check("Totaal = som van huidig en extra, woningen en niet-woningen", f"{nl(som.sum() / 4)} kWh", f"{nl(P.sum() / 4)} kWh",
              abs(som.sum() - P.sum()) <= TOL * max(1, abs(P.sum()))),
    ]
    return Resultaat(N, delen, potentie, benutting, I, i_ref, E, v, P, p_kw(p["zon_opbrengst"], E, v), checks, P_delen)
