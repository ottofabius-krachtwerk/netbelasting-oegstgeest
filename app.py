"""Netbelasting Oegstgeest: rekenkaarten per buurt op de referentiedag."""
import pandas as pd
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, stapeling
from model.data import WARMTEOPLOSSINGEN, DataFout, laad
from ui import tabs
from ui.kaarten import VASTGESTELD, VOLGORDE, kaartnaam, kleur

st.set_page_config(page_title="Netbelasting Oegstgeest", layout="wide")
st.markdown("<style>.block-container{padding-top:2.2rem;padding-bottom:1rem}"
            "[data-testid='stMetricValue']{font-size:1.4rem}</style>", unsafe_allow_html=True)

BADGE = {"mock": ":gray-badge[mock]", "placeholder": ":orange-badge[placeholder]"}


@st.cache_data
def _laad(bron: str):
    return laad(bron)


# Sidebar: databron, buurt, keuzes per buurt en alle variabelen
with st.sidebar:
    echt = st.toggle("Echte data", value=False)
    bron = "real" if echt else "mock"
    try:
        data = _laad(bron)
    except DataFout as e:
        st.error(str(e))
        st.stop()
    if data.buurten.empty:
        st.error(f"data/{bron}/buurten.csv bevat geen buurten.")
        st.stop()
    code = st.selectbox("Buurt", data.buurten.index, format_func=lambda c: data.buurten.loc[c, "buurt_naam"])
    b = data.buurten.loc[code].copy()
    b["warmteoplossing"] = st.selectbox("Warmteoplossing", WARMTEOPLOSSINGEN,
                                        index=WARMTEOPLOSSINGEN.index(b["warmteoplossing"]), key=f"{bron}:wo:{code}")
    b["isolatie_reductie"] = st.number_input("Isolatie: reductie warmtevraag (%)", 0.0, 80.0,
                                             float(b["isolatie_reductie"]), 1.0, key=f"{bron}:iso:{code}")
    wp_vorm = st.radio("Vorm warmtepomp (all-electric)", k3_warmtepomp.VORMEN, horizontal=True,
                       format_func=lambda v: {"G1A": "G1A (bovengrens)", "vlak": "vlak (ondergrens)"}[v],
                       key=f"{bron}:wpvorm")
    p = {}
    for kaart in VOLGORDE:
        rijen = data.parameters[data.parameters["kaart"] == kaart]
        if rijen.empty:
            continue
        with st.expander(kaartnaam(kaart).replace(" ", " · ", 1)):
            for naam, r in rijen.iterrows():
                label = f"{r['label']} ({r['eenheid']}) {BADGE.get(r['status'], '')}"
                p[naam] = st.number_input(label, float(r["min"]), float(r["max"]), float(r["waarde"]),
                                          float(r["stap"]), key=f"{bron}:{naam}",
                                          help=r["bron"] if isinstance(r["bron"], str) else None)

dag, prof = data.dag, data.profielen
wt = data.woningtypen[data.woningtypen["buurt_code"] == code]
r1 = k1_basis.bereken(b, p, dag, prof, wt)

datum = pd.Timestamp(dag["datum"].iloc[0])
kop = f"#### Netbelasting · {b['buurt_naam']} · {['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'][datum.weekday()]} {datum:%d-%m-%Y}"
st.markdown(kop + ("  :gray-badge[mockdata]" if bron == "mock" else ""))

def _tablabel(kaart: int, tekst: str) -> str:
    """Tabtitel gekleurd naar de status van de methodiek: groen vastgesteld, rood open."""
    return f":{'green' if VASTGESTELD.get(kaart, False) else 'red'}[{tekst}]"


t = dict(zip(VOLGORDE + [9], st.tabs([_tablabel(k, kaartnaam(k)) for k in VOLGORDE]
                                     + [_tablabel(9, f"{len(VOLGORDE) + 1} Stapeling")])))
r3 = k3_warmtepomp.bereken(b, p, dag, prof, wp_vorm=wp_vorm)
varianten = {o: k3_warmtepomp.bereken(b, p, dag, prof, o, wp_vorm) for o in WARMTEOPLOSSINGEN}
r4 = k4_laden_auto.bereken(b, p, prof)
r7 = k7_zon.bereken(b, p, dag)
r2 = k2_koken.bereken(b, p, prof)
r5 = k5_logistiek.bereken(b, p, prof)
r6 = k6_mkb.bereken(p, dag, prof, data.sectoren[data.sectoren["buurt_code"] == code])

with t[3]:
    tabs.kaart3(r3, varianten, p, data.status, b["isolatie_reductie"])
with t[4]:
    tabs.kaart4(r4, p, data.status)
with t[7]:
    tabs.kaart7(r7, p, data.status)
with t[1]:
    tabs.kaart1(r1, data.status)
with t[2]:
    tabs.kaart2(r2, data.status)
with t[5]:
    tabs.kaart5(r5, p, data.status)
with t[6]:
    tabs.kaart6(r6, data.status)
# Stapeling zonder logistiek (placeholder) en thuisbatterij (nog niet uitgewerkt), in tabvolgorde
alle = {1: r1, 2: r2, 3: r3, 4: r4, 6: r6, 7: r7}
IN_STAPEL = {k: alle[k] for k in VOLGORDE if k in alle}
P_kaart = {kaartnaam(k): (r.P_tot if k == 6 else r.P) for k, r in IN_STAPEL.items()}
e_kaart = {kaartnaam(k): (float((r.sectoren["teken"] * r.sectoren["E"]).sum()) if k == 6 else
                                 (-1 if k == 7 else 1) * r.N * r.E) for k, r in IN_STAPEL.items()}
rs = stapeling.bereken(P_kaart, e_kaart)
with t[8]:
    tabs.kaart8()
with t[9]:
    tabs.stapeling(rs, [kleur(k) for k in IN_STAPEL])
