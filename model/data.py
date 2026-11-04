"""Inlezen van een dataset (mock of echt). Beide gebruiken hetzelfde schema."""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

SCHEMA = {
    "buurten.csv": ["buurt_code", "buurt_naam", "woningen", "huishoudens", "zon_kwh_jaar", "gas_m3_per_woning",
                    "warmteoplossing", "isolatie_reductie",
                    "ev_extra", "pomp_kw_buurt", "wp_aandeel_huidig", "zon_potentie_kwh_jaar", "zon_benutting_pct", "log_bestel_extra", "log_truck_extra",
                    "zon_bedrijven_kwh_jaar"],
    "woningtypen.csv": ["buurt_code", "woningtype", "woningen", "e_netto_kwh_per_woning"],
    "bedrijfstakken.csv": ["bedrijfstak", "e_jaar_kwh_gemeente"],
    "referentiedag.csv": ["datum", "kwartier", "tijd", "T", "I", "prijs"],
    "profielen.csv": ["kwartier", "tijd", "nedu_e1a", "wp_aggregaat", "nedu_e3", "koken", "ev_ongestuurd", "ev_slim", "logistiek_bestel",
                      "logistiek_truck"],
    "parameters.csv": ["naam", "kaart", "rol", "label", "waarde", "eenheid", "min", "max", "stap", "status", "bron"],
    "status.csv": ["naam", "status", "bron"],
}
RANG = {"bron": 0, "aanname": 0, "mock": 1, "placeholder": 2}
WARMTEOPLOSSINGEN = ["geen", "all-electric", "ZLT", "MT"]


class DataFout(Exception):
    pass


@dataclass
class Dataset:
    bron: str
    buurten: pd.DataFrame
    woningtypen: pd.DataFrame
    bedrijfstakken: pd.DataFrame
    dag: pd.DataFrame
    profielen: pd.DataFrame
    parameters: pd.DataFrame
    statussen: pd.DataFrame

    def status(self, *namen: str) -> str:
        """Zwakste status van de gebruikte tabellen, reeksen en parameters: bron < mock < placeholder."""
        st = [self.statussen["status"].get(n) or self.parameters["status"].get(n) or "mock" for n in namen]
        return max(st, key=lambda s: RANG.get(s, 1)) if st else "bron"


def laad(bron: str) -> Dataset:
    """Lees data/<bron>/ en controleer het schema. Gooit DataFout met alle problemen."""
    map_ = DATA / bron
    fouten, tabellen = [], {}
    for bestand, kolommen in SCHEMA.items():
        pad = map_ / bestand
        if not pad.exists():
            fouten.append(f"{bestand} ontbreekt")
            continue
        df = pd.read_csv(pad)
        mist = [k for k in kolommen if k not in df.columns]
        if mist:
            fouten.append(f"{bestand}: kolommen ontbreken: {', '.join(mist)}")
        tabellen[bestand] = df
    if not fouten:
        for bestand in ("referentiedag.csv", "profielen.csv"):
            if len(tabellen[bestand]) != 96:
                fouten.append(f"{bestand}: {len(tabellen[bestand])} rijen, verwacht 96")
        for w in set(tabellen["buurten.csv"]["warmteoplossing"]) - set(WARMTEOPLOSSINGEN):
            fouten.append(f"buurten.csv: onbekende warmteoplossing '{w}'")
    if fouten:
        raise DataFout(f"data/{bron}/: " + "; ".join(fouten))
    return Dataset(
        bron=bron,
        buurten=tabellen["buurten.csv"].set_index("buurt_code"),
        woningtypen=tabellen["woningtypen.csv"],
        bedrijfstakken=tabellen["bedrijfstakken.csv"],
        dag=tabellen["referentiedag.csv"].sort_values("kwartier").reset_index(drop=True),
        profielen=tabellen["profielen.csv"].sort_values("kwartier").reset_index(drop=True),
        parameters=tabellen["parameters.csv"].set_index("naam"),
        statussen=tabellen["status.csv"].set_index("naam"),
    )
