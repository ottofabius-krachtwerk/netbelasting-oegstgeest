"""Kaart 5: Laden logistiek (placeholder). Per voertuigtype N = voertuigen × elektrificatie × (1 + groei)."""
from dataclasses import dataclass

import numpy as np

from model.common import Check, checks_standaard, p_kw, vorm

TYPES = {"Bestelauto": ("bestelautos", "log_e_dag_bestel", "logistiek_bestel"),
         "Truck": ("vrachtautos", "log_e_dag_truck", "logistiek_truck")}


@dataclass
class Klasse:
    voertuigen: float
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
    factor = p["log_elektrificatie"] / 100 * (1 + p["log_groei"] / 100)
    klassen, checks = {}, []
    for naam, (kolom, e_par, profiel) in TYPES.items():
        N = b[kolom] * factor
        E = p[e_par]
        v = vorm(prof[profiel])
        klassen[naam] = Klasse(float(b[kolom]), N, E, v, p_kw(N, E, v))
        checks += [Check(f"{c.naam} ({naam.lower()})", c.waarde, c.norm, c.ok) for c in checks_standaard(klassen[naam].P, N, E, v, +1)]
    return Resultaat(klassen, np.sum([k.P for k in klassen.values()], axis=0), checks)
