"""Kaart 3: Warmtepomp. E = Q_ref ÷ COP, met Q_ref uit gas en graaddagen; vorm uit een gemiddeld profiel."""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, nl, p_kw, vorm

TECH = {"geen": "ae", "all-electric": "ae", "ZLT": "zlt"}
POMPINVOER = ["per woning", "totaal buurt"]
VORMEN = ["vlak", "G1A"]  # bandbreedte voor all-electric: volgt stookgedrag gaswoningen, of maximale buffering


def labelfactor(labels_buurt, energielabels) -> float:
    """Factor op de warmtevraag uit de labelverdeling van de buurt; het gemeentegemiddelde is 1.

    Demo: factor_buurt = Σ aandeel_buurt × factor ÷ Σ aandeel_gemeente × factor.
    """
    el = energielabels.set_index("label")
    gem = (el["adressen_gemeente"] * el["factor"]).sum() / el["adressen_gemeente"].sum()
    lb = labels_buurt.set_index("label")["adressen"].reindex(el.index).fillna(0)
    if lb.sum() == 0:
        return 1.0
    return float((lb * el["factor"]).sum() / lb.sum() / gem)


def q_jaar_gas(b, p) -> float:
    """Warmtevraag per woning uit gas, vóór de labelcorrectie, in kWh."""
    return (b["gas_m3_per_woning"] - p["gas_tapwater_koken_m3"]) * p["calorische_waarde"] * p["ketelrendement"]


def q_jaar(b, p) -> float:
    """Jaarlijkse warmtevraag per woning, met labelcorrectie, in kWh."""
    return q_jaar_gas(b, p) * b["labelfactor"]


def wp_huidig(b, p) -> float:
    """Huidige warmtepompen in de buurt: gemeentetotaal naar aandeel woningen (eenvoudige verdeelregel)."""
    return p["wp_gemeente"] * b["woningen"] / p["woningen_gemeente"]


def e_wp_huidig(b, p) -> float:
    """Jaarenergie van de bestaande warmtepompen in de buurt (correctie op kaart 1)."""
    return wp_huidig(b, p) * q_jaar(b, p) / p["scop_huidig"]


def cop_dag(oplossing: str, p) -> float:
    """Eén COP voor de referentiedag; MT heeft geen warmtepomp per woning (dan nan).

    "geen": alleen de bestaande warmtepompen, gerekend als all-electric.
    ZLT: COP van de booster lineair met de temperatuur van het warmtenet (a + b × T_net).
    Verbetering voor later: Carnot × rendement met de aanvoertemperatuur in de woning.
    """
    if oplossing in ("geen", "all-electric"):
        return p["cop_ae"]
    if oplossing == "ZLT":
        return p["cop_zlt_a"] + p["cop_zlt_b"] * p["t_net_zlt"]
    return float("nan")


def e_pomp(oplossing: str, p, b, N: float, invoer: str = "per woning") -> float:
    """Pompenergie van het warmtenet per aangesloten woning per dag, in kWh; vast, los van de warmtevraag.

    Invoer per woning (W) of als totaal pompvermogen voor de buurt (kW), dat over de woningen wordt verdeeld.
    """
    if oplossing not in ("ZLT", "MT"):
        return 0.0
    if invoer == "totaal buurt":
        return b["pomp_kw_buurt"] * 24 / N if N else 0.0
    return p["pomp_w_woning"] / 1000 * 24


@dataclass
class Resultaat:
    oplossing: str
    N: float
    gas: float
    gas_tapwater_koken: float
    q_jaar_gas: float
    labelfactor: float
    q_jaar: float
    gd_ref: float
    q_ref: float
    T: np.ndarray
    vorm_bron: str
    band: dict  # vorm -> (v, P); alleen bij all-electric en geen
    cop: float
    e_warmtepomp: float  # kWh stroom per woning per dag voor warmtepomp of booster
    e_pomp: float        # kWh stroom per woning per dag voor de pompen van het warmtenet
    E: float
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]
    pomp_invoer: str = "per woning"


def bereken(b, p, dag, prof, oplossing: str | None = None, wp_vorm: str = "vlak",
            pomp_invoer: str = "per woning") -> Resultaat:
    oplossing = oplossing or b["warmteoplossing"]
    # "geen": geen extra woningen; de bestaande warmtepompen (die uit de basis zijn gehaald) blijven
    N = float(wp_huidig(b, p) if oplossing == "geen" else b["woningen"])
    T = dag["T"].to_numpy(float)
    Q = q_jaar(b, p)
    gd_ref = max(0.0, p["t_stookgrens"] - T.mean())
    q_ref = Q * gd_ref / p["gd_jaar"] * (1 - b["isolatie_reductie"] / 100)
    c = cop_dag(oplossing, p)
    e_wp = 0.0 if oplossing == "MT" else q_ref / c
    e_p = e_pomp(oplossing, p, b, N, pomp_invoer)
    E = e_wp + e_p
    band = {}
    if oplossing in ("geen", "all-electric"):
        vs = {"G1A": vorm(prof["nedu_g1a_tap"]), "vlak": np.full(len(T), 1 / len(T))}
        band = {naam: (vv, p_kw(N, E, vv)) for naam, vv in vs.items()}
        v, vorm_bron = vs[wp_vorm], wp_vorm
    else:  # warmtenetten: voorlopig constant over de dag
        v, vorm_bron = np.full(len(T), 1 / len(T)), "constant"
    P = p_kw(N, E, v)
    checks = checks_standaard(P, N, E, v, +1) + [
        Check("Warmtevraag per jaar positief (Q_jaar > 0)", f"{nl(Q)} kWh", "> 0", Q > 0),
    ]
    if oplossing in TECH:
        t = TECH[oplossing]
        lo, hi = p[f"cop_min_{t}"], p[f"cop_max_{t}"]
        checks.append(Check(f"COP {oplossing} binnen controlebereik", nl(c, 2), f"{nl(lo, 1)} tot {nl(hi, 1)}", lo <= c <= hi))
    return Resultaat(oplossing, N, b["gas_m3_per_woning"], p["gas_tapwater_koken_m3"], q_jaar_gas(b, p),
                     b["labelfactor"], Q, gd_ref,
                     q_ref, T, vorm_bron, band, c, e_wp, e_p, E, v, P, checks, pomp_invoer)
