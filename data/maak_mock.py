"""Genereert de mockdataset in data/mock/ (vaste seed).

Referentiedag di 18-02-2025: huishoudprofiel uit NEDU E1A_AZI_A 2025. De buitentemperatuur is een aanname (−10 °C,
parameters.csv), dus instraling_dayahead.csv heeft geen temperatuurkolom.
Instraling (mock): KNMI station 215 van wo 12-02-2025, een volledig bewolkte winterdag (8/8), in plaats van de
zonnige 18-02.
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
DATUM_ZON = "20250212"  # mock: instraling van een bewolkte winterdag
rng = np.random.default_rng(SEED)

t = np.arange(96)
h = t / 4 + 0.125  # midden van het kwartier, in uren
tijd = [f"{i // 4:02d}:{(i % 4) * 15:02d}" for i in t]


def gauss(mu, sigma):
    """Gauss over de klok, doorlopend over middernacht."""
    d = np.abs(h - mu)
    d = np.minimum(d, 24 - d)
    return np.exp(-0.5 * (d / sigma) ** 2)


def ruis(x, sd=0.03):
    return np.clip(x * (1 + sd * rng.standard_normal(x.size)), 1e-6, None)


def knmi_instraling(datum: str) -> np.ndarray:
    """KNMI uursom Q (J/cm², UT; uur HH = HH-1 tot HH) als gemiddelde W/m² per kwartier lokale tijd (CET = UT+1)."""
    regels = [r for r in (BRON / f"knmi_215_{datum}_uur_q.txt").read_text().splitlines()
              if r.strip() and not r.startswith("#")]
    k = pd.read_csv(io.StringIO("\n".join(regels)), header=None, names=["stn", "datum", "hh", "Q"],
                    skipinitialspace=True)
    cet = pd.to_datetime(k["datum"].astype(str)) + pd.to_timedelta(k["hh"], unit="h") + pd.Timedelta(hours=1)
    uur_eind = ((cet - pd.Timestamp(datum)) / pd.Timedelta(hours=1)).to_numpy()
    I = np.zeros(96)
    for e, q in zip(uur_eind, k["Q"].to_numpy()):
        if 1 <= e <= 24:
            I[int(e - 1) * 4:int(e) * 4] = q * 1e4 / 3600
    return I


I = knmi_instraling(DATUM_ZON)
# Day-ahead prijs: gemiddelde per kwartier van de 5 koudste werkdagen winter 2025/26 (EPEX NL, Energy Quantified)
prijs = pd.read_csv(BRON / "da_prijs_koudste_5_werkdagen_2025-26.csv")["gemiddelde"].to_numpy()
rng.standard_normal(96)  # vroeger de ruis op de mockprijs; blijft staan zodat de andere mockprofielen gelijk blijven

dag = pd.DataFrame({"datum": pd.Timestamp(DATUM).date().isoformat(), "kwartier": t, "tijd": tijd, "I": I.round(2), "prijs": prijs.round(2)})

prof = pd.DataFrame({"kwartier": t, "tijd": tijd})
prof["nedu_e1a"] = pd.read_csv(BRON / f"nedu_2025_e1a_{DATUM}.csv")["E1A_AZI_A"].to_numpy()
# mock: gemeten aggregaatprofiel warmtepompen op een koude winterdag (ochtendpiek na nachtverlaging, avondbult)
# eigen toevalsgenerator, zodat de ruis van de andere mockprofielen gelijk blijft
_wp = 1.0 + 0.45 * gauss(7.0, 1.0) + 0.25 * gauss(18.5, 2.0) - 0.15 * gauss(14.0, 2.5) - 0.1 * gauss(2.5, 2.0)
prof["wp_aggregaat"] = _wp * (1 + 0.02 * np.random.default_rng(SEED + 1).standard_normal(96))
# Kookprofiel: RAMP NL, winterwerkdagen, CET, middagpiek verlaagd (data/maak_koken.py)
prof["koken"] = pd.read_csv(BRON / "koken_ramp_nl.csv")["koken"].to_numpy()
rng.standard_normal(96)  # vroeger de ruis op het mock-kookprofiel; blijft staan zodat de andere mockprofielen gelijk blijven
# ElaadNL-laadpuntprofielen 2025 (kW per laadpunt, gemiddelde en spreiding), uit data/maak_elaad.py
_elaad = pd.read_csv(BRON / "elaad_laadpunten_2025.csv")
for _c in ["ev_ongestuurd_thuis", "ev_ongestuurd_thuis_sd", "ev_slim_thuis", "ev_slim_thuis_sd",
           "ev_ongestuurd_publiek", "ev_ongestuurd_publiek_sd", "ev_slim_publiek", "ev_slim_publiek_sd"]:
    prof[_c] = _elaad[_c].to_numpy()
prof["logistiek_bestel"] = ruis(0.1 + 1.0 * gauss(21.0, 2.5) + 0.3 * gauss(13.0, 1.5))
prof["logistiek_truck"] = ruis(0.15 + 1.0 * gauss(22.5, 2.0) + 0.5 * gauss(12.5, 1.0))
for c in prof.columns[4:]:
    prof[c] = prof[c].round(10)

buurten = pd.DataFrame([{
    "buurt_code": "BU_MOCK_A",
    "buurt_naam": "Buurt A",
    # mock: woningen per woningtype (samen 1.500)
    "woningen_vrijstaand": 150,
    "woningen_twee_onder_een_kap": 225,
    "woningen_hoekwoning": 225,
    "woningen_tussenwoning": 450,
    "woningen_appartement": 450,
    "huishoudens": 1450,
    # mock: bruto jaaropwek woningen (kWh): Zonnedakje gemeente-kWp naar aandeel woningen × 875 kWh/kWp (1.213 kWh per woning)
    "zon_kwh_jaar": round(round(1500 * 15_648 / 11_286) * 875),
    "gas_m3_per_woning": 960,  # Klimaatmonitor: gemiddelde Oegstgeest, alle woningen
    # mock: resterende dakpotentie zon, alle daken in de buurt (kWh/jaar) = 3 × huidige opwek woningen; Zonnedakje volgt
    "zon_potentie_kwh_jaar": 3 * round(round(1500 * 15_648 / 11_286) * 875),
    # mock: prognose totaal aantal EV's in de buurt per scenario en jaar (2025: 632 BEV gemeente naar aandeel woningen)
    "ev_laag_2025": 84,
    "ev_laag_2035": 350,
    "ev_laag_2050": 800,
    "ev_middel_2025": 84,
    "ev_middel_2035": 500,
    "ev_middel_2050": 1050,
    "ev_hoog_2025": 84,
    "ev_hoog_2035": 700,
    "ev_hoog_2050": 1300,
    "zon_bedrijven_kwh_jaar": 300_000,  # mock: jaaropwek zon op overige daken (Zonnedakje alle daken min woningen)
}])


# mock: elektriciteitsverbruik per bedrijfstak voor de gemeente (Klimaatmonitor), samen 36 GWh zoals de gemeente in 2024
bedrijfstakken = pd.DataFrame([
    {"bedrijfstak": "Handel", "e_jaar_kwh_gemeente": 8_000_000},
    {"bedrijfstak": "Zakelijke dienstverlening", "e_jaar_kwh_gemeente": 7_000_000},
    {"bedrijfstak": "Gezondheids- en welzijnszorg", "e_jaar_kwh_gemeente": 7_000_000},
    {"bedrijfstak": "Onderwijs", "e_jaar_kwh_gemeente": 4_000_000},
    {"bedrijfstak": "Openbaar bestuur", "e_jaar_kwh_gemeente": 3_000_000},
    {"bedrijfstak": "Horeca", "e_jaar_kwh_gemeente": 2_000_000},
    {"bedrijfstak": "Industrie", "e_jaar_kwh_gemeente": 2_000_000},
    {"bedrijfstak": "Overig", "e_jaar_kwh_gemeente": 3_000_000},
])

UIT.mkdir(exist_ok=True)
dag.to_csv(UIT / "instraling_dayahead.csv", index=False)
prof.to_csv(UIT / "profielen.csv", index=False)
buurten.to_csv(UIT / "buurten.csv", index=False)
bedrijfstakken.to_csv(UIT / "bedrijfstakken.csv", index=False)
print("mock geschreven naar", UIT)
