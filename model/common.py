"""Gedeelde rekenstappen: P = 4·N·E·v, vormen, dagfractie en checks."""
from dataclasses import dataclass

import numpy as np

KWARTIEREN = 96
TOL = 1e-6


@dataclass
class Check:
    naam: str
    waarde: str
    norm: str
    ok: bool


def p_kw(N: float, E: float, v) -> np.ndarray:
    """P[t] in kW. Factor 4: kWh per kwartier naar kW."""
    return 4.0 * N * E * np.asarray(v, float)


def vorm(x, teken: int = 1) -> np.ndarray:
    """Normaliseer een reeks zodat de som gelijk is aan teken (+1 of −1)."""
    x = np.asarray(x, float)
    s = x.sum()
    return np.zeros_like(x) if s == 0 else teken * x / s


def dagfractie(f) -> float:
    """d = som van f[t] over de 96 kwartieren van de referentiedag."""
    return float(np.sum(f))


def nl(x: float, dec: int = 0) -> str:
    """Getal in Nederlandse notatie."""
    s = f"{x:,.{dec}f}"
    if float(s.replace(",", "")) == 0:
        s = s.lstrip("-")
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def checks_standaard(P, N: float, E: float, v, teken: int) -> list[Check]:
    """Σ P ÷ 4 = teken × N × E, Σ v = teken en v heeft overal het juiste teken."""
    som_p = float(np.sum(P)) / 4
    doel = teken * N * E
    som_v = float(np.sum(v))
    v = np.asarray(v)
    juist_teken = bool(np.all(v >= -TOL)) if teken > 0 else bool(np.all(v <= TOL))
    return [
        Check("Σ P[t] ÷ 4 = " + ("N × E" if teken > 0 else "−N × E"),
              f"{nl(som_p)} kWh", f"{nl(doel)} kWh", abs(som_p - doel) <= TOL * max(1, abs(doel))),
        Check("Σ v", nl(som_v, 6), "+1" if teken > 0 else "−1", abs(som_v - teken) <= TOL),
        Check("Teken v", "alle ≥ 0" if np.all(v >= -TOL) else ("alle ≤ 0" if np.all(v <= TOL) else "gemengd"),
              "alle ≥ 0" if teken > 0 else "alle ≤ 0", juist_teken),
    ]


def zonvorm(I) -> np.ndarray:
    """Opwekvorm uit de instraling: v[t] = −I[t] ÷ Σ I (kaart 7 en de opwek-sector van kaart 6)."""
    return vorm(I, -1)


def instraling_dag(I) -> float:
    """I_ref in kWh/m² op de referentiedag, uit W/m² per kwartier."""
    return float(np.sum(I)) * 0.25 / 1000
