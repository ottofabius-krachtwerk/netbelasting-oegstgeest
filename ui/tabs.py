"""Eén renderfunctie per kaart. Stappen staan onder elkaar, in rekenvolgorde, in gewone taal.

Symbolen (N, E, v, P) staan alleen klein tussen haakjes; de tekst moet zonder die symbolen te volgen zijn.
"""
import numpy as np
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij
from model import stapeling as stapeling_model
from model.common import nl
from model.data import WONINGTYPEN
from ui.charts import H_GROOT, KLEUR, MUTED, TIJD, balans, gestapeld, lijn, staven, waterval
from ui.kaarten import kleur, kn, meta
from ui.stappen import badge, kop, p_en_checks, stap

VERLOOP = "% van de dag per kwartier"
VASTE_WAARDEN = None  # parameters-tabel; gezet door app.py


def _piek_per_eenheid(E, v) -> float:
    """Vermogen per eenheid op het piekkwartier van deze kaart, in kW."""
    return 4 * E * float(np.max(np.abs(v)))


def _pct(v) -> np.ndarray:
    """Verloop over de dag als percentage van de dagenergie per kwartier."""
    return np.asarray(v) * 100


def _hoogste(v) -> str:
    v = np.asarray(v)
    i = int(np.argmax(np.abs(v)))
    return TIJD[i]


def _getal(x: float) -> str:
    return nl(x) if float(x).is_integer() else nl(x, 2 if abs(x) >= 1 else 3)


def _vast(kaart: int) -> None:
    """Data en aannames van deze tab: niet instelbaar, compact onderaan ter referentie."""
    if VASTE_WAARDEN is None:
        return
    df = VASTE_WAARDEN[(VASTE_WAARDEN["kaart"] == kaart) & (VASTE_WAARDEN["rol"] != "invoer")]
    if df.empty:
        return
    rijen = "".join(
        f"<tr><td>{r['label']}</td><td class='r'>{_getal(float(r['waarde']))}</td><td>{r['eenheid']}</td>"
        f"<td>{'data' if r['rol'] == 'data' else 'aanname'}{badge(r['status'])}"
        f"{' · ' + r['bron'] if isinstance(r['bron'], str) and r['bron'] else ''}</td></tr>"
        for _, r in df.iterrows())
    with st.expander(f"Vaste waarden en aannames ({len(df)})"):
        st.markdown(
            "<style>.vast{width:100%;border-collapse:collapse;font-size:.76rem;color:#52514e}"
            ".vast td{border-bottom:1px solid #e1e0d9;padding:3px 6px;vertical-align:top}"
            ".vast .r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}</style>"
            f"<table class='vast'>{rijen}</table>", unsafe_allow_html=True)


def _kop(kaart: int, extra: str = "") -> None:
    kop(*meta(kaart), extra=extra)


def _formule(zin: str, symbolen: str) -> None:
    """Rekenregel in gewone taal, met de formule klein erachter."""
    st.markdown(f"<div style='font-size:.9rem;color:#0b0b0b;margin:-.2rem 0 .6rem'>{zin}"
                f"<span style='font-size:.75rem;color:#898781;margin-left:.6rem'>{symbolen}</span></div>",
                unsafe_allow_html=True)


def kaart1(r: k1_basis.Resultaat, p, dag, tag) -> None:
    k = kleur(1)
    _kop(1)
    _formule("Profiel = verbruik van de woningen op deze dag − opwek van de huidige zonnepanelen op deze dag",
             "P[t] = 4 × N × E × v[t] + 4 × E_zon,jaar × f_zon × v_zon[t], Σ v = +1, Σ v_zon = −1")
    t = r.types
    # A · jaarverbruik
    stap(1, "Aantal woningen", nl(r.N), "woningen", tag=tag("buurten"),
         reken=[" + ".join(nl(n) for n in t["woningen"]) + f" = {nl(r.N)} woningen"],
         uitleg="Som van de woningen per woningtype in de buurt.",
         bron="CBS (woningen per woningtype per buurt)")
    stap(2, "Netto jaarverbruik", nl(r.e_netto / 1e3), "MWh/jaar",
         tag=tag("buurten", *[f"e_netto_{k}" for k in WONINGTYPEN.values()]),
         reken=[f"{w}: {nl(n)} woningen × {nl(e)} kWh = {nl(n * e / 1e3)} MWh"
                for w, n, e in zip(t["woningtype"], t["woningen"], t["e_netto_kwh_per_woning"])]
               + [f"totaal: {nl(r.e_netto / 1e3)} MWh"],
         uitleg="Per woningtype: aantal woningen × netto verbruik per woning (levering min teruglevering). Het netto "
                "verbruik bevat ook de huidige warmtepompen en het thuisladen van de huidige EV's. Tab "
                f"{kn(3)} rekent alleen de toename; tab {kn(4)} rekent alle EV's, daarom gaat hun thuisladen er in "
                "stap 4 af.",
         bron="Klimaatmonitor (netto levering per woningtype, PC6, 2025) × CBS (woningen per woningtype)",
         noot="nagaan of de Klimaatmonitor het netto verbruik per woning op 0 afkapt, zoals CBS 81528NED. Dan wordt "
              "het bruto verbruik in stap 4 te hoog bij woningen die meer opwekken dan ze verbruiken; te controleren "
              "met de opwek per woningtype uit Zonnedakje.")
    stap(3, "Bruto zonopwek huidige panelen per jaar", nl(r.e_zon_bruto / 1e3), "MWh/jaar", tag=tag("buurten"),
         uitleg="Alle opwek van de huidige panelen bij woningen, ook wat de woningen zelf gebruiken. Extra panelen "
                f"staan in tab {kn(7)}.",
         bron="Zonnedakje (jaaropwek per pand, alleen woningen)",
         noot="Zonnedakje geeft alle daken; hier tellen alleen woningen (BAG-gebruiksdoel woonfunctie, staat al in "
              "Zonnedakje). Gemengde panden: verdelen naar gebruiksoppervlakte per functie of toewijzen aan de "
              f"grootste functie (keuze open). Waar de opwek op de overige daken meetelt, is ook nog open "
              f"(bijvoorbeeld tab {kn(6)}). Zelfde jaar als het netto "
              "verbruik (2025) en de opwek van geplaatste panelen, niet het dakpotentieel.")
    thuis = 100 - p["publiek_aandeel"]
    stap(4, "Huishoudelijk jaarverbruik", nl(r.e_jaar_buurt / 1e3), "MWh/jaar",
         tag=tag("buurten", "ev_e_dag"),
         reken=[f"thuisladen huidige EV's: {nl(r.ev_huidig)} EV's × {nl(p['ev_e_dag'], 1)} kWh × 365 × {nl(thuis)} % "
                f"thuis = {nl(r.e_ev_thuis / 1e3)} MWh",
                f"{nl(r.e_netto / 1e3)} MWh netto + {nl(r.e_zon_bruto / 1e3)} MWh zon − {nl(r.e_ev_thuis / 1e3)} MWh "
                f"thuisladen = {nl(r.e_jaar_buurt / 1e3)} MWh",
                f"per woning: {nl(r.e_jaar_buurt / 1e3)} MWh ÷ {nl(r.N)} woningen = {nl(r.e_jaar)} kWh"],
         uitleg="In het netto verbruik is de zon over het hele jaar al afgetrokken. De volledige bruto opwek komt er "
                "weer bij; zo ontstaat het werkelijke verbruik. De opwek gaat er in stap 8 weer af, met het verloop "
                f"van deze winterdag. Het thuisladen van de huidige EV's (prognose 2025) gaat eraf, omdat tab {kn(4)} "
                "alle EV's rekent met hun eigen laadprofiel; aandeel thuis = 100 % min het aandeel publiek laden.",
         bron=f"stap 2 en 3 · huidige EV's: prognose 2025 in de buurttabel · laadenergie en aandeel publiek: tab {kn(4)}")
    # B · verbruik op deze dag
    stap(5, "Deel van het jaarverbruik op deze dag", nl(r.d * 100, 3), "%", tag=tag("nedu_e1a"),
         reken=[f"d = {nl(r.d * 100, 3)} % (som van NEDU E1A_AZI_A over 18-02-2025)",
                f"gemiddelde dag: 1 ÷ 365 = {nl(100 / 365, 3)} %",
                f"{nl(r.d * 100, 3)} % ÷ {nl(100 / 365, 3)} % = {nl(r.d * 365, 2)} × een gemiddelde dag"],
         uitleg="NEDU-profiel voor woningen zonder teruglevering, dus zonder zon in het verloop; dat past bij het "
                "bruto jaarverbruik. Aanname: de warmtepompen en EV's in de NEDU-steekproef (2021 tot 2023) zijn zo "
                "weinig dat deze fractie ook voor de buurt geldt.",
         bron="NEDU standaardprofielen elektriciteit 2025 (E1A_AZI_A, 18-02-2025)",
         noot="bij NEDU nagaan hoeveel woningen met warmtepomp of EV in de steekproef voor E1A_AZI_A zaten (2021 tot "
              "2023). Bij een groot aandeel is de fractie voor puur huishoudelijk verbruik lager.")
    stap(6, "Verbruik op deze dag", nl(r.N * r.E), "kWh", tag=tag("nedu_e1a"),
         fig=lijn({"verbruik": r.P_verbruik}, [MUTED], "kW", fmt=",.0f", vlak=True),
         reken=[f"{nl(r.e_jaar)} kWh × {nl(r.d * 100, 3)} % = {nl(r.E, 2)} kWh per woning",
                f"{nl(r.N)} woningen × {nl(r.E, 2)} kWh = {nl(r.N * r.E)} kWh",
                f"hoogste kwartier {_hoogste(r.v)}: {nl(r.v.max() * 100, 2)} % van de dag → "
                f"4 × {nl(r.N * r.E)} kWh × {nl(r.v.max() * 100, 2)} % = {nl(r.P_verbruik.max())} kW"],
         uitleg="Het verloop volgt hetzelfde NEDU-profiel (E1A_AZI_A) per kwartier.",
         bron="NEDU standaardprofielen elektriciteit 2025 (E1A_AZI_A, 18-02-2025)")
    # C · opwek op deze dag
    e_zon_dag = r.e_zon_bruto * r.f_zon
    i_ref = r.f_zon * p["i_jaar"]
    stap(7, "Deel van de jaaropwek op deze dag", nl(r.f_zon * 100, 3), "%", tag=tag("I", "i_jaar"),
         fig=lijn({"instraling": dag["I"].to_numpy(float)}, [kleur(7)], "W/m²", fmt=",.0f"),
         reken=[f"{nl(i_ref, 2)} kWh/m² ÷ {nl(p['i_jaar'])} kWh/m² = {nl(r.f_zon * 100, 3)} %",
                f"{nl(r.f_zon * 100, 3)} % ÷ {nl(100 / 365, 3)} % = {nl(r.f_zon * 365, 2)} × een gemiddelde dag"],
         uitleg="Instraling op deze dag ÷ instraling per jaar: de opwek volgt de gemeten zon van deze winterdag, niet "
                "het jaargemiddelde.",
         bron="KNMI station 215 (instraling 18-02-2025; instraling per jaar)")
    i_zon = int(np.argmin(r.P_zon))
    stap(8, "Opwek huidige panelen op deze dag", nl(e_zon_dag), "kWh", tag=tag("buurten", "I"),
         fig=lijn({"opwek": r.P_zon}, [kleur(7)], "kW", fmt=",.0f", vlak=True),
         reken=[f"{nl(r.e_zon_bruto / 1e3)} MWh × {nl(r.f_zon * 100, 3)} % = {nl(e_zon_dag)} kWh",
                *([f"meeste opwek {TIJD[i_zon]}: {nl(-r.P_zon[i_zon])} kW"] if r.P_zon[i_zon] < 0 else [])],
         uitleg="Het verloop volgt de instraling per kwartier; negatief omdat het opwek is. Zelfde rekenwijze als "
                f"tab {kn(7)}.",
         bron="Zonnedakje (jaaropwek) · KNMI station 215 (instraling 18-02-2025)")
    # D · netto profiel
    i_max, i_min = int(np.argmax(r.P)), int(np.argmin(r.P))
    reken = [f"{w} {TIJD[i]}: {nl(r.P_verbruik[i])} kW verbruik − {nl(-r.P_zon[i])} kW opwek = {nl(r.P[i])} kW"
             for w, i in (("hoogste", i_max), ("laagste", i_min))]
    reken.append(f"dag: {nl(r.N * r.E)} kWh verbruik − {nl(e_zon_dag)} kWh opwek = {nl(r.e_dag)} kWh")
    fig = balans(r.P_verbruik, r.P_zon, r.P, [MUTED, kleur(7), k], namen=("verbruik (stap 6)", "opwek (stap 8)", "netto"))
    p_en_checks(9, r.P, k, r.checks, naam="Netto profiel: verbruik − opwek", fig=fig, reken=reken)
    _vast(1)


def kaart3(r: k3_warmtepomp.Resultaat, varianten: dict, p, tag, p_isolatie: float) -> None:
    k = kleur(3)
    q_par = ("buurten", "gas_tapwater_koken_m3", "calorische_waarde", "ketelrendement")
    cop_par = {"geen": ("cop_ae",), "all-electric": ("cop_ae",), "ZLT": ("t_net_zlt", "cop_zlt_a", "cop_zlt_b"),
               "MT": (k3_warmtepomp.MT_COP[r.mt_opwek], "mt_gas_pct") if r.mt_opwek in k3_warmtepomp.MT_COP else ()
               }[r.oplossing]
    net = r.oplossing in ("ZLT", "MT")
    _kop(3)
    _formule("Profiel = aantal woningen × stroom per woning op deze dag × verloop over de dag; "
             "stroom = warmtevraag ÷ COP" + (" + pompenergie van het warmtenet" if net else ""),
             "P[t] = 4 × N × E × v[t], E = Q_ref ÷ COP" + (" + E_pomp" if net else ""))
    stap(1, "Extra woningen op de warmteoplossing", nl(r.N), "woningen", extra=[("warmteoplossing", r.oplossing)],
         tag=tag("buurten"),
         reken=["geen: 0 woningen"] if r.oplossing == "geen" else
               [f"{nl(r.woningen)} woningen × (100 % − {nl(r.wp_aandeel_huidig)} % met nu al een warmtepomp) = "
                f"{nl(r.N)} woningen"],
         uitleg="Alleen de toename: alle woningen in de buurt gaan over op de gekozen warmteoplossing, behalve de "
                f"woningen die nu al een warmtepomp hebben. Hun verbruik zit al in tab {kn(1)}. Bij 'geen' komen er "
                "geen woningen bij.",
         bron="CBS (woningen) · warmteoplossing en huidig aandeel warmtepompen: invoer zijbalk")
    stap(2, "Warmtevraag per woning per jaar, uit gas", nl(r.q_jaar_gas), "kWh warmte",
         waterval(["gas", "−tapwater en koken", "ruimteverwarming"], [r.gas, -r.gas_tapwater_koken, 0],
                  ["absolute", "relative", "total"], "m³"),
         extra=[("omrekening", f"× {nl(p['calorische_waarde'] * p['ketelrendement'], 2)} kWh warmte per m³ gas")],
         tag=tag(*q_par),
         uitleg="Gasverbruik per woning min een vast gemiddelde voor tapwater en koken, omgerekend naar nuttige warmte "
                "(calorische waarde × ketelrendement).",
         bron="Klimaatmonitor (gasverbruik per woning) · 100 m³ tapwater en koken: projectaanname")
    stap(3, "Warmtevraag per woning op deze dag", nl(r.q_ref, 1), "kWh warmte",
         tag=tag(*q_par, "t_ref", "t_stookgrens", "gd_jaar"),
         reken=[f"graaddagen: {nl(p['t_stookgrens'])} °C stookgrens − ({nl(p['t_ref'])} °C) = {nl(r.gd_ref, 1)}",
                f"{nl(r.q_jaar)} kWh × {nl(r.gd_ref, 1)} ÷ {nl(p['gd_jaar'])} graaddagen × (100 % − {nl(p_isolatie)} % "
                f"isolatie) = {nl(r.q_ref, 1)} kWh",
                f"{nl(r.q_ref, 1)} kWh ÷ ({nl(r.q_jaar)} kWh ÷ 365) = "
                + (f"{nl(r.q_ref * 365 / r.q_jaar, 2)} × een gemiddelde dag" if r.q_jaar else "–")],
         uitleg="Jaarlijkse warmtevraag × graaddagen van deze dag ÷ graaddagen per jaar, minus isolatie. We nemen een "
                f"constante buitentemperatuur van {nl(p['t_ref'])} °C aan voor deze dag.",
         bron="aanname (buitentemperatuur) · KNMI station 215 (graaddagen 2025) · isolatie: invoer zijbalk")
    if r.band:
        stap(4, "Verloop over de dag: bandbreedte", r.vorm_bron, "gebruikt (keuze in de zijbalk)",
             lijn({n: _pct(vv) for n, (vv, _) in r.band.items()}, [k, MUTED], VERLOOP, fmt=".2f"),
             extra=[(f"piek {n}", f"{nl(_piek_per_eenheid(r.E, vv), 2)} kW per woning "
                     + ("constant" if np.ptp(vv) == 0 else f"om {TIJD[int(np.argmax(vv))]}"))
                    for n, (vv, _) in r.band.items()],
             tag=tag("wp_aggregaat"),
             uitleg="Hoe de stroom over de dag valt, hangt af van buffering in woning en installatie. Vlak: maximale "
                    "buffering (laagste piek). Gemeten aggregaat: het opgetelde profiel van veel warmtepompen op een "
                    "koude winterdag, met een ochtendpiek na de nachtverlaging.",
         bron="gemeten aggregaatprofiel warmtepompen (mock; bron open) · vlak: aanname")
    else:
        stap(4, "Verloop over de dag: constant", None,
             lijn({"verloop": _pct(r.v)}, [k], VERLOOP, fmt=".2f"),
             extra=[("elk kwartier", f"{nl(r.v[0] * 100, 2)} % van de dag")],
             uitleg="Voor warmtenetten nemen we voorlopig een constant verloop aan. Mogelijke bron voor een profiel: "
                    "meetdata van warmtenetten of van de Installatiemonitor (RVO/BDH; nu alleen dagwaarden gepubliceerd).",
         bron="aanname (constant)")
    extra6 = []
    if not np.isnan(r.cop):
        naam6 = {"ZLT": "booster", "MT": f"collectieve warmtepomp ({r.mt_opwek})"}.get(r.oplossing, "warmtepomp")
        extra6.append((naam6, f"{nl(r.e_warmtepomp, 2)} kWh (COP {nl(r.cop, 2)})"))
    if net:
        extra6.append(("pompen warmtenet", f"{nl(r.e_pomp, 2)} kWh ({nl(p['pomp_w_woning'])} W × 24 uur)"
                       if r.pomp_invoer == "per woning" else
                       f"{nl(r.e_pomp, 2)} kWh (totaal {nl(r.e_pomp * r.N / 24)} kW voor de buurt, "
                       f"verdeeld over {nl(r.N)} woningen)"))
    extra6.append(("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per woning"))
    reken6 = None
    if r.oplossing == "MT" and r.mt_opwek in k3_warmtepomp.MT_COP:
        g, piek = r.gas_pct, r.piek_warmte_kw
        reken6 = [f"piekvraag warmte: {nl(r.N)} woningen × {nl(r.q_ref, 1)} kWh ÷ 24 uur = {nl(piek)} kW warmte",
                  f"piek- en backupvoorziening (gas): {nl(piek)} kW × {nl(g)} % = {nl(piek * g / 100)} kW warmte",
                  f"collectieve warmtepomp: {nl(piek)} kW × {nl(100 - g)} % = {nl(piek * (100 - g) / 100)} kW warmte "
                  f"÷ COP {nl(r.cop, 1)} = {nl(piek * (100 - g) / 100 / r.cop)} kW stroom",
                  f"per woning: {nl(r.q_ref, 1)} kWh × {nl(100 - g)} % ÷ COP {nl(r.cop, 1)} = {nl(r.e_warmtepomp, 2)} kWh"]
    stap(5, "Stroom per woning op deze dag", nl(r.E, 2), "kWh per woning", extra=extra6, reken=reken6,
         tag=tag(*cop_par, "pomp_w_woning", *q_par) if net else tag(*cop_par, *q_par),
         uitleg={"geen": "Warmtevraag op deze dag ÷ één COP voor de hele dag, als all-electric.",
                 "all-electric": "Warmtevraag op deze dag ÷ één COP voor de hele dag.",
                 "ZLT": f"De booster tilt het water van het warmtenet ({nl(p['t_net_zlt'])} °C) op: warmtevraag ÷ COP. "
                        "De COP hangt lineair af van de nettemperatuur (vaste term + per graad × temperatuur); later "
                        "beter: Carnot × rendement met de aanvoertemperatuur in de woning. Daarbij een vast "
                        "pompvermogen (per woning of als totaal voor de buurt), los van de warmtevraag.",
                 "MT": "Geen warmtepomp per woning. Warmteproductie buiten beschouwing: alleen een vast "
                       "pompvermogen (per woning of als totaal voor de buurt)." if r.mt_opwek not in k3_warmtepomp.MT_COP
                       else f"De basislast komt uit {r.mt_opwek}, op 70 °C gebracht met collectieve warmtepompen in "
                            "combinatie met WKO (één systeem-COP per bron). Een gasgestuurde piek- en backupvoorziening "
                            "vangt een instelbaar deel van de piekvraag op; de warmtepomp levert de rest. De warmtevraag "
                            "is op deze koude dag constant genomen (buffering in het net), dus het deel van de piek is "
                            "ook het deel van de energie. Daarbij een vast pompvermogen. Geen warmteverlies in het net "
                            "(voorlopig)." + (" Ondiepe geothermie is in de praktijk beperkt beschikbaar."
                                              if r.mt_opwek == "ondiepe geothermie" else "")}[r.oplossing],
         bron={"geen": "stap 3 · COP: bron open", "all-electric": "stap 3 · COP: bron open",
               "ZLT": "stap 3 · nettemperatuur: projectaanname 25 °C · COP-lijn en pompvermogen: bron open",
               "MT": "stap 3 · warmtebron en aandeel gas: invoer zijbalk · systeem-COP per bron en pompvermogen: "
                     "bron open"}[r.oplossing])
    stap(6, "Warmteoplossingen naast elkaar", None,
         fig=lijn({o: v.P for o, v in varianten.items()}, KLEUR[:len(varianten)], "kW", fmt=",.0f"),
         extra=[(o, f"{nl(v.P.max())} kW ({nl(_piek_per_eenheid(v.E, v.v), 2)} kW per woning)")
                for o, v in varianten.items()],
         tag=tag("t_ref", *q_par, "cop_ae", "cop_zlt_a", "cop_zlt_b", "cop_mt_teo", "cop_mt_tea", "cop_mt_geo", "pomp_w_woning",
                 "wp_aggregaat"),
         uitleg="Dezelfde buurt bij elke warmteoplossing; bij 'geen' komen er geen woningen bij (0 kW). MT met de "
                "gekozen opwek.",
         bron="stappen 1 tot en met 5, voor elke warmteoplossing")
    fig = None
    if r.band:
        fig = lijn({f"{n}{' (gebruikt)' if n == r.vorm_bron else ''}": P for n, (_, P) in r.band.items()},
                   [k if n == r.vorm_bron else MUTED for n in r.band], "kW", H_GROOT, fmt=",.0f")
    p_en_checks(7, r.P, k, r.checks, fig=fig)
    _vast(3)


def kaart4(r: k4_laden_auto.Resultaat, p, tag, scenario: str, jaar: int) -> None:
    k = kleur(4)
    _kop(4)
    _formule("Profiel = aantal elektrische auto's × laadenergie per auto op deze dag × laadverloop over de dag; het "
             "verloop mengt vier profielen: thuis of publiek, standaard of slim",
             "P[t] = 4 × N × E × v[t], v = Σ gewicht × v_profiel; P95[t] = P[t] + 1,645 × σ[t]")
    stap(1, "Elektrische auto's in de buurt", nl(r.N), "auto's", tag=tag("buurten"),
         reken=[f"prognose {scenario}, {jaar}: {nl(r.N)} EV's"],
         uitleg="Het totale aantal elektrische personenauto's in de buurt volgens de gekozen prognose (zijbalk: laag, "
                f"middel of hoog). Het thuisladen van de huidige EV's haalt tab {kn(1)} van het netto verbruik af, "
                "zodat het niet dubbel telt. Voorlopig rekenen we met 2025; een keuze voor 2035 en 2050 volgt.",
         bron="prognose per buurt in de buurttabel (scenario's laag, middel, hoog; nu mock)")
    e_tot = r.N * r.E
    stap(2, "Laadenergie op deze dag", nl(e_tot), "kWh", tag=tag("ev_e_dag"),
         reken=[f"{nl(r.N)} auto's × {nl(r.E, 1)} kWh = {nl(e_tot)} kWh",
                f"publiek: {nl(e_tot)} kWh × {nl(r.q * 100)} % = {nl(e_tot * r.q)} kWh",
                f"thuis: {nl(e_tot)} kWh × {nl(100 - r.q * 100)} % = {nl(e_tot * (1 - r.q))} kWh"],
         uitleg="Laadenergie per auto per werkdag, alleen laden in de buurt (thuis en bij publieke laadpunten). "
                "Verdeeld met het aandeel publiek laden (zijbalk).",
         bron="laadenergie: onderbouwing open (7 tot 9 kWh volgens de rekenkaart; een thuislaadpunt laadt volgens "
              "ElaadNL 7,0 kWh per werkdag) · aandeel publiek: invoer zijbalk")
    g = {n: w * 100 for n, w in r.gewichten.items()}
    q, at, ap = r.q * 100, r.a_thuis * 100, r.a_publiek * 100
    stap(3, "Laadverloop: vier profielen en het mengsel", _hoogste(r.v), "hoogste kwartier",
         lijn({**{n: _pct(vv) for n, vv in r.vormen.items()}, "mengsel": _pct(r.v)},
              [KLEUR[0], KLEUR[1], KLEUR[2], KLEUR[3], MUTED], VERLOOP, fmt=".2f"),
         reken=[f"thuis standaard: (100 % − {nl(q)} %) × (100 % − {nl(at)} %) = {nl(g['thuis standaard'])} %",
                f"thuis slim: (100 % − {nl(q)} %) × {nl(at)} % = {nl(g['thuis slim'])} %",
                f"publiek standaard: {nl(q)} % × (100 % − {nl(ap)} %) = {nl(g['publiek standaard'])} %",
                f"publiek slim: {nl(q)} % × {nl(ap)} % = {nl(g['publiek slim'])} %"],
         tag=tag(*k4_laden_auto.KOLOM.values()),
         uitleg="Het mengsel weegt de vier profielen met het aandeel publiek laden en het aandeel slim laden per "
                "locatie. Hoe we aan de profielen komen: ElaadNL heeft per laadpunt profielen gegenereerd voor 2025 (50 "
                "thuislaadpunten, 100 publieke laadpunten, standaard en slim). Per kwartier nemen we het gemiddelde "
                "over alle laadpunten en de 261 werkdagen van 2025 en schalen dat tot een vorm van 100 %. Slim "
                "thuisladen is een aanname: vlak tussen 01:00 en 06:00.",
         bron="ElaadNL gegenereerde laadpuntprofielen 2025 (indicatief) · slim thuis: aanname · aandelen: invoer zijbalk")
    pub = r.laadpunten["publiek standaard"] + r.laadpunten["publiek slim"]
    stap(4, "Publieke laadpunten in de buurt (ter info)", nl(pub), "laadpunten", tag=tag("ev_ongestuurd_publiek", "ev_slim_publiek"),
         reken=[f"standaard: {nl(e_tot * r.gewichten['publiek standaard'])} kWh ÷ "
                f"{nl(r.e_punt['publiek standaard'], 1)} kWh per laadpunt = {nl(r.laadpunten['publiek standaard'], 1)}",
                f"slim: {nl(e_tot * r.gewichten['publiek slim'])} kWh ÷ {nl(r.e_punt['publiek slim'], 1)} kWh per "
                f"laadpunt = {nl(r.laadpunten['publiek slim'], 1)}"],
         uitleg="Hoeveel publieke laadpunten de publieke laadenergie vraagt, als elk laadpunt laadt zoals een "
                "gemiddeld ElaadNL-laadpunt op een werkdag. Een publiek laadpunt bedient meerdere auto's; thuis is "
                "het één laadpunt per auto.",
         bron="ElaadNL gegenereerde laadpuntprofielen 2025 (energie per laadpunt per werkdag)")
    i, j = int(np.argmax(r.P)), int(np.argmax(r.P95))
    stap(5, "Gelijktijdigheid: 95 %-grens", nl(r.P95[j]), "kW", tag=tag(*[f"{c}_sd" for c in k4_laden_auto.KOLOM.values()]),
         fig=lijn({"verwacht": r.P, "95 %-grens": r.P95}, [k, k], "kW", fmt=",.0f", stippel=("95 %-grens",)),
         reken=[f"verwacht: {nl(r.P[i])} kW om {TIJD[i]}",
                f"95 %-grens: {nl(r.P[j])} kW + 1,645 × {nl(r.sigma[j])} kW = {nl(r.P95[j])} kW om {TIJD[j]}"],
         uitleg="Elk laadpunt laadt anders; met weinig auto's valt de piek daardoor vaker hoger uit dan het gemiddelde. "
                "Per profiel: aantal laadpunten (energie ÷ energie per laadpunt; thuis één per auto) × de spreiding per "
                "laadpunt uit de ElaadNL-data; de spreiding groeit met de wortel van het aantal. De vier profielen zijn "
                "onafhankelijk. 95 % kans dat een kwartier onder de grens blijft (normale benadering, eenzijdig). Slim "
                "thuis heeft geen spreiding (aanname).",
         bron="ElaadNL gegenereerde laadpuntprofielen 2025 (spreiding per laadpunt over laadpunten en werkdagen)")
    p_en_checks(6, r.P, k, r.checks,
                fig=lijn({"verwacht": r.P, "95 %-grens": r.P95}, [k, k], "kW", H_GROOT, fmt=",.1f", stippel=("95 %-grens",)))
    _vast(4)


def kaart7(r: k7_zon.Resultaat, p, tag) -> None:
    k = kleur(7)
    _kop(7)
    _formule("Profiel = resterende dakpotentie × benutting × deel van de jaaropwek op deze dag × verloop over de dag "
             "(negatief: opwek)",
             "P[t] = 4 × N × E × v[t], Σ v = −1")
    stap(1, "Extra jaaropwek zon in de buurt", nl(r.N / 1e3), "MWh/jaar", tag=tag("buurten"),
         reken=[f"{nl(r.potentie / 1e3)} MWh resterende potentie × {nl(r.benutting)} % = {nl(r.N / 1e3)} MWh"],
         uitleg="Alleen de toename: een deel van de resterende dakpotentie op alle daken in de buurt, woningen en "
                f"bedrijven (zijbalk, 0 tot 50 %). De huidige zon staat in tab {kn(1)} (woningen) en tab {kn(6)} "
                "(bedrijven).",
         bron="Zonnedakje (resterende dakpotentie, alle daken in de buurt) · benutting: invoer zijbalk")
    stap(2, "Deel van de jaaropwek op deze dag", nl(r.E * 100, 3), "%",
         lijn({"instraling": r.I}, [k], "W/m²", fmt=",.0f"), tag=tag("I", "i_jaar"),
         reken=[f"{nl(r.i_ref, 2)} kWh/m² ÷ {nl(p['i_jaar'])} kWh/m² = {nl(r.E * 100, 3)} %",
                f"{nl(r.E * 100, 3)} % ÷ {nl(100 / 365, 3)} % = {nl(r.E * 365, 2)} × een gemiddelde dag"],
         uitleg="Instraling op deze dag ÷ instraling per jaar (KNMI, horizontaal vlak).",
         bron="KNMI station 215 (instraling 18-02-2025; instraling per jaar)")
    i_zon = int(np.argmin(r.P))
    stap(3, "Extra opwek op deze dag", nl(r.N * r.E), "kWh", tag=tag("buurten", "I"),
         fig=lijn({"opwek": r.P}, [k], "kW", fmt=",.0f", vlak=True),
         reken=[f"{nl(r.N / 1e3)} MWh × {nl(r.E * 100, 3)} % = {nl(r.N * r.E)} kWh",
                *([f"meeste opwek {TIJD[i_zon]}: {nl(-r.P[i_zon])} kW"] if r.P[i_zon] < 0 else [])],
         uitleg="Het verloop volgt de gemeten instraling per kwartier; negatief omdat het opwek is.",
         bron="KNMI station 215 (instraling per uur, 18-02-2025)")
    p_en_checks(4, r.P, k, r.checks)
    _vast(7)


def _type_a(nr_kleur: int, r, zin: str, symbolen: str, n_titel: str, n_eenheid: str, n_uitleg: str, e_titel: str,
            e_eenheid: str, e_uitleg: str, v_uitleg: str, basis_label: str, basis_n: float, e_par: str, v_naam: str,
            n_tag, tag, bronnen: tuple[str, str, str]) -> None:
    """Eenvoudig profiel met dagwaarde: aantal, energie per stuk, verloop, profiel en checks."""
    k = kleur(nr_kleur)
    _formule(zin, symbolen)
    stap(1, n_titel, nl(r.N), n_eenheid, extra=[(basis_label.lower(), nl(basis_n))], tag=tag(*n_tag),
         uitleg=n_uitleg, bron=bronnen[0])
    stap(2, e_titel, nl(r.E, 2), e_eenheid, extra=[("× 365", f"{nl(r.E * 365)} kWh per jaar")],
         tag=tag(e_par), uitleg=e_uitleg, bron=bronnen[1])
    stap(3, "Verloop over de dag", _hoogste(r.v), "hoogste kwartier",
         lijn({"verloop": _pct(r.v)}, [k], VERLOOP, fmt=".2f"),
         extra=[("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per {n_eenheid.split()[0].rstrip('s')}")],
         tag=tag(v_naam), uitleg=v_uitleg, bron=bronnen[2])
    p_en_checks(4, r.P, k, r.checks)


def kaart2(r: k2_koken.Resultaat, tag) -> None:
    _kop(2)
    _type_a(2, r, "Profiel = extra elektrisch kokende huishoudens × kookenergie per huishouden × verloop over de dag",
            "P[t] = 4 × N × E × v[t]",
            "Extra huishoudens met elektrisch koken", "huishoudens",
            f"Huishoudens × extra aandeel elektrisch koken (% van alle huishoudens, bovenop nu). Huidig elektrisch "
            f"koken zit al in tab {kn(1)}.",
            "Kookenergie per huishouden op deze dag", "kWh per huishouden",
            "200 kWh per jaar voor elektrisch koken ÷ 365. Koken verschilt nauwelijks per seizoen, dus het "
            "jaargemiddelde geldt ook voor een winterwerkdag. Omgerekend uit het gasverbruik voor koken, met de hogere "
            "efficiëntie van elektrisch koken.",
            "Kookprofiel van een groep huishoudens op een winterwerkdag; de gelijktijdigheid zit in het verloop. Hoe we "
            "eraan komen: de RAMP-kookprofielen voor Nederland (gesimuleerd met Nederlandse maaltijdtijden), "
            "gemiddeld over de werkdagen van december tot en met februari, omgezet van UTC naar wintertijd. RAMP "
            "neemt Italiaans kookgedrag over met elke dag een warme lunch; die middagpiek hebben we verlaagd tot "
            "12,5 % van de dag (aanname).",
            "Huishoudens", r.huishoudens, "koken_e_dag", "koken", ("buurten", "koken_penetratie_groei"), tag,
            ("Klimaatmonitor (huishoudens per buurt) · extra aandeel: invoer zijbalk",
             "ECN-notitie ECN-N--14-024 (ECN voor RVO, 2014): 211 kWh per jaar · Milieu Centraal: inductie 175 kWh per "
             "jaar · afgerond 200 kWh per jaar",
             "RAMP-kookprofielen NL (Lombardi en Pickering, TU Delft/ETH, Zenodo 6579421, 2022) · middagpiek: aanname"))
    _vast(2)


def kaart5(r: k5_logistiek.Resultaat, p, tag) -> None:
    kl = r.klassen
    kleuren = KLEUR[:len(kl)]
    _kop(5, extra=badge("placeholder").replace("margin-left:6px", "margin-left:0") + " laadenergie en verloop zijn "
                                                                                       "nog open")
    _formule("Profiel = per voertuigtype: aantal elektrische voertuigen × laadenergie per voertuig × verloop over de dag",
             "P[t] = Σ 4 × N × E × v[t]")
    stap(1, "Extra elektrische voertuigen", nl(sum(k.N for k in kl.values())), "voertuigen", tag=tag("buurten"),
         extra=[(n, nl(k.N)) for n, k in kl.items()],
         uitleg="Alleen de toename: het aantal extra e-bestelbussen en e-trucks dat in de buurt laadt (zijbalk). Wat "
                f"nu al bij bedrijven laadt, zit in het verbruik van tab {kn(6)}.",
         bron="invoer zijbalk")
    stap(2, "Laadenergie per voertuig per dag", None, tag=tag("log_e_dag_bestel", "log_e_dag_truck"),
         reken=[f"{n}: {nl(k.N)} voertuigen × {nl(k.E)} kWh = {nl(k.N * k.E)} kWh" for n, k in kl.items()],
         uitleg="Aangenomen laadenergie per voertuigtype op een werkdag.",
         bron="aanname (bron open)")
    stap(3, "Laadprofiel: vlak", None,
         reken=[f"{n}: {nl(k.E)} kWh ÷ 24 uur = {nl(_piek_per_eenheid(k.E, k.v), 2)} kW per voertuig, elk kwartier"
                for n, k in kl.items()],
         uitleg="Voorlopig nemen we voor beide types een vlak laadprofiel aan: de laadenergie is gelijk verdeeld over de "
                "dag.",
         bron="aanname (vlak) · later: ElaadNL laadprofiel logistiek (te bevestigen)")
    p_en_checks(4, r.P, kleur(5), r.checks, naam="Profiel per voertuigtype",
                fig=gestapeld({n: k.P for n, k in kl.items()}, kleuren, totaal=r.P))
    _vast(5)


def kaart6(r: k6_mkb.Resultaat, p, tag) -> None:
    df = r.sectoren
    verbruik = df[df["teken"] > 0]
    zon = df[df["teken"] < 0].iloc[0]
    _kop(6)
    _formule("Profiel = per bedrijfstak: jaarverbruik in de buurt ÷ werkdagen, vlak over de dag; opwek van bedrijven "
             "negatief", "P[t] = Σ 4 × E_s × v_s[t], E_s = E_gemeente,s ÷ buurten ÷ werkdagen")
    stap(1, "Jaarverbruik per bedrijfstak in de buurt", nl(verbruik["e_jaar"].sum() / 1e3), "MWh/jaar",
         tag=tag("bedrijfstakken", "buurten_gemeente", "groei_niet_huish"),
         reken=[f"{r.sector}: {nl(r.e_gemeente / 1e3)} MWh ÷ {nl(p['buurten_gemeente'])} buurten = {nl(r.e_jaar / 1e3)} MWh"
                for r in verbruik.itertuples()],
         uitleg="Verbruik per bedrijfstak voor de hele gemeente, voorlopig gelijk verdeeld over de buurten (elke buurt "
                "evenveel). Groei is een invoer in MWh per jaar voor de gemeente en wordt op dezelfde manier verdeeld.",
         bron="Klimaatmonitor (elektriciteitsverbruik per bedrijfstak, gemeente) · CBS wijk- en buurtkaart 2025 "
              "(15 buurten) · groei: invoer zijbalk",
         noot="de gelijke verdeling over de buurten later verfijnen, bijvoorbeeld met het BAG-gebruiksoppervlak per "
              "gebruiksfunctie of grote verbruikers op hun eigen adres.")
    stap(2, "Verbruik op deze dag", nl(verbruik["E"].sum()), "kWh",
         tag=tag("bedrijfstakken", "werkdagen_jaar"),
         reken=[f"{nl(verbruik['e_jaar'].sum() / 1e3)} MWh ÷ {nl(p['werkdagen_jaar'])} werkdagen = "
                f"{nl(verbruik['E'].sum())} kWh",
                f"vlak over de dag: {nl(verbruik['E'].sum())} kWh ÷ 24 uur = {nl(verbruik['E'].sum() / 24)} kW"],
         uitleg="Elke werkdag hetzelfde verbruik en in het weekend niets; deze dinsdag krijgt dus een werkdagdeel. Over "
                "de dag nemen we een vlak verbruik aan.",
         bron="aanname (vlak, alleen werkdagen) · kalender 2025")
    stap(3, "Opwek zon van bedrijven op deze dag", nl(zon["E"]), "kWh", tag=tag("buurten", "I", "i_jaar"),
         fig=lijn({"opwek": r.P[zon["sector"]]}, [kleur(7)], "kW", fmt=",.0f", vlak=True),
         reken=[f"{nl(zon['e_jaar'] / 1e3)} MWh × {nl(zon['d'] * 100, 3)} % = {nl(zon['E'])} kWh"],
         uitleg=f"Jaaropwek op de overige daken × deel van de jaaropwek op deze dag, met het verloop van de instraling, "
                f"net als in tab {kn(1)} en {kn(7)}.",
         bron="Zonnedakje (alle daken min woningen) · KNMI station 215 (instraling)",
         noot=f"opwek van bedrijven = Zonnedakje voor alle overige panden: alle daken min de woningen uit tab {kn(1)} "
              "(nu nog mock), zodat alle zonne-energie in de buurt één keer meetelt. Controle toevoegen: opwek woningen "
              "+ overige panden = totaal Zonnedakje voor de buurt.")
    P_verbruik = np.sum([r.P[s] for s in verbruik["sector"]], axis=0)
    fig = balans(P_verbruik, r.P[zon["sector"]], r.P_tot, [MUTED, kleur(7), kleur(6)],
                 namen=("verbruik (stap 2)", "opwek (stap 3)", "netto"))
    p_en_checks(4, r.P_tot, kleur(6), r.checks, naam="Netto profiel: verbruik − opwek", fig=fig)
    _vast(6)


def stapeling(r: stapeling_model.Resultaat, kleuren: list[str]) -> None:
    i = r.i_piek
    _kop(9)
    _formule("Profiel van de buurt = de profielen van alle tabs opgeteld",
             "P_buurt[t] = Σ P[t]")
    j = r.i_piek95
    stap(1, "Piek van de buurt", nl(r.P_tot[i]), "kW", extra=[("om", TIJD[i]), ("laagste", f"{nl(r.P_tot.min())} kW")],
         reken=[f"verwacht: {nl(r.P_tot[i])} kW om {TIJD[i]}",
                f"95 %-grens: {nl(r.P95[j])} kW om {TIJD[j]} (+{nl(r.P95[j] - r.P_tot[j])} kW door de spreiding van "
                f"laden personenauto's)"],
         uitleg="Hoogste kwartier van het opgetelde profiel. De 95 %-grens telt de spreiding van het laden van "
                f"personenauto's op (tab {kn(4)}); de andere tabs hebben nog geen spreiding.",
         bron="de profielen van de tabs")
    stap(2, f"Bijdrage per tab op het piekkwartier ({TIJD[i]})", None,
         fig=staven(r.tabel["kaart"], r.tabel["op_piek"], kleuren=kleuren, eenheid="kW"),
         uitleg="Welke tabs de piek bepalen.",
         bron="de profielen van de tabs")
    stap(3, "Eigen piek per tab en tijdstip", None,
         fig=staven([f"{k} · {TIJD[j]}" for k, j in zip(r.tabel["kaart"], r.tabel["i_extreem"])],
                    r.tabel["extreem"], kleuren=kleuren, eenheid="kW"),
         uitleg="Hoogste kwartier van elke tab apart; bij zon de grootste opwek. Vallen die samen, dan stapelt de "
                "piek.",
         bron="de profielen van de tabs")
    p_en_checks(4, r.P_tot, KLEUR[0], r.checks, naam="Profiel van de buurt",
                fig=gestapeld(r.P, kleuren, totaal=r.P_tot, grens=("95 %-grens", r.P95)))


def kaart8(r: k8_batterij.Resultaat, p, tag) -> None:
    k = kleur(8)
    _kop(8)
    _formule("Profiel = totale batterijcapaciteit × laad- en ontlaadvermogen per kWh batterij; positief is laden",
             "P[t] = N × v[t], v in kW per kWh")
    stap(1, "Totale batterijcapaciteit in de buurt", nl(r.N), "kWh",
         tag=tag("buurten", "bat_adoptie"),
         reken=[f"{nl(r.woningen)} woningen × {nl(p['bat_adoptie'])} % = {nl(r.batterijen)} batterijen",
                f"{nl(r.batterijen)} batterijen × {nl(p['bat_kwh'])} kWh = {nl(r.N)} kWh"],
         uitleg="Woningen × aandeel woningen met een batterij × capaciteit per batterij. De capaciteit is een keuze "
                "uit 5, 10 of 15 kWh, het gangbare bereik voor thuisbatterijen.",
         bron="CBS (woningen) · aandeel en capaciteit: invoer zijbalk · bereik 5 tot 15 kWh: marktaanbod en "
              "consumentensites (Selectra, Werkspot), geen onafhankelijke bron")
    stap(2, "Geen eigen verbruik", None,
         uitleg="Een batterij verschuift energie in de tijd en verbruikt netto alleen zijn verliezen. Daarom is er "
                "geen verbruik per stuk zoals op de andere tabs.")
    overschot = float(np.clip(r.pv - r.last, 0, None).sum() / 4)
    stap(3, "Verbruik en zon van een woning met batterij", nl(overschot, 2), "kWh zonoverschot op deze dag",
         lijn({f"verbruik (tab {kn(1)})": r.last, f"zon (tab {kn(7)})": r.pv}, [KLEUR[0], KLEUR[3]], "kW", fmt=".2f"),
         extra=[("zonnepanelen per batterijwoning", f"{nl(p['bat_kwp_woning'], 1)} kWp"),
                ("jaaropbrengst", f"{nl(p['zon_opbrengst'])} kWh per kWp")],
         tag=tag("nedu_e1a", "I", "bat_kwp_woning", "zon_opbrengst"),
         uitleg=f"Gemiddelde woning uit tab {kn(1)} met de zon van één batterijwoning (kWp × jaaropbrengst per kWp, verloop als tab {kn(7)}). Alleen het "
                "overschot kan de batterij met zelfconsumptie laden.",
         bron=f"tab {kn(1)} (verbruik per woning) · tab {kn(7)} (verloop zon) · zonnepanelen per batterijwoning: invoer zijbalk")
    goedkoop, duur = r.prijs[r.goedkoop].mean(), r.prijs[r.duur].mean()
    stap(4, "Day-ahead prijs: aansturing van de batterij", f"{int(r.goedkoop.sum())}",
         "goedkoopste en duurste kwartieren",
         lijn({"prijs": r.prijs}, [KLEUR[1]], "€/MWh", fmt=",.0f"), tag=tag("prijs"),
         reken=[f"laden: {', '.join(TIJD[i] for i in np.flatnonzero(r.goedkoop))} (gemiddeld {nl(goedkoop)} €/MWh)",
                f"ontladen: {', '.join(TIJD[i] for i in np.flatnonzero(r.duur))} (gemiddeld {nl(duur)} €/MWh)",
                f"verschil {nl(duur - goedkoop)} €/MWh; het rendementsverlies kost {nl(goedkoop * (1 / p['bat_eta'] - 1))} €/MWh"],
         uitleg="Alleen voor zelfconsumptie + day-ahead: laden uit het net in de goedkoopste kwartieren en op vol "
                "vermogen ontladen in de duurste; zoveel kwartieren als nodig om vol of leeg te gaan. De prijs is het "
                "gemiddelde per kwartier van de 5 koudste werkdagen van winter 2025/26 (5, 6, 7 en 29 januari en 3 "
                "februari 2026), omdat de echte prijs van 18-02-2025 niet bij een koude ontwerpdag past.",
         bron="EPEX day-ahead NL per kwartier (Energy Quantified), gemiddelde van de 5 koudste werkdagen winter "
              "2025/26 (bevolkingsgewogen temperatuur)")
    stap(5, "Laden en ontladen per kWh batterij", r.modus, "gebruikt (keuze in de zijbalk)",
         lijn({m: md.v for m, md in r.modi.items()}, [KLEUR[0], KLEUR[1]], "kW per kWh", fmt=".3f"),
         extra=[(m, f"verlies {nl(md.v.sum() / 4, 3)} kWh per kWh batterij") for m, md in r.modi.items()],
         tag=tag("bat_c", "bat_eta", "prijs"),
         uitleg="Zelfconsumptie: zonoverschot laden, eigen tekort dekken uit zonnestroom. Plus day-ahead: daarnaast "
                "laden uit het net in de goedkoopste kwartieren en in de duurste kwartieren op vol vermogen ontladen (eigen "
                "tekort dekken, de rest terugleveren). Ingekochte stroom blijft staan tot de duurste kwartieren, zodat "
                "zonnestroom voor eigen gebruik blijft. Positief is laden; de batterij eindigt de dag zo vol als hij "
                "begon (v).",
         bron="stap 3 en 4 · vermogen en rendement: invoer zijbalk")
    stap(6, "Laadtoestand", None,
         fig=lijn({**{m: md.soc * 100 for m, md in r.modi.items()},
                   f"{k8_batterij.MODI[1]}: waarvan ingekocht": r.modi[k8_batterij.MODI[1]].soc_net * 100},
                  [KLEUR[0], KLEUR[1], MUTED], "% vol", fmt=".0f"),
         tag=tag("bat_c", "bat_eta", "prijs"),
         uitleg="Hoe vol de batterij is over de dag; de grijze lijn is het deel dat uit het net is ingekocht.",
         bron="stap 5")
    p_en_checks(7, r.P, k, r.checks)
    _vast(8)
