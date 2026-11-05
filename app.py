"""Netbelasting Oegstgeest: rekenkaarten per buurt op de referentiedag."""
import pandas as pd
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij, stapeling
from model.data import DATA, EV_SCENARIOS, WARMTEOPLOSSINGEN, DataFout, laad
from ui import invoer, tabs
from ui.kaarten import ROOD, VOLGORDE, kaartnaam, kleur

st.set_page_config(page_title="Netbelasting Oegstgeest", layout="wide")
st.markdown("<style>.block-container{padding-top:2.2rem;padding-bottom:1rem}"
            "[data-testid='stMetricValue']{font-size:1.4rem}</style>", unsafe_allow_html=True)



TABLABEL = {k: f":red[{kaartnaam(k)}]" if k in ROOD else kaartnaam(k) for k in VOLGORDE} | {9: f"{len(VOLGORDE) + 1} Stapeling"}
# De gekozen tab (uit de vorige run) bepaalt welke groep in de zijbalk open staat
ACTIEF = {v: k for k, v in TABLABEL.items()}.get(st.session_state.get("tabkeuze"), VOLGORDE[0])


@st.cache_data
def _laad(bron: str, stempel: float):  # stempel telt mee in de cachesleutel
    return laad(bron)


def _stempel(bron: str) -> float:
    """Laatste wijziging van de CSV's van deze bron; een aangepast bestand laadt zo opnieuw in plaats van uit de cache."""
    return max((p.stat().st_mtime for p in (DATA / bron).glob("*.csv")), default=0.0)


# Sidebar: databron en buurt gelden voor alle tabs; de rest staat in de groep van de tab waar het bij hoort
with st.sidebar:
    echt = st.toggle("Echte data", value=False)
    bron = "real" if echt else "mock"
    try:
        data = _laad(bron, _stempel(bron))
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

    def _veld(naam: str, v: invoer.Veld, per_buurt: bool = False, standaard: float | None = None) -> float:
        """Eén invoerveld; per-buurt-velden hebben de buurtnaam in het label en een eigen sleutel per buurt."""
        label = f"{v.label} {buurt} ({v.eenheid})" if per_buurt else f"{v.label} ({v.eenheid})"
        return st.number_input(label, float(v.min), float(v.max), float(v.standaard if standaard is None else standaard),
                               float(v.stap), key=f"{bron}:{naam}:{code}" if per_buurt else f"{bron}:{naam}",
                               help=v.uitleg or None)

    def _keuzes(kaart: int) -> None:
        """Keuzes en per-buurt-invoer die bij één tab horen, bovenaan de groep van die tab."""
        for naam, v in invoer.PER_BUURT.items():
            if v.kaart == kaart and kaart != 3:
                b[naam] = _veld(naam, v, per_buurt=True)
        if kaart == 3:
            b["warmteoplossing"] = st.selectbox(f"Warmteoplossing ({buurt})", WARMTEOPLOSSINGEN,
                                                index=WARMTEOPLOSSINGEN.index(invoer.WARMTEOPLOSSING),
                                                key=f"{bron}:warmteoplossing:{code}")
            for naam in ("wp_aandeel_huidig", "isolatie_reductie"):
                b[naam] = _veld(naam, invoer.PER_BUURT[naam], per_buurt=True)
            wo = b["warmteoplossing"]
            keuzes["pomp_invoer"], keuzes["wp_vorm"] = k3_warmtepomp.POMPINVOER[0], k3_warmtepomp.VORMEN[0]
            keuzes["mt_opwek"] = k3_warmtepomp.MT_OPWEK[0]
            b["pomp_kw_buurt"] = invoer.ALGEMEEN["pomp_w_woning"].standaard * b["woningen"] / 1000
            if wo == "MT":
                keuzes["mt_opwek"] = st.radio(f"Warmtebron MT-net 70 °C ({buurt})", k3_warmtepomp.MT_OPWEK,
                                              format_func=lambda o: {"buiten beschouwing": "warmteproductie buiten "
                                                                     "beschouwing laten"}.get(o, f"{o} + collectieve "
                                                                                                 "warmtepomp en WKO"),
                                              key=f"{bron}:mtopwek:{code}")
            if wo in ("ZLT", "MT"):  # alleen bij een warmtenet
                keuzes["pomp_invoer"] = st.radio("Pompvermogen warmtenet opgeven als", k3_warmtepomp.POMPINVOER,
                                                 horizontal=True, key=f"{bron}:pompinvoer")
                if keuzes["pomp_invoer"] == "totaal buurt":  # standaard: het pompvermogen per woning × woningen
                    b["pomp_kw_buurt"] = st.number_input(f"Totaal pompvermogen warmtenet {buurt} (kW, constant)", 0.0,
                                                         5000.0, float(b["pomp_kw_buurt"]), 5.0,
                                                         key=f"{bron}:pomp_kw_buurt:{code}")
            else:  # alleen bij warmtepompen in de woning
                keuzes["wp_vorm"] = st.radio("Verloop warmtepomp", k3_warmtepomp.VORMEN, horizontal=True,
                                             format_func=lambda v: {"vlak": "vlak (ondergrens)",
                                                                    "gemeten": "gemeten aggregaat"}[v],
                                             key=f"{bron}:wpvorm")
        elif kaart == 4:  # prognose: totaal aantal EV's in de buurt, één scenario voor alle buurten
            keuzes["ev_scenario"] = st.radio("Prognose elektrische auto's", EV_SCENARIOS, horizontal=True,
                                             index=EV_SCENARIOS.index(invoer.EV_SCENARIO), key=f"{bron}:ev_scenario")
            b["ev_aantal"] = float(b[f"ev_{keuzes['ev_scenario']}_{invoer.JAAR}"])
            b["ev_huidig"] = float(b[f"ev_{keuzes['ev_scenario']}_2025"])
        elif kaart == 8:
            keuzes["bat_modus"] = st.radio("Batterijmodus", k8_batterij.MODI, key=f"{bron}:batmodus")
            keuzes["bat_kwh"] = st.radio("Capaciteit per thuisbatterij", k8_batterij.GROOTTES, index=1, horizontal=True,
                                         format_func=lambda x: f"{x:.0f} kWh", key=f"{bron}:batkwh")

    def _relevant(naam: str) -> bool:
        """Invoer van de warmtepomptab alleen tonen als die bij de gekozen warmteoplossing hoort."""
        if naam == "t_net_zlt":
            return b["warmteoplossing"] == "ZLT"
        if naam == "mt_gas_pct":
            return b["warmteoplossing"] == "MT" and keuzes["mt_opwek"] in k3_warmtepomp.MT_COP
        if naam == "pomp_w_woning":
            return b["warmteoplossing"] in ("ZLT", "MT") and keuzes["pomp_invoer"] == "per woning"
        return True

    p = {naam: float(r["waarde"]) for naam, r in data.parameters.iterrows()}  # data en aannames, onderaan de tab
    met_keuzes = {v.kaart for v in invoer.PER_BUURT.values()} | {3, 4, 8}
    for kaart in VOLGORDE:
        velden = {n: v for n, v in invoer.ALGEMEEN.items() if v.kaart == kaart}
        if not velden and kaart not in met_keuzes:
            continue
        with st.expander(kaartnaam(kaart).replace(" ", " · ", 1), expanded=kaart == ACTIEF):
            _keuzes(kaart)
            for naam, v in velden.items():
                p[naam] = _veld(naam, v) if _relevant(naam) else float(v.standaard)  # niet van toepassing: standaard

    def _status(*namen: str) -> str:
        """Status van data en aannames; invoervelden zijn keuzes en tellen niet mee."""
        return data.status(*[n for n in namen if n not in invoer.NAMEN])

    wp_vorm, bat_modus = keuzes["wp_vorm"], keuzes["bat_modus"]
    p["bat_kwh"] = keuzes["bat_kwh"]

dag, prof = data.dag, data.profielen
tabs.VASTE_WAARDEN = data.parameters
r1 = k1_basis.bereken(b, p, dag, prof)

datum = pd.Timestamp(dag["datum"].iloc[0])
kop = f"#### Netbelasting · {b['buurt_naam']} · {['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'][datum.weekday()]} {datum:%d-%m-%Y}"
st.markdown(kop + ("  :gray-badge[mockdata]" if bron == "mock" else ""))

# Tabkeuze met rerun: de zijbalk opent de groep van de gekozen tab, en alleen die tab wordt opgebouwd
t = dict(zip(TABLABEL, st.tabs(list(TABLABEL.values()), key="tabkeuze", on_change="rerun")))
r3 = k3_warmtepomp.bereken(b, p, dag, prof, wp_vorm=wp_vorm, pomp_invoer=keuzes["pomp_invoer"], mt_opwek=keuzes["mt_opwek"])
varianten = {o: k3_warmtepomp.bereken(b, p, dag, prof, o, wp_vorm, keuzes["pomp_invoer"], keuzes["mt_opwek"])
             for o in WARMTEOPLOSSINGEN}
r4 = k4_laden_auto.bereken(b, p, prof)
r7 = k7_zon.bereken(b, p, dag)
r2 = k2_koken.bereken(b, p, prof)
r5 = k5_logistiek.bereken(b, p, prof)
r6 = k6_mkb.bereken(b, p, dag, data.bedrijfstakken)

if t[3].open:
    with t[3]:
        tabs.kaart3(r3, varianten, p, _status, b["isolatie_reductie"])
if t[4].open:
    with t[4]:
        tabs.kaart4(r4, p, _status, keuzes["ev_scenario"], invoer.JAAR)
if t[7].open:
    with t[7]:
        tabs.kaart7(r7, p, _status)
if t[1].open:
    with t[1]:
        tabs.kaart1(r1, p, dag, _status)
if t[2].open:
    with t[2]:
        tabs.kaart2(r2, _status)
if t[5].open:
    with t[5]:
        tabs.kaart5(r5, p, _status)
if t[6].open:
    with t[6]:
        tabs.kaart6(r6, p, _status)
r8 = k8_batterij.bereken(b, p, dag, r1.P_verbruik / r1.N, r7.per_kwp, bat_modus)

# Stapeling van alle tabs, in tabvolgorde
alle = {1: r1, 2: r2, 3: r3, 4: r4, 5: r5, 6: r6, 7: r7, 8: r8}
IN_STAPEL = {k: alle[k] for k in VOLGORDE if k in alle}
P_kaart = {kaartnaam(k): (r.P_tot if k == 6 else r.P) for k, r in IN_STAPEL.items()}
e_kaart = {kaartnaam(k): (float((r.sectoren["teken"] * r.sectoren["E"]).sum()) if k == 6 else
                          float(r.N * r.v.sum() / 4) if k == 8 else
                          r.e_dag if k == 1 else
                          sum(kl.N * kl.E for kl in r.klassen.values()) if k == 5 else
                          (-1 if k == 7 else 1) * r.N * r.E) for k, r in IN_STAPEL.items()}
rs = stapeling.bereken(P_kaart, e_kaart, sigma=r4.sigma)  # spreiding: alleen laden personenauto's
if t[8].open:
    with t[8]:
        tabs.kaart8(r8, p, _status)
if t[9].open:
    with t[9]:
        tabs.stapeling(rs, [kleur(k) for k in IN_STAPEL])
