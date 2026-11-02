"""Kaart 8: Thuisbatterij. Type D: P = N × v, v in kW per kWh capaciteit, Σ v ≈ 0 (iets > 0 door verliezen)."""
import math
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, nl

MODI = ["zelfconsumptie", "zelfconsumptie + day-ahead"]
DT = 0.25  # uur per kwartier


@dataclass
class Modus:
    v: np.ndarray    # kW per kWh capaciteit, positief = laden
    soc: np.ndarray  # laadtoestand aan het eind van elk kwartier, 0 tot 1
    soc_start: float


@dataclass
class Resultaat:
    N: float
    batterijen: float
    last: np.ndarray  # kW per batterijwoning
    pv: np.ndarray    # kW per batterijwoning (positief = opwek)
    prijs: np.ndarray
    goedkoop: np.ndarray
    duur: np.ndarray
    modi: dict
    modus: str
    v: np.ndarray
    P: np.ndarray
    checks: list[Check]


def _simuleer(last, pv, goedkoop, duur, modus: str, kwh: float, c: float, eta: float) -> Modus:
    """Eenvoudige regel per kwartier; de dag herhaald doorrekenen tot eind-SoC gelijk is aan begin-SoC.

    Zelfconsumptie: laden bij zonoverschot, ontladen bij tekort.
    Plus day-ahead: laden bij zonoverschot en in de goedkoopste kwartieren, ontladen in de duurste kwartieren.
    """
    p_max = c * kwh
    eta_l = eta_d = math.sqrt(eta)
    soc_start = 0.0
    for _ in range(20):
        e = soc_start * kwh
        p_bat, soc = np.zeros(len(last)), np.zeros(len(last))
        for t in range(len(last)):
            overschot = pv[t] - last[t]
            ruimte = (kwh - e) / eta_l / DT  # max laadvermogen aan de netzijde
            beschikbaar = e * eta_d / DT     # max ontlaadvermogen aan de netzijde
            if overschot > 0:
                p = min(overschot, p_max, ruimte)
            elif modus == MODI[0]:
                p = -min(-overschot, p_max, beschikbaar)
            elif goedkoop[t]:
                p = min(p_max, ruimte)
            elif duur[t]:
                p = -min(p_max, beschikbaar)
            else:
                p = 0.0
            e += p * DT * eta_l if p > 0 else p * DT / eta_d
            p_bat[t], soc[t] = p, e / kwh
        if abs(soc[-1] - soc_start) < 1e-9:
            break
        soc_start = soc[-1]
    return Modus(p_bat / kwh, soc, soc_start)


def bereken(b, p, dag, last_per_woning, zon_per_kwp, modus: str = MODI[0]) -> Resultaat:
    kwh = p["bat_kwh"]
    batterijen = b["woningen"] * p["bat_adoptie"] / 100
    N = batterijen * kwh
    last = np.asarray(last_per_woning, float)
    pv = -np.asarray(zon_per_kwp, float) * p["bat_kwp_woning"]
    prijs = dag["prijs"].to_numpy(float)
    n = math.ceil(1 / (p["bat_c"] * DT))  # kwartieren om vol of leeg te gaan
    volgorde = np.argsort(prijs)
    goedkoop, duur = np.zeros(len(prijs), bool), np.zeros(len(prijs), bool)
    goedkoop[volgorde[:n]], duur[volgorde[-n:]] = True, True
    modi = {m: _simuleer(last, pv, goedkoop, duur, m, kwh, p["bat_c"], p["bat_eta"]) for m in MODI}
    v = modi[modus].v
    P = N * v
    m = modi[modus]
    laden = float(np.clip(v, 0, None).sum() * DT)
    verlies = float(v.sum() * DT)
    checks = [
        Check("Verlies over de dag ≥ 0 (Σ v ÷ 4)", nl(verlies, 4), "≥ 0", verlies >= -TOL),
        Check("Verlies ≤ rendementsverlies op wat geladen is", nl(verlies, 4), f"≤ {nl((1 - p['bat_eta']) * laden, 4)}",
              verlies <= (1 - p["bat_eta"]) * laden + TOL),
        Check("Laad- en ontlaadvermogen binnen maximum (|v|)", nl(float(np.abs(v).max()), 3), f"≤ {nl(p['bat_c'], 2)}",
              float(np.abs(v).max()) <= p["bat_c"] + TOL),
        Check("Laadtoestand tussen 0 en 100 %", f"{nl(m.soc.min() * 100)} tot {nl(m.soc.max() * 100)} %", "0 tot 100",
              m.soc.min() >= -TOL and m.soc.max() <= 1 + TOL),
        Check("Batterij eindigt zo vol als hij begon", f"{nl(m.soc[-1] * 100, 1)} %", f"{nl(m.soc_start * 100, 1)} %",
              abs(m.soc[-1] - m.soc_start) < 1e-6),
    ]
    return Resultaat(N, batterijen, last, pv, prijs, goedkoop, duur, modi, modus, v, P, checks)
