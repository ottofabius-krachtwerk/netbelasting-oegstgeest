"""Kaart 3: Warmtepomp, alleen de toename. E = Q_ref ÷ COP, met Q_ref uit gas en graaddagen.

De huidige warmtepompen zitten in het netto verbruik van kaart 1 (woningen basis); woningen die er nu al een
hebben gaan niet nog eens over.
"""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, nl, p_kw, vorm

TECH = {"geen": "ae", "all-electric": "ae", "ZLT": "zlt"}
POMPINVOER = ["per woning", "totaal buurt"]
# MT (70 °C): warmteproductie buiten beschouwing, of een bron opgewaardeerd met collectieve warmtepompen en WKO
MT_OPWEK = ["buiten beschouwing", "aquathermie TEO", "aquathermie TEA", "ondiepe geothermie"]
MT_COP = {"aquathermie TEO": "cop_mt_teo", "aquathermie TEA": "cop_mt_tea", "ondiepe geothermie": "cop_mt_geo"}
VORMEN = ["vlak", "gemeten"]  # bandbreedte voor all-electric: maximale buffering, of gemeten aggregaatprofiel


def q_jaar_gas(b, p) -> float:
    """Warmtevraag per woning uit gas, in kWh."""
    return (b["gas_m3_per_woning"] - p["gas_tapwater_koken_m3"]) * p["calorische_waarde"] * p["ketelrendement"]


def q_jaar(b, p) -> float:
    """Jaarlijkse warmtevraag per woning, in kWh (energielabels gebruiken we niet: data incompleet)."""
    return q_jaar_gas(b, p)


def n_woningen(oplossing: str, b) -> float:
    """Extra woningen op de warmteoplossing: alle woningen min die nu al een warmtepomp hebben; bij "geen" 0."""
    if oplossing == "geen":
        return 0.0
    return b["woningen"] * (1 - b["wp_aandeel_huidig"] / 100)


def cop_dag(oplossing: str, p, mt_opwek: str = MT_OPWEK[0]) -> float:
    """Eén COP voor de referentiedag; MT zonder meegerekende warmteproductie heeft geen opwek (dan nan).

    "geen": geen extra woningen; de COP van all-electric wordt alleen getoond.
    ZLT: COP van de booster lineair met de temperatuur van het warmtenet (a + b × T_net).
    Verbetering voor later: Carnot × rendement met de aanvoertemperatuur in de woning.
    """
    if oplossing in ("geen", "all-electric"):
        return p["cop_ae"]
    if oplossing == "ZLT":
        return p["cop_zlt_a"] + p["cop_zlt_b"] * p["t_net_zlt"]
    if oplossing == "MT" and mt_opwek in MT_COP:  # systeem-COP naar 70 °C, inclusief WKO en bronpompen
        return p[MT_COP[mt_opwek]]
    return float("nan")  # MT met warmteproductie buiten beschouwing


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
    woningen: float = 0.0           # alle woningen in de buurt
    wp_aandeel_huidig: float = 0.0  # % woningen met nu al een warmtepomp
    mt_opwek: str = MT_OPWEK[0]
    gas_pct: float = 0.0       # % van de piekvraag uit de gasgestuurde piek- en backupvoorziening
    piek_warmte_kw: float = 0.0  # piekvraag warmte van het net op deze dag


def bereken(b, p, dag, prof, oplossing: str | None = None, wp_vorm: str = "vlak",
            pomp_invoer: str = "per woning", mt_opwek: str = MT_OPWEK[0]) -> Resultaat:
    oplossing = oplossing or b["warmteoplossing"]
    N = float(n_woningen(oplossing, b))
    T = np.full(len(dag), p["t_ref"])  # aanname: constante buitentemperatuur op de referentiedag
    Q = q_jaar(b, p)
    gd_ref = max(0.0, p["t_stookgrens"] - T.mean())
    q_ref = Q * gd_ref / p["gd_jaar"] * (1 - b["isolatie_reductie"] / 100)
    c = cop_dag(oplossing, p, mt_opwek)
    # MT: de gasgestuurde piek- en backupvoorziening levert een deel van de piekvraag; de warmtevraag is op deze dag
    # constant genomen, dus dat deel geldt ook voor de energie. De collectieve warmtepomp levert de rest.
    gas = p["mt_gas_pct"] / 100 if oplossing == "MT" and mt_opwek in MT_COP else 0.0
    e_wp = 0.0 if np.isnan(c) else q_ref * (1 - gas) / c  # warmtepomp, booster of collectieve warmtepomp
    e_p = e_pomp(oplossing, p, b, N, pomp_invoer)
    E = e_wp + e_p
    band = {}
    if oplossing in ("geen", "all-electric"):
        vs = {"vlak": np.full(len(T), 1 / len(T)), "gemeten": vorm(prof["wp_aggregaat"])}
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
                     Q, gd_ref,
                     q_ref, T, vorm_bron, band, c, e_wp, e_p, E, v, P, checks, pomp_invoer,
                     float(b["woningen"]), float(b["wp_aandeel_huidig"]), mt_opwek, gas * 100, N * q_ref / 24)
