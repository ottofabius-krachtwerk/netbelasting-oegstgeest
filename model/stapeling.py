"""Stapeling: P_b[t] = Σ kaarten P_s,b[t]. Piek in kW, geen omrekening naar kVA of MSR.

95 %-grens: P_b[t] + 1,645 × σ[t], met σ de spreiding van de tabs die er een hebben (nu alleen laden personenauto's).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model.common import TOL, Check, nl


@dataclass
class Resultaat:
    P: dict          # kaartnaam -> P[t]
    dagenergie: dict  # kaartnaam -> verwachte Σ P ÷ 4 volgens de kaart
    P_tot: np.ndarray
    i_piek: int
    tabel: pd.DataFrame
    checks: list[Check]
    P95: np.ndarray    # 95 %-grens van het totaal per kwartier
    i_piek95: int


def bereken(P: dict, dagenergie: dict, sigma=None, z: float = 1.645) -> Resultaat:
    P_tot = np.sum(list(P.values()), axis=0)
    P95 = P_tot + z * (np.zeros_like(P_tot) if sigma is None else np.asarray(sigma))
    i = int(np.argmax(P_tot))
    rijen = []
    for k, p in P.items():
        j = int(np.argmin(p)) if p.sum() < 0 else int(np.argmax(p))  # opwek: grootste opwek, anders grootste afname
        rijen.append({"kaart": k, "op_piek": p[i], "extreem": p[j], "i_extreem": j, "dag_kwh": p.sum() / 4})
    tabel = pd.DataFrame(rijen)
    som, doel = P_tot.sum() / 4, sum(dagenergie.values())
    checks = [
        Check("Bijdragen tellen op tot de piek", f"{nl(tabel['op_piek'].sum())} kW", f"{nl(P_tot[i])} kW",
              abs(tabel["op_piek"].sum() - P_tot[i]) <= TOL * max(1, abs(P_tot[i]))),
        Check("Dagtotaal = som van de dagtotalen van de tabs", f"{nl(som)} kWh", f"{nl(doel)} kWh", abs(som - doel) <= TOL * max(1, abs(doel))),
    ] + [
        Check(f"Dagtotaal {k} klopt", f"{nl(P[k].sum() / 4)} kWh", f"{nl(e)} kWh", abs(P[k].sum() / 4 - e) <= TOL * max(1, abs(e)))
        for k, e in dagenergie.items()
    ]
    checks.append(Check("95 %-grens ligt overal op of boven het totaal", nl(float((P95 - P_tot).min()), 2), "≥ 0",
                        bool(np.all(P95 >= P_tot - TOL))))
    return Resultaat(P, dagenergie, P_tot, i, tabel, checks, P95, int(np.argmax(P95)))
