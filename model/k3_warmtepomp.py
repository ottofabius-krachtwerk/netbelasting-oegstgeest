"""Kaart 3: Warmtepomp. E = Q_ref ÷ COP, met Q_ref uit gas en graaddagen; vorm uit een gemiddeld profiel."""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, nl, p_kw, vorm

TECH = {"geen": "ae", "all-electric": "ae", "ZLT": "zlt"}
VORMEN = ["vlak", "G1A"]  # bandbreedte voor all-electric: volgt stookgedrag gaswoningen, of maximale buffering


def q_jaar(b, p) -> float:
    """Jaarlijkse warmtevraag per woning uit gas, in kWh."""
    gas_ruimte = b["gas_m3_per_woning"] - p["gas_tapwater_m3"] - p["gas_koken_m3"]
    return gas_ruimte * p["calorische_waarde"] * p["ketelrendement"]


def e_wp_huidig(b, p) -> float:
    """Jaarenergie van de bestaande warmtepompen in de buurt (correctie op kaart 1)."""
    return b["wp_huidig"] * q_jaar(b, p) / p["scop_huidig"]


def cop_dag(oplossing: str, p) -> float:
    """Eén COP voor de referentiedag. MT: geen warmtepomp per woning, alleen pompenergie (1 ÷ pompfactor).

    "geen": alleen de bestaande warmtepompen, gerekend als all-electric.
    """
    if oplossing in ("geen", "all-electric"):
        return p["cop_ae"]
    if oplossing == "ZLT":
        return p["cop_zlt"]
    return 1 / p["mt_pompfactor"]


@dataclass
class Resultaat:
    oplossing: str
    N: float
    gas: float
    gas_tapwater: float
    gas_koken: float
    q_jaar: float
    gd_ref: float
    q_ref: float
    T: np.ndarray
    vorm_bron: str
    band: dict  # vorm -> (v, P); alleen bij all-electric en geen
    cop: float
    E: float
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, dag, prof, oplossing: str | None = None, wp_vorm: str = "vlak") -> Resultaat:
    oplossing = oplossing or b["warmteoplossing"]
    # "geen": geen extra woningen; de bestaande warmtepompen (die uit de basis zijn gehaald) blijven
    N = float(b["wp_huidig"] if oplossing == "geen" else b["woningen"])
    T = dag["T"].to_numpy(float)
    Q = q_jaar(b, p)
    gd_ref = max(0.0, p["t_stookgrens"] - T.mean())
    q_ref = Q * gd_ref / p["gd_jaar"] * (1 - b["isolatie_reductie"] / 100)
    c = cop_dag(oplossing, p)
    E = q_ref / c
    band = {}
    if oplossing in ("geen", "all-electric"):
        vs = {"G1A": vorm(prof["nedu_g1a_tap"]), "vlak": np.full(len(T), 1 / len(T))}
        band = {naam: (vv, p_kw(N, E, vv)) for naam, vv in vs.items()}
        v, vorm_bron = vs[wp_vorm], wp_vorm
    else:  # ZLT en MT: ongewijzigd, graaduren per kwartier
        v, vorm_bron = vorm(np.maximum(p["t_stookgrens"] - T, 0)), "graaduren"
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Q_jaar > 0", f"{nl(Q)} kWh", "> 0", Q > 0),
    ]
    if oplossing in TECH:
        t = TECH[oplossing]
        lo, hi = p[f"cop_min_{t}"], p[f"cop_max_{t}"]
        checks.append(Check(f"COP {oplossing} in bereik", nl(c, 2), f"{nl(lo, 1)} tot {nl(hi, 1)}", lo <= c <= hi))
    return Resultaat(oplossing, N, b["gas_m3_per_woning"], p["gas_tapwater_m3"], p["gas_koken_m3"], Q, gd_ref,
                     q_ref, T, vorm_bron, band, c, E, v, P, checks)
