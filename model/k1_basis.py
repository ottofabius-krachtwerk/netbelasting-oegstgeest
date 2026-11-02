"""Kaart 1: Woningen basis. P = 4·N·E·v met E = E_jaar × d en v = f ÷ d."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model import k3_warmtepomp, k4_laden_auto, k7_zon
from model.common import TOL, Check, checks_standaard, dagfractie, nl, p_kw


@dataclass
class Resultaat:
    N: float
    types: pd.DataFrame  # woningtype, woningen, e_netto_kwh_per_woning, e_netto_kwh
    e_netto: float
    e_zon_bruto: float
    e_wp_huidig: float
    e_ev_thuis_huidig: float
    e_jaar_buurt: float
    e_jaar: float
    d: float
    f: np.ndarray
    E: float
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, dag, prof, woningtypen: pd.DataFrame) -> Resultaat:
    types = woningtypen.assign(e_netto_kwh=woningtypen["woningen"] * woningtypen["e_netto_kwh_per_woning"])
    N = float(types["woningen"].sum())
    e_netto = float(types["e_netto_kwh"].sum())
    e_zon = k7_zon.e_zon_bruto(b, p)
    e_wp = k3_warmtepomp.e_wp_huidig(b, p)
    e_ev = k4_laden_auto.e_ev_thuis_huidig(b, p)
    e_jaar_buurt = e_netto + e_zon - e_wp - e_ev
    e_jaar = e_jaar_buurt / N
    f = prof["nedu_e1a"].to_numpy(float)
    d = dagfractie(f)
    E = e_jaar * d
    v = f / d
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Σ woningtypen = woningen buurt", nl(N), nl(b["woningen"]), abs(N - b["woningen"]) < TOL),
        Check("E_jaar ≥ levering (E_netto)", f"{nl(e_jaar_buurt)} kWh", f"≥ {nl(e_netto)} kWh",
              e_jaar_buurt >= e_netto - TOL),
        Check("E_jaar > 0", f"{nl(e_jaar_buurt)} kWh", "> 0", e_jaar_buurt > 0),
    ]
    return Resultaat(N, types, e_netto, e_zon, e_wp, e_ev, e_jaar_buurt, e_jaar, d, f, E, v, P, checks)
