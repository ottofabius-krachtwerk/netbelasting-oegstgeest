"""Kaart 6: MKB en grootverbruik. Per bedrijfstak: gemeenteverbruik ÷ buurten ÷ werkdagen, vlak over de dag.

Elke werkdag hetzelfde verbruik; groei (MWh per jaar, gemeente) gaat op dezelfde manier. Zon van bedrijven (overige
daken) volgt de instraling van deze dag, zoals kaart 1 en 7.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model import k7_zon
from model.common import TOL, Check, nl, p_kw


@dataclass
class Resultaat:
    sectoren: pd.DataFrame  # sector, teken, e_gemeente, e_jaar (buurt), d, E
    v: dict
    P: dict
    P_tot: np.ndarray
    checks: list[Check]


def bereken(b, p, dag, bedrijfstakken: pd.DataFrame) -> Resultaat:
    n = len(dag)
    aandeel = 1 / p["buurten_gemeente"]  # voorlopig: elke buurt evenveel
    d_werkdag = 1 / p["werkdagen_jaar"]
    vlak = np.full(n, 1 / n)
    rijen = [(r["bedrijfstak"], 1, float(r["e_jaar_kwh_gemeente"]), d_werkdag, vlak) for _, r in bedrijfstakken.iterrows()]
    rijen.append(("Groei", 1, p["groei_niet_huish"] * 1000, d_werkdag, vlak))
    _, _, f_zon, v_zon = k7_zon.opwek_dag(p, dag)
    rijen.append(("Opwek (zon bedrijven)", -1, float(b["zon_bedrijven_kwh_jaar"]) / aandeel, f_zon, v_zon))
    tabel, V, P = [], {}, {}
    for sector, teken, e_gem, d, v in rijen:
        e_jaar = e_gem * aandeel
        E = e_jaar * d
        V[sector], P[sector] = v, p_kw(1, E, v)
        tabel.append({"sector": sector, "teken": teken, "e_gemeente": e_gem, "e_jaar": e_jaar, "d": d, "E": E})
    df = pd.DataFrame(tabel)
    P_tot = np.sum(list(P.values()), axis=0)
    som_p, doel = P_tot.sum() / 4, float((df["teken"] * df["E"]).sum())
    checks = [
        Check("Dagtotaal = som van de bedrijfstakken (Σ P ÷ 4 = Σ E)", f"{nl(som_p)} kWh", f"{nl(doel)} kWh",
              abs(som_p - doel) <= TOL * max(1, abs(doel))),
        Check("Elke bedrijfstak komt één keer voor", f"{df['sector'].nunique()} van {len(df)}", "uniek", df["sector"].is_unique),
    ] + [
        Check(f"Verloop {r.sector} telt op tot {'100' if r.teken > 0 else '−100'} % (Σ v)", nl(V[r.sector].sum(), 4),
              f"{r.teken:+d}, alle {'≥' if r.teken > 0 else '≤'} 0",
              abs(V[r.sector].sum() - r.teken) <= TOL and bool(np.all(V[r.sector] * r.teken >= -TOL)))
        for r in df.itertuples()
    ]
    return Resultaat(df, V, P, P_tot, checks)
