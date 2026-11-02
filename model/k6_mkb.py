"""Kaart 6: MKB en grootverbruik. P = Σ_s 4 × E_s × v_s, met E_s = E_jaar,s × d_s en N = 1 per sector."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from model.common import TOL, Check, nl, p_kw, vorm


PROFIELBRONNEN = ["Liander", "NEDU E3"]  # per sector een eigen profiel, of één E3-profiel voor alle sectoren


@dataclass
class Resultaat:
    profielbron: str
    sectoren: pd.DataFrame  # sector, teken, e_jaar, d, E
    v: dict
    P: dict
    P_tot: np.ndarray
    checks: list[Check]


def bereken(p, dag, prof, sectoren: pd.DataFrame, profielbron: str = "Liander") -> Resultaat:
    groei = 1 + p["groei_niet_huish"] / 100
    rijen, V, P = [], {}, {}
    for _, s in sectoren.iterrows():
        teken = int(s["teken"])
        if s["profiel"] == "instraling":  # opwek: f[t] = I[t] × 0,25 ÷ 1000 ÷ I_jaar, vorm gelijk aan kaart 7
            f = dag["I"].to_numpy(float) * 0.25 / 1000 / p["i_jaar"]
        elif profielbron == "NEDU E3":
            f = prof["nedu_e3"].to_numpy(float)
        else:
            f = prof[s["profiel"]].to_numpy(float)
        d = float(f.sum())
        E = s["e_jaar_kwh"] * groei * d
        V[s["sector"]] = vorm(f, teken)
        P[s["sector"]] = p_kw(1, E, V[s["sector"]])
        rijen.append({"sector": s["sector"], "teken": teken, "e_jaar": s["e_jaar_kwh"] * groei, "d": d, "E": E})
    df = pd.DataFrame(rijen)
    P_tot = np.sum(list(P.values()), axis=0) if P else np.zeros(96)
    som_p, doel = P_tot.sum() / 4, float((df["teken"] * df["E"]).sum())
    checks = [
        Check("Σ P[t] ÷ 4 = Σ teken × E_s", f"{nl(som_p)} kWh", f"{nl(doel)} kWh", abs(som_p - doel) <= TOL * max(1, abs(doel))),
        Check("Elke sector één keer", f"{df['sector'].nunique()} van {len(df)}", "uniek", df["sector"].is_unique),
    ] + [
        Check(f"Σ v en teken: {r.sector}", nl(V[r.sector].sum(), 4), f"{r.teken:+d}, alle {'≥' if r.teken > 0 else '≤'} 0",
              abs(V[r.sector].sum() - r.teken) <= TOL and bool(np.all(V[r.sector] * r.teken >= -TOL)))
        for r in df.itertuples()
    ]
    return Resultaat(profielbron, df, V, P, P_tot, checks)
