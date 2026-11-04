"""Kaart 1: Woningen basis, de huidige situatie. P = verbruik − huidige zon.

Verbruik: 4·N·E·v met E = E_jaar × d en v = f ÷ d, E_jaar = netto + bruto zon (inclusief de huidige warmtepompen en
EV's; de andere kaarten rekenen alleen de toename). Huidige zon: jaaropwek (Zonnedakje) × deel op deze dag,
zoals kaart 7.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model import k7_zon
from model.common import TOL, Check, checks_standaard, dagfractie, nl, p_kw
from model.data import WONINGTYPEN


@dataclass
class Resultaat:
    N: float
    types: pd.DataFrame  # woningtype, woningen, e_netto_kwh_per_woning, e_netto_kwh
    e_netto: float
    e_zon_bruto: float
    e_jaar_buurt: float
    e_jaar: float
    d: float
    f: np.ndarray
    E: float
    v: np.ndarray
    P_verbruik: np.ndarray  # bruto huishoudelijk verbruik, kW
    f_zon: float            # deel van de jaaropwek op deze dag
    v_zon: np.ndarray       # verloop opwek, Σ = −1
    P_zon: np.ndarray       # opwek huidige zon, kW (negatief)
    P: np.ndarray           # netto: verbruik + opwek
    e_dag: float            # netto dagenergie, kWh
    checks: list[Check]


def bereken(b, p, dag, prof) -> Resultaat:
    types = pd.DataFrame([{"woningtype": w, "woningen": float(b[f"woningen_{k}"]),
                           "e_netto_kwh_per_woning": p[f"e_netto_{k}"]} for w, k in WONINGTYPEN.items()])
    types["e_netto_kwh"] = types["woningen"] * types["e_netto_kwh_per_woning"]
    N = float(types["woningen"].sum())
    e_netto = float(types["e_netto_kwh"].sum())
    e_zon = float(b["zon_kwh_jaar"])  # bruto jaaropwek huidige panelen bij woningen (Zonnedakje)
    e_jaar_buurt = e_netto + e_zon
    e_jaar = e_jaar_buurt / N
    f = prof["nedu_e1a"].to_numpy(float)
    d = dagfractie(f)
    E = e_jaar * d
    v = f / d
    P_verbruik = p_kw(N, E, v)
    _, _, f_zon, v_zon = k7_zon.opwek_dag(p, dag)
    P_zon = p_kw(e_zon, f_zon, v_zon)
    P = P_verbruik + P_zon
    e_dag = N * E - e_zon * f_zon
    checks = checks_standaard(P_verbruik, N, E, v, +1) + [
        Check("Opwek huidige zon: dagtotaal = jaaropwek × deel op deze dag", f"{nl(P_zon.sum() / 4)} kWh",
              f"{nl(-e_zon * f_zon)} kWh", abs(P_zon.sum() / 4 + e_zon * f_zon) <= TOL * max(1, e_zon * f_zon)),
        Check("Netto dagtotaal = verbruik − opwek", f"{nl(P.sum() / 4)} kWh", f"{nl(e_dag)} kWh",
              abs(P.sum() / 4 - e_dag) <= TOL * max(1, abs(e_dag))),
        Check("Bruto jaarverbruik ≥ netto verbruik (E_jaar ≥ E_netto)", f"{nl(e_jaar_buurt)} kWh", f"≥ {nl(e_netto)} kWh",
              e_jaar_buurt >= e_netto - TOL),
        Check("Bruto jaarverbruik positief (E_jaar > 0)", f"{nl(e_jaar_buurt)} kWh", "> 0", e_jaar_buurt > 0),
    ]
    return Resultaat(N, types, e_netto, e_zon, e_jaar_buurt, e_jaar, d, f, E, v, P_verbruik, f_zon,
                     v_zon, P_zon, P, e_dag, checks)
