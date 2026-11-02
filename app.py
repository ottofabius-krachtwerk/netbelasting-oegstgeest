"""Netbelasting Oegstgeest: rekenkaarten per buurt op de referentiedag."""
import pandas as pd
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij, stapeling
from model.data import WARMTEOPLOSSINGEN, DataFout, laad
from ui import tabs
from ui.kaarten import VASTGESTELD, VOLGORDE, kaartnaam, kleur

st.set_page_config(page_title="Netbelasting Oegstgeest", layout="wide")
st.markdown("<style>.block-container{padding-top:2.2rem;padding-bottom:1rem}"
            "[data-testid='stMetricValue']{font-size:1.4rem}</style>", unsafe_allow_html=True)

BADGE = {"mock": ":gray-badge[mock]", "placeholder": ":orange-badge[placeholder]"}


def _tablabel(kaart: int, tekst: str) -> str:
    """Tabtitel gekleurd naar de status van de methodiek: groen vastgesteld, rood open."""
    return f":{'green' if VASTGESTELD.get(kaart, False) else 'red'}[{tekst}]"


TABLABEL = {k: _tablabel(k, kaartnaam(k)) for k in VOLGORDE} | {9: _tablabel(9, f"{len(VOLGORDE) + 1} Stapeling")}
# De gekozen tab (uit de vorige run) bepaalt welke groep in de zijbalk open staat
ACTIEF = {v: k for k, v in TABLABEL.items()}.get(st.session_state.get("tabkeuze"), VOLGORDE[0])


@st.cache_data
def _laad(bron: str):
    return laad(bron)


# Sidebar: databron en buurt gelden voor alle tabs; de rest staat in de groep van de tab waar het bij hoort
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
    buurt = b["buurt_naam"]
    keuzes = {}

    def _keuzes(kaart: int) -> None:
        """Instellingen die bij één tab horen, bovenaan de groep van die tab. Per-buurt-invoer heeft de buurtnaam."""
        if kaart == 3:
            b["warmteoplossing"] = st.selectbox(f"Warmteoplossing ({buurt})", WARMTEOPLOSSINGEN,
                                                index=WARMTEOPLOSSINGEN.index(b["warmteoplossing"]),
                                                key=f"{bron}:wo:{code}")
            b["isolatie_reductie"] = st.number_input(f"Isolatie: reductie warmtevraag (%, {buurt})", 0.0, 80.0,
                                                     float(b["isolatie_reductie"]), 1.0, key=f"{bron}:iso:{code}")
            keuzes["wp_vorm"] = st.radio("Vorm warmtepomp (all-electric)", k3_warmtepomp.VORMEN, horizontal=True,
                                         format_func=lambda v: {"G1A": "G1A (bovengrens)", "vlak": "vlak (ondergrens)"}[v],
                                         key=f"{bron}:wpvorm")
        elif kaart == 4:
            b["ev_toename_pct"] = st.number_input(f"EV toename (% van de personenauto's, {buurt})", 0.0, 100.0,
                                                  float(b["ev_toename_pct"]), 1.0, key=f"{bron}:ev:{code}")
        elif kaart == 6:
            keuzes["mkb_bron"] = st.radio("Sectorprofielen", k6_mkb.PROFIELBRONNEN, horizontal=True,
                                          key=f"{bron}:mkbbron")
        elif kaart == 8:
            keuzes["bat_modus"] = st.radio("Batterijmodus", k8_batterij.MODI, key=f"{bron}:batmodus")

    p = {}
    for kaart in VOLGORDE:
        rijen = data.parameters[data.parameters["kaart"] == kaart]
        if rijen.empty and kaart not in (3, 4, 6, 8):
            continue
        with st.expander(kaartnaam(kaart).replace(" ", " · ", 1), expanded=kaart == ACTIEF):
            _keuzes(kaart)
            for naam, r in rijen.iterrows():
                label = f"{r['label']} ({r['eenheid']}) {BADGE.get(r['status'], '')}"
                p[naam] = st.number_input(label, float(r["min"]), float(r["max"]), float(r["waarde"]),
                                          float(r["stap"]), key=f"{bron}:{naam}",
                                          help=r["bron"] if isinstance(r["bron"], str) else None)
    wp_vorm, mkb_bron, bat_modus = keuzes["wp_vorm"], keuzes["mkb_bron"], keuzes["bat_modus"]

dag, prof = data.dag, data.profielen
lb = data.labels_buurt[data.labels_buurt["buurt_code"] == code]
b["labelfactor"] = k3_warmtepomp.labelfactor(lb, data.energielabels)
labeltabel = data.energielabels.merge(lb[["label", "adressen"]], on="label", how="left").fillna({"adressen": 0})
labeltabel["aandeel_buurt"] = labeltabel["adressen"] / max(labeltabel["adressen"].sum(), 1)
wt = data.woningtypen[data.woningtypen["buurt_code"] == code]
r1 = k1_basis.bereken(b, p, dag, prof, wt)

datum = pd.Timestamp(dag["datum"].iloc[0])
kop = f"#### Netbelasting · {b['buurt_naam']} · {['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'][datum.weekday()]} {datum:%d-%m-%Y}"
st.markdown(kop + ("  :gray-badge[mockdata]" if bron == "mock" else ""))

# Tabkeuze met rerun: de zijbalk opent de groep van de gekozen tab, en alleen die tab wordt opgebouwd
t = dict(zip(TABLABEL, st.tabs(list(TABLABEL.values()), key="tabkeuze", on_change="rerun")))
r3 = k3_warmtepomp.bereken(b, p, dag, prof, wp_vorm=wp_vorm)
varianten = {o: k3_warmtepomp.bereken(b, p, dag, prof, o, wp_vorm) for o in WARMTEOPLOSSINGEN}
r4 = k4_laden_auto.bereken(b, p, prof)
r7 = k7_zon.bereken(b, p, dag)
r2 = k2_koken.bereken(b, p, prof)
r5 = k5_logistiek.bereken(b, p, prof)
sect = data.sectoren[data.sectoren["buurt_code"] == code]
r6 = k6_mkb.bereken(p, dag, prof, sect, mkb_bron)
mkb_opties = {o: k6_mkb.bereken(p, dag, prof, sect, o) for o in k6_mkb.PROFIELBRONNEN}

if t[3].open:
    with t[3]:
        tabs.kaart3(r3, varianten, p, data.status, b["isolatie_reductie"], labeltabel)
if t[4].open:
    with t[4]:
        tabs.kaart4(r4, p, data.status, b["ev_toename_pct"])
if t[7].open:
    with t[7]:
        tabs.kaart7(r7, p, data.status)
if t[1].open:
    with t[1]:
        tabs.kaart1(r1, data.status)
if t[2].open:
    with t[2]:
        tabs.kaart2(r2, data.status)
if t[5].open:
    with t[5]:
        tabs.kaart5(r5, p, data.status)
if t[6].open:
    with t[6]:
        tabs.kaart6(r6, mkb_opties, data.status)
r8 = k8_batterij.bereken(b, p, dag, r1.P / r1.N, r7.P / r7.N if r7.N else 0 * r7.P, bat_modus)

# Stapeling zonder logistiek (placeholder), in tabvolgorde
alle = {1: r1, 2: r2, 3: r3, 4: r4, 6: r6, 7: r7, 8: r8}
IN_STAPEL = {k: alle[k] for k in VOLGORDE if k in alle}
P_kaart = {kaartnaam(k): (r.P_tot if k == 6 else r.P) for k, r in IN_STAPEL.items()}
e_kaart = {kaartnaam(k): (float((r.sectoren["teken"] * r.sectoren["E"]).sum()) if k == 6 else
                          float(r.N * r.v.sum() / 4) if k == 8 else
                          (-1 if k == 7 else 1) * r.N * r.E) for k, r in IN_STAPEL.items()}
rs = stapeling.bereken(P_kaart, e_kaart)
if t[8].open:
    with t[8]:
        tabs.kaart8(r8, p, data.status)
if t[9].open:
    with t[9]:
        tabs.stapeling(rs, [kleur(k) for k in IN_STAPEL])
