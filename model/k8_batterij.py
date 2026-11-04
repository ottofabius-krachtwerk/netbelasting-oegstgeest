"""Kaart 8: Thuisbatterij. Type D: P = N × v, v in kW per kWh capaciteit, Σ v ≈ 0 (iets > 0 door verliezen)."""
import math
from dataclasses import dataclass

import numpy as np

from model.common import TOL, Check, nl

MODI = ["zelfconsumptie", "zelfconsumptie + day-ahead"]
GROOTTES = [5.0, 10.0, 15.0]  # kWh per thuisbatterij; gangbaar 5 tot 15 kWh (marktaanbod, zie tab)
DT = 0.25  # uur per kwartier


@dataclass
class Modus:
    v: np.ndarray    # kW per kWh capaciteit, positief = laden
    soc: np.ndarray  # laadtoestand aan het eind van elk kwartier, 0 tot 1
    soc_start: float
    soc_net: np.ndarray  # deel van de laadtoestand dat uit het net is ingekocht


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
    woningen: float = 0.0


def _simuleer(last, pv, goedkoop, duur, modus: str, kwh: float, c: float, eta: float) -> Modus:
    """Eenvoudige regel per kwartier; de dag herhaald doorrekenen tot eind-SoC gelijk is aan begin-SoC.

    De batterij houdt zonnestroom en ingekochte stroom apart bij (samen maximaal de capaciteit).
    Zelfconsumptie: zonoverschot laden, eigen tekort dekken uit zonnestroom.
    Plus day-ahead: daarnaast in de goedkoopste kwartieren laden uit het net (ingekochte stroom, dan geen ontladen) en
    in de duurste kwartieren op vol vermogen ontladen: eigen tekort dekken en de rest terugleveren, eerst de
    ingekochte stroom. Buiten de duurste kwartieren blijft ingekochte stroom staan; zonnestroom dekt het eigen tekort.
    """
    p_max = c * kwh
    eta_l = eta_d = math.sqrt(eta)
    plus = modus == MODI[1]
    start = (0.0, 0.0)  # (zonnestroom, ingekochte stroom) in kWh in de batterij
    for _ in range(50):
        ez, en = start
        p_bat, soc, soc_net = np.zeros(len(last)), np.zeros(len(last)), np.zeros(len(last))
        for t in range(len(last)):
            overschot = pv[t] - last[t]
            ruimte = lambda: (kwh - ez - en) / eta_l / DT  # max laadvermogen aan de netzijde
            p = 0.0
            if overschot > 0:  # zon laadt
                pz = min(overschot, p_max, ruimte())
                ez += pz * DT * eta_l
                p += pz
            if plus and goedkoop[t]:  # bijladen uit het net
                pn = min(p_max - p, ruimte())
                en += pn * DT * eta_l
                p += pn
            elif plus and duur[t]:  # vol vermogen ontladen, eerst ingekochte stroom
                uit_n = min(p_max, en * eta_d / DT)
                uit_z = min(p_max - uit_n, ez * eta_d / DT)
                en -= uit_n * DT / eta_d
                ez -= uit_z * DT / eta_d
                p -= uit_n + uit_z
            elif overschot < 0:  # eigen tekort dekken uit zonnestroom
                uit = min(-overschot, p_max, ez * eta_d / DT)
                ez -= uit * DT / eta_d
                p -= uit
            p_bat[t], soc[t], soc_net[t] = p, (ez + en) / kwh, en / kwh
        if abs(ez - start[0]) + abs(en - start[1]) < 1e-9:
            break
        start = (ez, en)
    return Modus(p_bat / kwh, soc, (start[0] + start[1]) / kwh, soc_net)


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
    return Resultaat(N, batterijen, last, pv, prijs, goedkoop, duur, modi, modus, v, P, checks, float(b["woningen"]))
