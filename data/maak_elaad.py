"""Zet de ElaadNL-laadpuntprofielen 2025 om naar data/bron/elaad_laadpunten_2025.csv.

Gebruik: .venv/bin/python data/maak_elaad.py <map met elaad_cp_thuis_standaard, elaad_cp_publiek_standaard en
elaad_cp_publiek_smart>. Elke map bevat profile.csv: een kolom datetime (CET/CEST, begin van het kwartier) en per
gegenereerd laadpunt het vermogen in kW.

Per profiel en per kwartier van de dag, over alle laadpunten en alle weekdagen (ma t/m vr) van 2025:
- mu: gemiddeld vermogen per laadpunt (kW);
- sd: standaarddeviatie per laadpunt (kW), voor de 95 %-grens met √N.
Slim thuisladen is een aanname: vlak van 01:00 tot 06:00, met dezelfde energie per laadpunt als thuis standaard, sd 0.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BRON = Path(__file__).parent / "bron"
MAPPEN = {"ongestuurd_thuis": "elaad_cp_thuis_standaard", "ongestuurd_publiek": "elaad_cp_publiek_standaard",
          "slim_publiek": "elaad_cp_publiek_smart"}


def lees(pad: Path) -> tuple[np.ndarray, np.ndarray, int]:
    df = pd.read_csv(pad)
    t = pd.to_datetime(df["datetime"].str[:19])  # lokale kloktijd
    X = df.drop(columns="datetime").astype(float)
    werkdag = (t.dt.day_of_week < 5).to_numpy()
    X, t = X[werkdag], t[werkdag]
    k = (t.dt.hour * 4 + t.dt.minute // 15).to_numpy()
    assert (pd.Series(k).value_counts() == werkdag.sum() / 96).all(), "niet elk kwartier even vaak"
    g = X.groupby(k)
    mu = g.mean().mean(axis=1).to_numpy()
    sd = g.apply(lambda d: np.std(d.to_numpy())).to_numpy()
    return mu, sd, X.shape[1]


def main(map_elaad: Path) -> None:
    uit = pd.DataFrame({"kwartier": range(96), "tijd": [f"{i // 4:02d}:{i % 4 * 15:02d}" for i in range(96)]})
    for naam, mapnaam in MAPPEN.items():
        mu, sd, n = lees(map_elaad / mapnaam / "profile.csv")
        uit[f"ev_{naam}"], uit[f"ev_{naam}_sd"] = mu.round(6), sd.round(6)
        print(f"{mapnaam}: {n} laadpunten, {mu.sum() / 4:.2f} kWh per laadpunt per weekdag")
    e_thuis = uit["ev_ongestuurd_thuis"].sum() / 4
    nacht = (uit["kwartier"] >= 4) & (uit["kwartier"] < 24)  # 01:00 tot 06:00
    uit["ev_slim_thuis"] = np.where(nacht, e_thuis * 4 / nacht.sum(), 0.0).round(6)
    uit["ev_slim_thuis_sd"] = 0.0
    uit.to_csv(BRON / "elaad_laadpunten_2025.csv", index=False)
    print("geschreven:", BRON / "elaad_laadpunten_2025.csv")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
