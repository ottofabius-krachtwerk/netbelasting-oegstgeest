"""Kaart 5: Laden logistiek, alleen de extra voertuigen. Per type N = aantal (invoer), E = laadenergie per dag.

Verloop voorlopig vlak over de dag (aanname); de laadprofielen per type in profielen.csv zijn voor later.
"""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, p_kw, vorm

# voertuigtype -> (aantal per buurt, laadenergie per dag, laadprofiel ongestuurd, laadprofiel slim, aandeel slim)
TYPES = {"E-bestelbus": ("log_bestel_extra", "log_e_dag_bestel", "logistiek_bestel", "logistiek_bestel_slim", "slim_log_bestel"),
         "E-truck": ("log_truck_extra", "log_e_dag_truck", "logistiek_truck", "logistiek_truck_slim", "slim_log_truck")}


@dataclass
class Klasse:
    N: float
    E: float
    v: np.ndarray
    P: np.ndarray
    slim: float = 0.0  # aandeel slim laden, 0 tot 1
    v_std: np.ndarray | None = None   # verloop ongestuurd laden
    v_slim: np.ndarray | None = None  # verloop slim laden


@dataclass
class Resultaat:
    klassen: dict
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    klassen, checks = {}, []
    for naam, (kolom, e_par, profiel, profiel_slim, slim_par) in TYPES.items():
        N = float(b[kolom])
        E = p[e_par]
        s = p[slim_par] / 100
        v_std, v_slim = vorm(prof[profiel]), vorm(prof[profiel_slim])
        v = (1 - s) * v_std + s * v_slim
        klassen[naam] = Klasse(N, E, v, p_kw(N, E, v), s, v_std, v_slim)
        checks += [Check(f"{c.naam} ({naam.lower()})", c.waarde, c.norm, c.ok) for c in checks_standaard(klassen[naam].P, N, E, v, +1)]
    return Resultaat(klassen, np.sum([k.P for k in klassen.values()], axis=0), checks)
