"""Kaart 1: Woningen basis, het huidige bruto huishoudelijke verbruik. P = 4·N·E·v.

E = E_jaar × d en v = f ÷ d (NEDU-profiel), E_jaar = netto + bruto zon − thuisladen huidige EV's (inclusief de huidige
warmtepompen; de andere kaarten rekenen alleen de toename). De zon telt hier alleen mee als jaargetal om van netto naar
bruto te gaan; alle opwek (ook de huidige) staat in kaart 7. Zo is het profiel te schalen met een groeifactor.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model.common import Check, checks_standaard, dagfractie, nl, p_kw
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
    P: np.ndarray           # bruto huishoudelijk verbruik, kW
    e_dag: float            # dagenergie, kWh
    checks: list[Check]
    e_ev_thuis: float = 0.0  # thuisladen huidige EV's per jaar, kWh
    ev_huidig: float = 0.0   # huidige EV's in de buurt (stand 2025)
    netneutraal: float = 0.0  # extra netneutrale woningen: tellen niet mee in N en hebben geen netbelasting


def bereken(b, p, prof) -> Resultaat:
    types = pd.DataFrame([{"woningtype": w, "woningen": float(b[f"woningen_{k}"]), "nu": float(b.get(f"woningen_{k}_nu", b[f"woningen_{k}"])),
                           "e_netto_kwh_per_woning": p[f"e_netto_{k}"]} for w, k in WONINGTYPEN.items()])
    types["e_netto_kwh"] = types["woningen"] * types["e_netto_kwh_per_woning"]
    N = float(types["woningen"].sum())
    e_netto = float(types["e_netto_kwh"].sum())
    e_zon = float(b["zon_kwh_jaar"])  # bruto jaaropwek huidige panelen bij woningen (Zonnedakje)
    # thuisladen van de huidige EV's zit in het netto verbruik; kaart 4 rekent alle EV's, dus hier eraf
    e_ev_thuis = float(b["ev_huidig"]) * p["ev_e_dag"] * 365 * (1 - p["publiek_aandeel"] / 100)
    e_jaar_buurt = e_netto + e_zon - e_ev_thuis
    e_jaar = e_jaar_buurt / N
    f = prof["nedu_e1a"].to_numpy(float)
    d = dagfractie(f)
    E = e_jaar * d
    v = f / d
    P = p_kw(N, E, v)
    e_dag = N * E
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Huishoudelijk jaarverbruik positief (E_jaar > 0)", f"{nl(e_jaar_buurt)} kWh", "> 0", e_jaar_buurt > 0),
    ]
    return Resultaat(N, types, e_netto, e_zon, e_jaar_buurt, e_jaar, d, f, E, v, P, e_dag, checks, e_ev_thuis=e_ev_thuis,
                     ev_huidig=float(b["ev_huidig"]), netneutraal=float(b.get("extra_netneutraal", 0.0)))
