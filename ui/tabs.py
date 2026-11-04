"""Eén renderfunctie per kaart. Stappen staan onder elkaar, in rekenvolgorde, in gewone taal.

Symbolen (N, E, v, P) staan alleen klein tussen haakjes; de tekst moet zonder die symbolen te volgen zijn.
"""
import numpy as np
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij
from model import stapeling as stapeling_model
from model.common import nl
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
    stap(1, "Aantal woningen", nl(r.N), "woningen", tag=tag("woningtypen"),
         reken=[" + ".join(nl(n) for n in t["woningen"]) + f" = {nl(r.N)} woningen"],
         uitleg="Som van de woningen per woningtype in de buurt.",
         bron="CBS (woningen per woningtype per buurt)")
    stap(2, "Netto jaarverbruik", nl(r.e_netto / 1e3), "MWh/jaar", tag=tag("woningtypen"),
         reken=[f"{w}: {nl(n)} woningen × {nl(e)} kWh = {nl(n * e / 1e3)} MWh"
                for w, n, e in zip(t["woningtype"], t["woningen"], t["e_netto_kwh_per_woning"])]
               + [f"totaal: {nl(r.e_netto / 1e3)} MWh"],
         uitleg="Per woningtype: aantal woningen × netto verbruik per woning (levering min teruglevering). Het netto "
                "verbruik bevat ook de huidige warmtepompen en het thuisladen van de huidige EV's; de tabs "
                f"{kn(4)} en {kn(3)} rekenen alleen de toename.",
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
              f"grootste functie (keuze open). De overige daken gaan naar tab {kn(6)}. Zelfde jaar als het netto "
              "verbruik (2025) en de opwek van geplaatste panelen, niet het dakpotentieel.")
    stap(4, "Bruto jaarverbruik", nl(r.e_jaar_buurt / 1e3), "MWh/jaar",
         tag=tag("woningtypen", "buurten"),
         reken=[f"{nl(r.e_netto / 1e3)} MWh netto + {nl(r.e_zon_bruto / 1e3)} MWh zon = {nl(r.e_jaar_buurt / 1e3)} MWh",
                f"per woning: {nl(r.e_jaar_buurt / 1e3)} MWh ÷ {nl(r.N)} woningen = {nl(r.e_jaar)} kWh"],
         uitleg="In het netto verbruik is de zon over het hele jaar al afgetrokken. De volledige bruto opwek komt er "
                "weer bij; zo ontstaat het werkelijke verbruik. De opwek gaat er in stap 8 weer af, met het verloop "
                "van deze winterdag.",
         bron="stap 2 en 3")
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
               "MT": ("cop_mt_wp",) if r.mt_opwek == "grote warmtepomp" else ()}[r.oplossing]
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
        naam6 = {"ZLT": "booster", "MT": f"centrale opwek ({r.mt_opwek})"}.get(r.oplossing, "warmtepomp")
        extra6.append((naam6, f"{nl(r.e_warmtepomp, 2)} kWh (COP {nl(r.cop, 2)})"))
    if net:
        extra6.append(("pompen warmtenet", f"{nl(r.e_pomp, 2)} kWh ({nl(p['pomp_w_woning'])} W × 24 uur)"
                       if r.pomp_invoer == "per woning" else
                       f"{nl(r.e_pomp, 2)} kWh (totaal {nl(r.e_pomp * r.N / 24)} kW voor de buurt, "
                       f"verdeeld over {nl(r.N)} woningen)"))
    extra6.append(("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per woning"))
    stap(5, "Stroom per woning op deze dag", nl(r.E, 2), "kWh per woning", extra=extra6,
         tag=tag(*cop_par, "pomp_w_woning", *q_par) if net else tag(*cop_par, *q_par),
         uitleg={"geen": "Warmtevraag op deze dag ÷ één COP voor de hele dag, als all-electric.",
                 "all-electric": "Warmtevraag op deze dag ÷ één COP voor de hele dag.",
                 "ZLT": f"De booster tilt het water van het warmtenet ({nl(p['t_net_zlt'])} °C) op: warmtevraag ÷ COP. "
                        "De COP hangt lineair af van de nettemperatuur (vaste term + per graad × temperatuur); later "
                        "beter: Carnot × rendement met de aanvoertemperatuur in de woning. Daarbij een vast "
                        "pompvermogen (per woning of als totaal voor de buurt), los van de warmtevraag.",
                 "MT": {"restwarmte": "Geen warmtepomp per woning en de warmte komt van buiten de buurt (restwarmte): "
                                      "alleen een vast pompvermogen (per woning of als totaal voor de buurt).",
                        "grote warmtepomp": "De warmte wordt in de buurt gemaakt met een grote warmtepomp: warmtevraag "
                                            "÷ COP van de centrale warmtepomp, constant over de dag. Daarbij een vast "
                                            "pompvermogen. Geen warmteverlies in het net (voorlopig).",
                        "e-boiler": "De warmte wordt in de buurt gemaakt met een e-boiler: warmtevraag ÷ 1, constant "
                                    "over de dag. Daarbij een vast pompvermogen. Geen warmteverlies in het net "
                                    "(voorlopig)."}[r.mt_opwek]}[r.oplossing],
         bron={"geen": "stap 3 · COP: bron open", "all-electric": "stap 3 · COP: bron open",
               "ZLT": "stap 3 · nettemperatuur: projectaanname 25 °C · COP-lijn en pompvermogen: bron open",
               "MT": "stap 3 · opwek: invoer zijbalk · COP centrale warmtepomp en pompvermogen: bron open"}[r.oplossing])
    stap(6, "Warmteoplossingen naast elkaar", None,
         fig=lijn({o: v.P for o, v in varianten.items()}, KLEUR[:len(varianten)], "kW", fmt=",.0f"),
         extra=[(o, f"{nl(v.P.max())} kW ({nl(_piek_per_eenheid(v.E, v.v), 2)} kW per woning)")
                for o, v in varianten.items()],
         tag=tag("t_ref", *q_par, "cop_ae", "cop_zlt_a", "cop_zlt_b", "cop_mt_wp", "pomp_w_woning", "wp_aggregaat"),
         uitleg="Dezelfde buurt bij elke warmteoplossing; bij 'geen' komen er geen woningen bij (0 kW). MT met de "
                "gekozen opwek.",
         bron="stappen 1 tot en met 5, voor elke warmteoplossing")
    fig = None
    if r.band:
        fig = lijn({f"{n}{' (gebruikt)' if n == r.vorm_bron else ''}": P for n, (_, P) in r.band.items()},
                   [k if n == r.vorm_bron else MUTED for n in r.band], "kW", H_GROOT, fmt=",.0f")
    p_en_checks(7, r.P, k, r.checks, fig=fig)
    _vast(3)


def kaart4(r: k4_laden_auto.Resultaat, p, tag) -> None:
    k = kleur(4)
    _kop(4)
    _formule("Profiel = aantal elektrische auto's × laadenergie per auto op deze dag × laadverloop over de dag",
             "P[t] = 4 × N × E × v[t], v = (1 − a) × v_ongestuurd + a × v_slim")
    stap(1, "Extra elektrische auto's", nl(r.N), "auto's", tag=tag("buurten"),
         uitleg="Alleen de toename: het aantal extra EV's in de buurt (zijbalk). Het laden van de huidige EV's zit al "
                f"in tab {kn(1)}.",
         bron="invoer zijbalk")
    stap(2, "Laadenergie per auto op deze dag", nl(r.E, 1), "kWh per auto",
         extra=[("× 365", f"{nl(r.E * 365)} kWh per jaar")],
         tag=tag("ev_e_dag"),
         uitleg="Dagwaarde op een winterwerkdag, thuis en openbaar samen.",
         bron="onderbouwing open (7 tot 9 kWh volgens de rekenkaart)")
    stap(3, "Laadverloop: ongestuurd, slim en gemengd", f"{nl(r.a * 100)} %", "slim laden",
         lijn({"ongestuurd": _pct(r.v_ongestuurd), "slim": _pct(r.v_slim), "gemengd": _pct(r.v)},
              [KLEUR[0], KLEUR[1], KLEUR[2]], VERLOOP, fmt=".2f"),
         extra=[("piek ongestuurd", f"{nl(_piek_per_eenheid(r.E, r.v_ongestuurd), 2)} kW per auto"),
                ("gemengd", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per auto")],
         tag=tag("ev_ongestuurd", "ev_slim", "slim_aandeel"),
         uitleg="Het gemengde verloop weegt ongestuurd en slim laden met het aandeel slim laden (% van alle EV's, "
                "extra). Aantal en laadenergie veranderen niet. Verlopen: mock tot de ElaadNL-dataset "
                "gekozen is.",
         bron="ElaadNL gemeten aggregaat (dataset open) · aandeel slim laden: invoer zijbalk")
    p_en_checks(4, r.P, k, r.checks)
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
            "Kookenergie per huishouden op deze dag", "kWh per huishouden", "Dagwaarde op een winterwerkdag.",
            "Kookprofiel van een groep huishoudens; de gelijktijdigheid zit in het verloop.",
            "Huishoudens", r.huishoudens, "koken_e_dag", "koken", ("buurten", "koken_penetratie_groei"), tag,
            ("Klimaatmonitor (huishoudens per buurt) · extra aandeel: invoer zijbalk",
             "bron open: Liander/BAT, monitoring aardgasvrije wijken, TNO of Milieu Centraal; bij voorkeur dezelfde "
             "bron als het verloop",
             "kookprofiel: bron open (Liander/BAT, monitoring aardgasvrije wijken, TNO of Milieu Centraal; terugval UK "
             "Household Electricity Survey)"))
    _vast(2)


def kaart5(r: k5_logistiek.Resultaat, p, tag) -> None:
    kl = r.klassen
    kleuren = KLEUR[:len(kl)]
    par = ("buurten", "log_elektrificatie", "log_groei")
    _kop(5, extra=badge("placeholder").replace("margin-left:6px", "margin-left:0") + " aantallen, energie en "
                                                                                       "verloop zijn allemaal open")
    _formule("Profiel = per voertuigtype: aantal elektrische voertuigen × laadenergie per voertuig × verloop over de dag",
             "P[t] = Σ 4 × N × E × v[t]")
    stap(1, "Aantal elektrische voertuigen", nl(sum(k.N for k in kl.values()), 1), "voertuigen",
         extra=[(n, f"{nl(k.N, 1)} = {nl(k.voertuigen)} × {nl(p['log_elektrificatie'])} % × "
                    f"(1 + {nl(p['log_groei'])} %)") for n, k in kl.items()], tag=tag(*par),
         uitleg="Bestelauto's en trucks in de buurt × elektrificatiegraad (% elektrisch) × (1 + groei t.o.v. nu).",
         bron="CBS 85239NED (bestelauto's Zuid-Holland, via bedrijfsvestigingen naar de buurt) · trucks: bron open · elektrificatie en groei: invoer zijbalk")
    stap(2, "Laadenergie per voertuig per dag", None,
         extra=[(n, f"{nl(k.E)} kWh") for n, k in kl.items()], tag=tag("log_e_dag_bestel", "log_e_dag_truck"),
         uitleg="Dagwaarde per voertuigtype.",
         bron="bron open")
    stap(3, "Verloop over de dag per type", None,
         lijn({n: _pct(k.v) for n, k in kl.items()}, kleuren, VERLOOP, fmt=".2f"),
         extra=[(n, f"{nl(_piek_per_eenheid(k.E, k.v), 2)} kW per voertuig om {TIJD[int(np.argmax(k.v))]}")
                for n, k in kl.items()], tag=tag("logistiek_bestel", "logistiek_truck"),
         uitleg="Laadprofiel per voertuigtype (laden op het depot).",
         bron="ElaadNL laadprofiel logistiek (te bevestigen)")
    p_en_checks(4, r.P, kleur(5), r.checks, naam="Profiel per voertuigtype",
                fig=gestapeld({n: k.P for n, k in kl.items()}, kleuren, totaal=r.P))
    _vast(5)


def kaart6(r: k6_mkb.Resultaat, opties: dict, tag) -> None:
    df = r.sectoren
    kleuren = KLEUR[:len(df)]
    _kop(6)
    _formule("Profiel = per sector: verbruik op deze dag × verloop over de dag; opwek van bedrijven negatief",
             "P[t] = Σ 4 × E_s × v_s[t], E_s = E_jaar,s × d_s")
    stap(1, "Jaarverbruik per sector", nl((df["teken"] * df["e_jaar"]).sum() / 1e3), "MWh/jaar netto",
         staven(df["sector"], df["teken"] * df["e_jaar"] / 1e3, kleuren=kleuren, eenheid="MWh/jaar"),
         tag=tag("sectoren", "groei_niet_huish"),
         uitleg="Gemeentetotaal per sector verdeeld naar de buurt, × (1 + groei t.o.v. het huidige jaarverbruik). "
                "Opwek van bedrijven negatief.",
         bron="Klimaatmonitor (verbruik per sector, gemeente) · BAG gebruiksoppervlak (verdeling naar buurt) · groei: "
              "invoer zijbalk · opwek: Zonnedakje (alle daken min woningen)",
         noot=f"opwek van bedrijven = Zonnedakje voor alle overige panden: alle daken min de woningen uit tab {kn(1)} "
              "(nu nog mock), zodat alle zonne-energie in de buurt één keer meetelt. Controle toevoegen: opwek woningen "
              "+ overige panden = totaal Zonnedakje voor de buurt.")
    stap(2, "Verbruik op deze dag per sector", nl(float(df["E"].abs().sum())), "kWh (verbruik en opwek opgeteld)",
         staven(df["sector"], df["d"] * 365, kleuren=kleuren, eenheid="× een gemiddelde dag", fmt=".2f"),
         tag=tag(*r.v.keys(), "i_jaar"),
         uitleg="Het sectorprofiel zegt welk deel van het jaar op deze dag valt; de grafiek toont dat ten opzichte "
                f"van een gemiddelde dag. Opwek: uit de instraling, net als tab {kn(7)}.",
         bron=f"sectorprofielen ({r.profielbron}) · opwek: KNMI station 215 (instraling)")
    vorm_tag = tag("nedu_e3") if r.profielbron == "NEDU E3" else tag(*r.v.keys())
    stap(3, f"Verloop over de dag per sector ({r.profielbron})", None,
         fig=lijn({s: _pct(v) for s, v in r.v.items()}, kleuren, VERLOOP, fmt=".2f"), tag=vorm_tag,
         uitleg={"Liander": "Liander open data: elke sector een eigen verloop. Opwek is negatief.",
                 "NEDU E3": "NEDU E3: één verloop voor alle verbruikssectoren (E3A t/m E3D zijn gelijk, bevroren "
                            "meetdata 2011 tot 2013). Opwek houdt het zonverloop."}[r.profielbron],
         bron={"Liander": "Liander open data (sectorprofielen)", "NEDU E3": "NEDU standaardprofielen elektriciteit 2025 (E3, 18-02-2025)"}[r.profielbron])
    stap(4, "Twee opties voor de sectorprofielen", None,
         fig=lijn({n: v.P_tot for n, v in opties.items()}, [KLEUR[0], KLEUR[1]], "kW", fmt=",.0f"),
         extra=[(n, f"max {nl(v.P_tot.max())} kW om {TIJD[int(np.argmax(v.P_tot))]}") for n, v in opties.items()],
         tag=tag(*r.v.keys(), "nedu_e3"),
         uitleg="Zelfde jaarverbruik per sector, ander verloop. Keuze in de zijbalk.",
         bron="Liander open data en NEDU standaardprofielen elektriciteit 2025 (E3)")
    p_en_checks(5, r.P_tot, kleur(6), r.checks, naam="Profiel per sector", fig=gestapeld(r.P, kleuren, totaal=r.P_tot))
    _vast(6)


def stapeling(r: stapeling_model.Resultaat, kleuren: list[str]) -> None:
    i = r.i_piek
    _kop(9)
    _formule(f"Profiel van de buurt = de profielen van alle tabs opgeteld (zonder tab {kn(5)})",
             "P_buurt[t] = Σ P[t]")
    stap(1, "Piek van de buurt", nl(r.P_tot[i]), "kW", extra=[("om", TIJD[i]), ("laagste", f"{nl(r.P_tot.min())} kW")],
         uitleg="Hoogste kwartier van het opgetelde profiel.",
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
    p_en_checks(4, r.P_tot, KLEUR[0], r.checks, naam="Profiel van de buurt", fig=gestapeld(r.P, kleuren, totaal=r.P_tot))


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
    stap(4, "Day-ahead prijs", f"{int(r.goedkoop.sum())}", "goedkoopste en duurste kwartieren",
         lijn({"prijs": r.prijs}, [KLEUR[1]], "€/MWh", fmt=",.0f"), tag=tag("prijs"),
         extra=[("laden rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.goedkoop)[:3]) + " …"),
                ("ontladen rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.duur)[:3]) + " …")],
         uitleg="Alleen voor zelfconsumptie + day-ahead: laden uit het net in de goedkoopste kwartieren en op vol "
                "vermogen ontladen in de duurste; zoveel kwartieren als nodig om vol of leeg te gaan.",
         bron="day-ahead prijs Nederland, 18-02-2025 (bron nog te kiezen)")
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
