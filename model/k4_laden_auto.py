"""Kaart 4: Laden personenauto's, alleen de extra EV's. Vier laadprofielen: thuis of publiek, standaard of slim.

Energie = N × E (alleen laden in de buurt), verdeeld naar publiek (q) en thuis (1 − q), en per locatie naar slim
(a_thuis, a_publiek) en standaard. Het verloop mengt de vier ElaadNL-vormen met die gewichten.
95 %-grens: per onderdeel n laadpunten = energie ÷ ElaadNL-energie per laadpunt, spreiding √n × σ per laadpunt;
de onderdelen zijn onafhankelijk, dus σ_totaal = √Σ σ². Grens = verwacht + 1,645 × σ_totaal (eenzijdig, per kwartier).
Het laden van de huidige EV's zit in het netto verbruik van kaart 1 (woningen basis).
"""
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, checks_standaard, nl, p_kw, vorm

Z95 = 1.645  # eenzijdig 95 %
PROFIELEN = ["thuis standaard", "thuis slim", "publiek standaard", "publiek slim"]
KOLOM = {"thuis standaard": "ev_ongestuurd_thuis", "thuis slim": "ev_slim_thuis",
         "publiek standaard": "ev_ongestuurd_publiek", "publiek slim": "ev_slim_publiek"}


@dataclass
class Resultaat:
    N: float
    E: float
    q: float          # aandeel publiek (fractie van de laadenergie)
    a_thuis: float    # aandeel slim bij thuisladen
    a_publiek: float  # aandeel slim bij publiek laden
    vormen: dict      # profiel -> v, elk Σ = 1
    gewichten: dict   # profiel -> deel van de laadenergie, samen 1
    e_punt: dict      # profiel -> kWh per laadpunt per dag (ElaadNL)
    laadpunten: dict  # profiel -> aantal laadpunten (energie ÷ e_punt)
    v: np.ndarray
    P: np.ndarray
    sigma: np.ndarray  # spreiding van het totaal per kwartier, kW
    P95: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    N = float(b["ev_extra"])  # toename per buurt, aantal extra EV's (invoer)
    E = p["ev_e_dag"]
    q, at, ap = p["publiek_aandeel"] / 100, p["slim_thuis"] / 100, p["slim_publiek"] / 100
    gewichten = {"thuis standaard": (1 - q) * (1 - at), "thuis slim": (1 - q) * at,
                 "publiek standaard": q * (1 - ap), "publiek slim": q * ap}
    mu = {n: prof[KOLOM[n]].to_numpy(float) for n in PROFIELEN}
    sd = {n: prof[f"{KOLOM[n]}_sd"].to_numpy(float) for n in PROFIELEN}
    vormen = {n: vorm(mu[n]) for n in PROFIELEN}
    e_punt = {n: float(mu[n].sum() / 4) for n in PROFIELEN}
    laadpunten = {n: N * E * gewichten[n] / e_punt[n] if e_punt[n] else 0.0 for n in PROFIELEN}
    v = np.sum([gewichten[n] * vormen[n] for n in PROFIELEN], axis=0)
    P = p_kw(N, E, v)
    sigma = np.sqrt(np.sum([laadpunten[n] * sd[n] ** 2 for n in PROFIELEN], axis=0))
    P95 = P + Z95 * sigma
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Gewichten van de vier profielen tellen op tot 100 %", nl(sum(gewichten.values()), 6), "1",
              abs(sum(gewichten.values()) - 1) <= TOL),
        Check("95 %-grens ligt overal op of boven het verwachte profiel", nl(float((P95 - P).min()), 2), "≥ 0",
              bool(np.all(P95 >= P - TOL))),
    ] + [Check(f"Verloop {n} telt op tot 100 % (Σ v)", nl(vv.sum(), 6), "1", abs(vv.sum() - 1) <= TOL)
         for n, vv in vormen.items()]
    return Resultaat(N, E, q, at, ap, vormen, gewichten, e_punt, laadpunten, v, P, sigma, P95, checks)
