"""Inlezen van een dataset (mock of echt). Beide gebruiken hetzelfde schema."""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# woningtype -> sleutel; per type een kolom woningen_<sleutel> in buurten.csv en een parameter e_netto_<sleutel>
WONINGTYPEN = {"Vrijstaand": "vrijstaand", "2-onder-1-kap": "twee_onder_een_kap", "Hoekwoning": "hoekwoning",
               "Tussenwoning": "tussenwoning", "Appartement": "appartement"}
SCHEMA = {
    "buurten.csv": ["buurt_code", "buurt_naam", *[f"woningen_{k}" for k in WONINGTYPEN.values()], "huishoudens",
                    "zon_kwh_jaar", "gas_m3_per_woning", "zon_potentie_kwh_jaar", "zon_bedrijven_kwh_jaar"],
    "bedrijfstakken.csv": ["bedrijfstak", "e_jaar_kwh_gemeente"],
    "instraling_dayahead.csv": ["datum", "kwartier", "tijd", "I", "prijs"],
    "profielen.csv": ["kwartier", "tijd", "nedu_e1a", "wp_aggregaat", "koken",
                      "ev_ongestuurd_thuis", "ev_ongestuurd_thuis_sd", "ev_slim_thuis", "ev_slim_thuis_sd",
                      "ev_ongestuurd_publiek", "ev_ongestuurd_publiek_sd", "ev_slim_publiek", "ev_slim_publiek_sd", "logistiek_bestel",
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
        for bestand in ("instraling_dayahead.csv", "profielen.csv"):
            if len(tabellen[bestand]) != 96:
                fouten.append(f"{bestand}: {len(tabellen[bestand])} rijen, verwacht 96")
    if fouten:
        raise DataFout(f"data/{bron}/: " + "; ".join(fouten))
    return Dataset(
        bron=bron,
        buurten=tabellen["buurten.csv"].set_index("buurt_code").assign(  # woningen = som van de woningtypen
            woningen=lambda df: df[[f"woningen_{k}" for k in WONINGTYPEN.values()]].sum(axis=1)),
        bedrijfstakken=tabellen["bedrijfstakken.csv"],
        dag=tabellen["instraling_dayahead.csv"].sort_values("kwartier").reset_index(drop=True),
        profielen=tabellen["profielen.csv"].sort_values("kwartier").reset_index(drop=True),
        parameters=tabellen["parameters.csv"].set_index("naam"),
        statussen=tabellen["status.csv"].set_index("naam"),
    )
