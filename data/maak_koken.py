"""Leidt het kookprofiel af uit de RAMP-kookprofielen voor Nederland en schrijft data/bron/koken_ramp_nl.csv.

Gebruik: .venv/bin/python data/maak_koken.py <pad naar nld.csv uit Zenodo record 6579421>.
Bron: Lombardi en Pickering, cooking demand profiles Euro-Calliope (RAMP, TU Delft/ETH, 2022, CC BY 4.0): uurwaarden
2000 tot 2018, gesimuleerd met Nederlandse maaltijdtijden uit de Europese tijdsbestedingsenquête (HETUS).
Stappen:
1. gemiddelde per uur over de werkdagen van december, januari en februari;
2. tijden van UTC naar wintertijd (CET = UTC + 1): in de zomer valt elke piek precies een uur eerder in de data;
3. middagpiek verlagen (aanname): RAMP neemt Italiaans kookgedrag over (elke dag een warme lunch); 11:00 tot 15:00
   lokale tijd wordt geschaald tot LUNCH van de dag, de rest naar verhouding;
4. elk uur gelijk verdeeld over zijn vier kwartieren; het profiel telt op tot 1.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BRON = Path(__file__).parent / "bron"
LUNCH = 0.125  # aanname: deel van de dag rond het middaguur, in plaats van circa 40 % in RAMP
UREN_LUNCH = range(11, 15)  # lokale tijd, 11:00 tot 15:00


def main(pad: Path) -> None:
    d = pd.read_csv(pad, header=None, names=["t", "jaar", "land", "w"])
    d["t"] = pd.to_datetime(d["t"])
    d = d[(d.t.dt.day_of_week < 5) & d.t.dt.month.isin([12, 1, 2])]
    utc = d.groupby(d.t.dt.hour)["w"].mean().reindex(range(24), fill_value=0).to_numpy()
    lokaal = np.roll(utc, 1)  # uur h in UTC is uur h + 1 in CET
    lokaal = lokaal / lokaal.sum()
    lunch = np.isin(np.arange(24), list(UREN_LUNCH))
    aangepast = np.where(lunch, lokaal / lokaal[lunch].sum() * LUNCH, lokaal / lokaal[~lunch].sum() * (1 - LUNCH))
    kwartier = np.repeat(aangepast / 4, 4)
    uit = pd.DataFrame({"kwartier": range(96), "tijd": [f"{i // 4:02d}:{i % 4 * 15:02d}" for i in range(96)],
                        "koken": kwartier.round(8)})
    uit.to_csv(BRON / "koken_ramp_nl.csv", index=False)
    print("RAMP lokaal (% per uur):", " ".join(f"{h}:{v * 100:.1f}" for h, v in enumerate(lokaal)))
    print("aangepast   (% per uur):", " ".join(f"{h}:{v * 100:.1f}" for h, v in enumerate(aangepast)))
    print("geschreven:", BRON / "koken_ramp_nl.csv")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
