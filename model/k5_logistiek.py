"""Kaart 5: Laden logistiek, alleen de extra voertuigen. Per type N = aantal (invoer), E = laadenergie per dag.

Verloop voorlopig vlak over de dag (aanname); de laadprofielen per type in profielen.csv zijn voor later.
"""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, p_kw

# voertuigtype -> (aantal per buurt, laadenergie per dag, laadprofiel)
TYPES = {"E-bestelbus": ("log_bestel_extra", "log_e_dag_bestel", "logistiek_bestel"),
         "E-truck": ("log_truck_extra", "log_e_dag_truck", "logistiek_truck")}


@dataclass
class Klasse:
    N: float
    E: float
    v: np.ndarray
    P: np.ndarray


@dataclass
class Resultaat:
    klassen: dict
    P: np.ndarray
    checks: list[Check]


def bereken(b, p, prof) -> Resultaat:
    klassen, checks = {}, []
    for naam, (kolom, e_par, profiel) in TYPES.items():
        N = float(b[kolom])
        E = p[e_par]
        v = np.full(len(prof), 1 / len(prof))  # aanname: vlak profiel
        klassen[naam] = Klasse(N, E, v, p_kw(N, E, v))
        checks += [Check(f"{c.naam} ({naam.lower()})", c.waarde, c.norm, c.ok) for c in checks_standaard(klassen[naam].P, N, E, v, +1)]
    return Resultaat(klassen, np.sum([k.P for k in klassen.values()], axis=0), checks)
