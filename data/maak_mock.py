"""Genereert de mockdataset in data/mock/ (vaste seed).

Referentiedag di 18-02-2025: weer uit KNMI (station 215), huishoudprofiel uit NEDU E1A_AZI_A 2025.
Al het overige is mock; zie data/mock/status.csv.
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2025
BRON = Path(__file__).parent / "bron"
UIT = Path(__file__).parent / "mock"
DATUM = "20250218"
rng = np.random.default_rng(SEED)

t = np.arange(96)
h = t / 4 + 0.125  # midden van het kwartier, in uren
tijd = [f"{i // 4:02d}:{(i % 4) * 15:02d}" for i in t]


def gauss(mu, sigma):
    """Gauss over de klok, doorlopend over middernacht."""
    d = np.abs(h - mu)
    d = np.minimum(d, 24 - d)
    return np.exp(-0.5 * (d / sigma) ** 2)


def plateau(start, eind, flank=0.75):
    return 1 / (1 + np.exp(-(h - start) / flank * 4)) * 1 / (1 + np.exp((h - eind) / flank * 4))


def ruis(x, sd=0.03):
    return np.clip(x * (1 + sd * rng.standard_normal(x.size)), 1e-6, None)


def als_fractie(x, d):
    """Schaal een vorm zodat de som over de dag gelijk is aan d (fractie van het jaar)."""
    return x / x.sum() * d


def knmi_dag() -> tuple[np.ndarray, np.ndarray]:
    """KNMI uurwaarden (UT, uur HH = HH-1 tot HH) naar 96 kwartieren lokale tijd (CET = UT+1).

    T: momentane waarde aan het eind van het uur, lineair geïnterpoleerd naar het kwartiermidden.
    I: uursom Q (J/cm²) als gemiddelde W/m², gelijk verdeeld over de vier kwartieren van dat uur.
    """
    regels = [r for r in (BRON / f"knmi_215_{DATUM}_uur.txt").read_text().splitlines()
              if r.strip() and not r.startswith("#")]
    k = pd.read_csv(io.StringIO("\n".join(regels)), header=None, names=["stn", "datum", "hh", "T", "Q"],
                    skipinitialspace=True)
    ut = pd.to_datetime(k["datum"].astype(str)) + pd.to_timedelta(k["hh"], unit="h")  # eind van het uur
    cet = ut + pd.Timedelta(hours=1)
    dag0 = pd.Timestamp(DATUM)
    uur_eind = ((cet - dag0) / pd.Timedelta(hours=1)).to_numpy()
    T = np.interp(h, uur_eind, k["T"].to_numpy() / 10)
    I = np.zeros(96)
    for e, q in zip(uur_eind, k["Q"].to_numpy()):
        if 1 <= e <= 24:
            I[int(e - 1) * 4:int(e) * 4] = q * 1e4 / 3600
    return T, I


def g1a_ruimteverwarming() -> np.ndarray:
    """NEDU gasprofiel G1A, temperatuurafhankelijk deel: TAP[h] = RER[h] × max(0, TST[h] − TAC).

    TAC = etmaalgemiddelde effectieve temperatuur T − W/1,5 (KNMI daggegevens). Vereenvoudiging: de TAC van
    deze dag geldt voor alle 24 uur (de gasdag loopt formeel van 06:00 tot 06:00). Uur gelijk over 4 kwartieren.
    """
    regels = [r for r in (BRON / f"knmi_215_{DATUM}_dag.txt").read_text().splitlines()
              if r.strip() and not r.startswith("#")]
    _, _, tg, fg = [float(x) for x in regels[0].split(",")]
    tac = tg / 10 - (fg / 10) / 1.5
    g = pd.read_csv(BRON / f"nedu_2025_g1a_{DATUM}.csv")
    tap = g["G1A_RER"].to_numpy() * np.maximum(g["G1A_TST"].to_numpy() - tac, 0)
    return np.repeat(tap / 4, 4)


T, I = knmi_dag()
prijs = 70 + 60 * gauss(8.5, 1.2) + 110 * gauss(18.5, 1.5) + 25 * gauss(13, 3) - 15 * gauss(3.5, 2)
prijs = prijs + 3 * rng.standard_normal(96)

dag = pd.DataFrame({"datum": pd.Timestamp(DATUM).date().isoformat(), "kwartier": t, "tijd": tijd, "T": T.round(2), "I": I.round(2), "prijs": prijs.round(2)})

prof = pd.DataFrame({"kwartier": t, "tijd": tijd})
prof["nedu_e1a"] = pd.read_csv(BRON / f"nedu_2025_e1a_{DATUM}.csv")["E1A_AZI_A"].to_numpy()
prof["nedu_g1a_tap"] = g1a_ruimteverwarming()
# NEDU E3 (E3A t/m E3D zijn gelijk); profiel telt op tot 2 per jaar (normaal + laag), dus ÷ 2
prof["nedu_e3"] = pd.read_csv(BRON / f"nedu_2025_e3_{DATUM}.csv")["E3A_A"].to_numpy() / 2
prof["koken"] = ruis(0.02 + 0.15 * gauss(7.5, 0.6) + 0.25 * gauss(12.5, 0.8) + 1.0 * gauss(18.0, 0.9))
prof["ev_ongestuurd"] = ruis(0.05 + 0.2 * gauss(8.5, 1.0) + 1.0 * gauss(18.5, 1.8))
prof["ev_slim"] = ruis(0.03 + 1.0 * gauss(2.5, 2.0))
prof["logistiek_bestel"] = ruis(0.1 + 1.0 * gauss(21.0, 2.5) + 0.3 * gauss(13.0, 1.5))
prof["logistiek_truck"] = ruis(0.15 + 1.0 * gauss(22.5, 2.0) + 0.5 * gauss(12.5, 1.0))
prof["sector_kantoor"] = als_fractie(ruis(0.25 + plateau(8, 18)), 0.0033)
prof["sector_winkel"] = als_fractie(ruis(0.2 + plateau(9, 21)), 0.0030)
prof["sector_onderwijs"] = als_fractie(ruis(0.15 + plateau(8, 16)), 0.0035)
prof["sector_zorg"] = als_fractie(ruis(0.6 + 0.5 * plateau(7, 20)), 0.0029)
for c in prof.columns[4:]:
    prof[c] = prof[c].round(10)

buurten = pd.DataFrame([{
    "buurt_code": "BU_MOCK_A",
    "buurt_naam": "Buurt A",
    "woningen": 1500,
    "huishoudens": 1450,
    "kwp_woningen": round(1500 * 15_648 / 11_286),  # Zonnedakje gemeente (kWp woningen) naar aandeel woningen
    "gas_m3_per_woning": 960,  # Klimaatmonitor: gemiddelde Oegstgeest, alle woningen
    "personenautos": 1300,
    "bestelautos": 120,
    "vrachtautos": 10,
    "warmteoplossing": "geen",
    "isolatie_reductie": 0,
    "ev_toename_pct": 0,
}])

# Verhoudingen tussen woningtypen zijn mock, geschaald naar het bekende gemeentegemiddelde netto (1.920 kWh)
_types = [("Vrijstaand", 150, 3600), ("2-onder-1-kap", 225, 3000), ("Hoekwoning", 225, 2500),
          ("Tussenwoning", 450, 2300), ("Appartement", 450, 1800)]
_schaal = 1920 / (sum(n * e for _, n, e in _types) / sum(n for _, n, _ in _types))
woningtypen = pd.DataFrame([
    {"buurt_code": "BU_MOCK_A", "woningtype": w, "woningen": n, "e_netto_kwh_per_woning": round(e * _schaal, -1)}
    for w, n, e in _types
])

# Energielabels: gemeenteverdeling uit Zonnedakje (adressen met label); factoren en buurtverdeling zijn mock
energielabels = pd.DataFrame({
    "label": ["A+", "A", "B", "C", "D", "E", "F", "G"],
    "factor": [0.6, 0.7, 0.85, 1.0, 1.1, 1.2, 1.3, 1.4],
    "adressen_gemeente": [701, 2744, 904, 1471, 453, 413, 218, 188],
})
labels_buurt = pd.DataFrame({"buurt_code": "BU_MOCK_A", "label": energielabels["label"],
                             "adressen": [40, 180, 90, 160, 70, 60, 40, 30]})

sectoren = pd.DataFrame([
    {"buurt_code": "BU_MOCK_A", "sector": "Kantoor", "e_jaar_kwh": 900_000, "profiel": "sector_kantoor", "teken": 1},
    {"buurt_code": "BU_MOCK_A", "sector": "Winkel", "e_jaar_kwh": 600_000, "profiel": "sector_winkel", "teken": 1},
    {"buurt_code": "BU_MOCK_A", "sector": "Onderwijs", "e_jaar_kwh": 400_000, "profiel": "sector_onderwijs", "teken": 1},
    {"buurt_code": "BU_MOCK_A", "sector": "Zorg", "e_jaar_kwh": 700_000, "profiel": "sector_zorg", "teken": 1},
    {"buurt_code": "BU_MOCK_A", "sector": "Opwek (zon bedrijven)", "e_jaar_kwh": 300_000, "profiel": "instraling", "teken": -1},
])

UIT.mkdir(exist_ok=True)
dag.to_csv(UIT / "referentiedag.csv", index=False)
prof.to_csv(UIT / "profielen.csv", index=False)
buurten.to_csv(UIT / "buurten.csv", index=False)
woningtypen.to_csv(UIT / "woningtypen.csv", index=False)
energielabels.to_csv(UIT / "energielabels.csv", index=False)
labels_buurt.to_csv(UIT / "labels_buurt.csv", index=False)
sectoren.to_csv(UIT / "sectoren.csv", index=False)
print("mock geschreven naar", UIT)
