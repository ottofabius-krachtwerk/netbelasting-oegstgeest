"""Eén renderfunctie per kaart. Stappen staan onder elkaar, in rekenvolgorde."""
import numpy as np
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij
from model import stapeling as stapeling_model
from model.common import nl
from ui.charts import H_GROOT, KLEUR, MUTED, TIJD, gestapeld, lijn, staven, waterval
from ui.kaarten import kleur, kn, meta
from ui.stappen import badge, kop, p_en_checks, stap


def _piek_per_eenheid(E, v) -> float:
    """Vermogen per eenheid op het piekkwartier van deze kaart, in kW."""
    return 4 * E * float(np.max(np.abs(v)))


def _kop(kaart: int, extra: str = "") -> None:
    kop(*meta(kaart), extra=extra)


def _formule(tekst: str) -> None:
    st.markdown(f"<div style='font-size:.9rem;color:#52514e;margin:-.2rem 0 .6rem'>{tekst}</div>",
                unsafe_allow_html=True)


def kaart1(r: k1_basis.Resultaat, tag) -> None:
    k = kleur(1)
    _kop(1)
    _formule("P[t] = 4 × N × E × v[t], met E = E_jaar × d en v = f ÷ d")
    stap(1, "Aantal woningen N", nl(r.N), "woningen", tag=tag("woningtypen"),
         uitleg="Som van de woningen per woningtype in de buurt (CBS).")
    stap(2, "Netto jaarverbruik per woningtype", nl(r.e_netto / 1e3), "MWh/jaar",
         staven(r.types["woningtype"], r.types["e_netto_kwh"] / 1e3, k, "MWh/jaar"), tag=tag("woningtypen"),
         uitleg="Aantal woningen × netto verbruik per woning (Klimaatmonitor: levering min teruglevering).")
    mwh = [r.e_netto / 1e3, r.e_zon_bruto / 1e3, -r.e_wp_huidig / 1e3, -r.e_ev_thuis_huidig / 1e3, 0]
    stap(3, "Van netto naar huishoudelijk jaarverbruik", nl(r.e_jaar_buurt / 1e3), "MWh/jaar",
         waterval(["E_netto", f"+zon ({kn(7)})", f"−WP ({kn(3)})", f"−EV ({kn(4)})", "E_jaar"], mwh,
                  ["absolute", "relative", "relative", "relative", "total"], "MWh"),
         extra=[("per woning", f"{nl(r.e_jaar)} kWh/jaar")],
         tag=tag("woningtypen", "buurten", "zon_opbrengst", "scop_huidig", "gas_tapwater_m3", "ev_jaarenergie",
                 "ev_aandeel_thuis", "autos_gemeente"),
         uitleg="Bruto zon erbij (eigen verbruik zat verstopt in netto), bestaande warmtepompen en thuisladen eraf. "
                f"Die komen volledig terug op kaart {kn(3)} en {kn(4)}; de opwek op kaart {kn(7)}.")
    stap(4, "Naar de referentiedag: d en E", nl(r.E, 2), "kWh/woning/dag",
         lijn({"f[t]": r.f}, [k], fmt=".2e", tickformat=".0e"),
         extra=[("d", nl(r.d, 5)), ("d × 365", nl(r.d * 365, 2))], tag=tag("nedu_e1a"),
         uitleg="f[t] is het NEDU-profiel E1A_AZI_A: het deel van het jaarverbruik per kwartier; d = som over de dag; "
                "E = E_jaar × d. AZI (aansluitingen zonder teruglevering) omdat E_jaar het bruto huishoudverbruik is: "
                f"zo zit er geen zelfverbruik van zon in de vorm, en telt de opwek alleen in tab {kn(7)}.")
    stap(5, "Vorm v = f ÷ d", nl(r.v.sum(), 3), "Σ v", lijn({"v[t]": r.v}, [k]), tag=tag("nedu_e1a"),
         uitleg="Dezelfde vorm, geschaald zodat de dag optelt tot 1.")
    p_en_checks(6, r.P, k, r.checks)


def kaart3(r: k3_warmtepomp.Resultaat, varianten: dict, p, tag, p_isolatie: float, labeltabel) -> None:
    k = kleur(3)
    q_par = ("buurten", "gas_tapwater_koken_m3", "calorische_waarde", "ketelrendement")
    cop_par = {"geen": "cop_ae", "all-electric": "cop_ae", "ZLT": "cop_zlt", "MT": "mt_pompfactor"}[r.oplossing]
    _kop(3)
    _formule("P[t] = 4 × N × E × v[t], met E = Q_ref ÷ COP")
    stap(1, "Aantal woningen N", nl(r.N), "woningen", extra=[("warmteoplossing", r.oplossing)],
         tag=tag("buurten", "wp_gemeente") if r.oplossing == "geen" else tag("buurten"),
         uitleg="Bij 'geen': alleen de huidige warmtepompen, het gemeentetotaal verdeeld naar het aandeel woningen in "
                "de buurt (eenvoudige verdeelregel, kan verfijnd worden). Anders alle woningen in de buurt op de "
                "gekozen warmteoplossing (keuze per buurt in de zijbalk).")
    stap(2, "Warmtevraag uit gas", nl(r.q_jaar_gas), "kWh warmte/woning/jaar",
         waterval(["gas", "−tapwater en koken", "ruimteverwarming"], [r.gas, -r.gas_tapwater_koken, 0],
                  ["absolute", "relative", "total"], "m³"),
         extra=[("× cal. waarde × ketelrendement", nl(p["calorische_waarde"] * p["ketelrendement"], 2))],
         tag=tag(*q_par),
         uitleg="Gasverbruik per woning min een vast gemiddelde voor tapwater en koken, omgerekend naar nuttige warmte.")
    lt = labeltabel
    stap(3, "Labelcorrectie", nl(r.labelfactor, 3), "labelfactor buurt",
         staven(lt["label"], lt["aandeel_buurt"] * 100, kleuren=[k] * len(lt), eenheid="% adressen", fmt=".0f"),
         extra=[("Q_jaar", f"{nl(r.q_jaar)} kWh warmte/woning/jaar"),
                ("factoren", " ".join(f"{l} {nl(f, 2)}" for l, f in zip(lt["label"], lt["factor"])))],
         tag=tag("energielabels", "labels_buurt"),
         uitleg="Demo: factor per energielabel, gewogen met de labelverdeling van de buurt en gedeeld door het "
                "gemeentegemiddelde. Een buurt met de gemeentelijke labelverdeling krijgt factor 1.")
    stap(4, "Warmtevraag op de referentiedag Q_ref", nl(r.q_ref, 1), "kWh warmte/woning/dag",
         lijn({"T[t]": r.T}, [KLEUR[0]], "°C", fmt=".1f", hlijn=(p["t_stookgrens"], "stookgrens")),
         extra=[("graaddagen", nl(r.gd_ref, 1)),
                ("dag ÷ gemiddelde dag", nl(r.q_ref * 365 / r.q_jaar, 2) if r.q_jaar else "–"),
                ("isolatie buurt", f"{nl(p_isolatie)} %")],
         tag=tag(*q_par, "T", "t_stookgrens", "gd_jaar"),
         uitleg="Q_jaar × graaddagen van deze dag ÷ graaddagen per jaar × (1 − isolatie). Graaddagen = stookgrens "
                "min daggemiddelde temperatuur (KNMI); per jaar: KNMI 2025.")
    if r.band:
        anders = next(n for n in r.band if n != r.vorm_bron)
        stap(5, "Vorm v: bandbreedte vlak tot G1A", r.vorm_bron, "gebruikt (keuze in de zijbalk)",
             lijn({n: vv for n, (vv, _) in r.band.items()}, [k, MUTED]),
             extra=[(f"piek {n}", f"{nl(_piek_per_eenheid(r.E, vv), 2)} kW/woning "
                     + ("constant" if np.ptp(vv) == 0 else f"om {TIJD[int(np.argmax(vv))]}"))
                    for n, (vv, _) in r.band.items()],
             tag=tag("nedu_g1a_tap"),
             uitleg="Hoe de dagenergie over de dag valt, hangt af van buffering in woning en installatie. Vlak: maximale "
                    "buffering (ondergrens piek). G1A: volgt het stookgedrag van gasgestookte woningen, het "
                    "temperatuurafhankelijke deel van het NEDU-gasprofiel op deze dag (bovengrens piek).")
    else:
        i = int(np.argmax(r.v))
        stap(5, "Vorm v (graaduren)", nl(r.v.sum(), 3), "Σ v", lijn({"v[t]": r.v}, [k]),
             extra=[("hoogste kwartier", TIJD[i]), ("max ÷ gemiddeld", nl(r.v.max() * 96, 2))], tag=tag("T", "t_stookgrens"),
             uitleg="Naar rato van het temperatuurverschil met de stookgrens per kwartier (ongewijzigd voor ZLT en MT).")
    stap(6, "Elektriciteit per woning E = Q_ref ÷ COP", nl(r.E, 2), "kWh/woning/dag",
         extra=[("COP", nl(r.cop, 2)), ("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW/woning")],
         tag=tag(cop_par, *q_par),
         uitleg={"geen": "Eén COP voor de hele dag, als all-electric.",
                 "all-electric": "Eén COP voor de hele dag.",
                 "ZLT": "Booster op het ZLT-net: vaste COP.",
                 "MT": "Geen warmtepomp per woning; alleen pompenergie per kWh warmte (placeholder)."}[r.oplossing])
    stap(7, "Warmteoplossingen naast elkaar", None,
         fig=lijn({o: v.P for o, v in varianten.items()}, KLEUR[:len(varianten)], "kW", fmt=",.0f"),
         extra=[(o, f"{nl(v.P.max())} kW ({nl(_piek_per_eenheid(v.E, v.v), 2)} kW/woning)")
                for o, v in varianten.items()],
         tag=tag("T", *q_par, "cop_ae", "cop_zlt", "mt_pompfactor", "nedu_g1a_tap"),
         uitleg="Dezelfde buurt bij elke warmteoplossing; 'geen' is alleen de huidige warmtepompen.")
    fig = None
    if r.band:
        fig = lijn({f"{n}{' (gebruikt)' if n == r.vorm_bron else ''}": P for n, (_, P) in r.band.items()},
                   [k if n == r.vorm_bron else MUTED for n in r.band], "kW", H_GROOT, fmt=",.0f")
    p_en_checks(8, r.P, k, r.checks, fig=fig)


def kaart4(r: k4_laden_auto.Resultaat, p, tag, p_ev_toename: float) -> None:
    k = kleur(4)
    _kop(4)
    _formule("P[t] = 4 × N × E × v[t], met v = (1 − a) × v_ongestuurd + a × v_slim")
    stap(1, "Aantal elektrische auto's N", nl(r.N), "auto's",
         staven(["Huidig (jan 2025)", "Toename", "N"], [r.n_huidig, r.n_extra, r.N], k, "auto's"),
         extra=[("EV toename buurt", f"{nl(p_ev_toename)} % van de personenauto's")],
         tag=tag("buurten", "autos_gemeente"),
         uitleg="Huidige EV's (632 BEV in de gemeente, verdeeld naar aandeel personenauto's) plus de toename per buurt "
                "als percentage van de huidige personenauto's in de buurt (zijbalk).")
    stap(2, "Laadenergie per auto E", nl(r.E, 1), "kWh/auto/dag",
         extra=[("× 365", f"{nl(r.E * 365)} kWh/jaar"), (f"jaarwaarde op kaart {kn(1)}", f"{nl(p['ev_jaarenergie'])} kWh")],
         tag=tag("ev_e_dag", "ev_jaarenergie"),
         uitleg="Dagwaarde op een winterwerkdag, thuis en openbaar samen.")
    stap(3, "Laadvorm: ongestuurd, slim en gemengd", f"{nl(r.a * 100)} %", "slim (a)",
         lijn({"ongestuurd": r.v_ongestuurd, "slim": r.v_slim, "gemengd": r.v}, [KLEUR[0], KLEUR[1], KLEUR[2]]),
         extra=[("piek ongestuurd", f"{nl(_piek_per_eenheid(r.E, r.v_ongestuurd), 2)} kW/auto"),
                ("gemengd", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW/auto")],
         tag=tag("ev_ongestuurd", "ev_slim", "slim_aandeel"),
         uitleg="Mengsel van twee vaste vormen met aandeel slim laden a. N en E veranderen niet. Vormen: mock tot "
                "de ElaadNL-dataset gekozen is.")
    p_en_checks(4, r.P, k, r.checks)


def kaart7(r: k7_zon.Resultaat, p, tag) -> None:
    k = kleur(7)
    _kop(7)
    _formule("P[t] = 4 × N × E × v[t], met E = jaaropbrengst per kWp × I_ref ÷ I_jaar en Σ v = −1")
    stap(1, "Opgesteld vermogen N", nl(r.N), "kWp",
         staven(["Huidig", "Scenario"], [r.n_huidig, r.N], k, "kWp"),
         extra=[("groei", f"{nl(p['zon_groei'])} %")], tag=tag("buurten", "zon_groei"),
         uitleg=f"kWp bij woningen in de buurt × (1 + groei). Zon van bedrijven staat op kaart {kn(6)}.")
    stap(2, "Opbrengst per kWp op de referentiedag E", nl(r.E, 3), "kWh/kWp/dag",
         lijn({"I[t]": r.I}, [KLEUR[3]], "W/m²", fmt=",.0f"),
         extra=[("I_ref", f"{nl(r.i_ref, 2)} kWh/m²"), ("dag ÷ gemiddelde dag", nl(r.i_ref * 365 / p["i_jaar"], 2)),
                ("PR", nl(r.E / r.i_ref, 2) if r.i_ref else "–")],
         tag=tag("I", "zon_opbrengst", "i_jaar"),
         uitleg="Jaaropbrengst per kWp geschaald met de instraling van deze dag ten opzichte van het jaar (KNMI, "
                "horizontaal vlak). kWp en jaaropbrengst komen zoveel mogelijk uit Zonnedakje.")
    stap(3, "Vorm v = −I ÷ Σ I", nl(r.v.sum(), 3), "Σ v", lijn({"v[t]": r.v}, [k]),
         extra=[("grootste opwek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW/kWp")], tag=tag("I"),
         uitleg="Volgt de gemeten instraling per uur; negatief omdat het opwek is.")
    p_en_checks(4, r.P, k, r.checks)


def _type_a(nr_kleur: int, r, formule: str, n_titel: str, n_eenheid: str, n_uitleg: str, e_eenheid: str,
            e_uitleg: str, v_uitleg: str, basis_label: str, basis_n: float, e_par: str, v_naam: str, n_tag,
            tag) -> None:
    """Standaard type A met dagwaarde: N, E, v, P en checks (kaart 2 en 5)."""
    k = kleur(nr_kleur)
    _formule(formule)
    stap(1, n_titel, nl(r.N), n_eenheid, staven([basis_label, "N"], [basis_n, r.N], k, ""), tag=tag(*n_tag),
         uitleg=n_uitleg)
    stap(2, "Energie per eenheid E", nl(r.E, 2), e_eenheid, extra=[("× 365", f"{nl(r.E * 365)} kWh/jaar")],
         tag=tag(e_par), uitleg=e_uitleg)
    i = int(np.argmax(r.v))
    stap(3, "Vorm v", nl(r.v.sum(), 3), "Σ v", lijn({"v[t]": r.v}, [k]),
         extra=[("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per eenheid om {TIJD[i]}")], tag=tag(v_naam),
         uitleg=v_uitleg)
    p_en_checks(4, r.P, k, r.checks)


def kaart2(r: k2_koken.Resultaat, tag) -> None:
    _kop(2)
    _type_a(2, r, "P[t] = 4 × N × E × v[t], met N = huishoudens × groei in penetratie",
            "Nieuw elektrisch kokende huishoudens N", "huishoudens",
            f"Huishoudens × groei in penetratie. Alleen de groei: huidig elektrisch koken zit al in kaart {kn(1)}.",
            "kWh/huishouden/dag", "Dagwaarde op een winterwerkdag.",
            "Kookprofiel van een groep huishoudens; de gelijktijdigheid zit in de vorm.",
            "Huishoudens", r.huishoudens, "koken_e_dag", "koken", ("buurten", "koken_penetratie_groei"), tag)


def kaart5(r: k5_logistiek.Resultaat, p, tag) -> None:
    kl = r.klassen
    kleuren = KLEUR[:len(kl)]
    par = ("buurten", "log_elektrificatie", "log_groei")
    _kop(5, extra=badge("placeholder").replace("margin-left:6px", "margin-left:0") + " N, E en v zijn allemaal open")
    _formule("P[t] = Σ over voertuigtypen 4 × N × E × v[t], met N = voertuigen × elektrificatie × (1 + groei)")
    stap(1, "Elektrische voertuigen N per type", nl(sum(k.N for k in kl.values())), "voertuigen",
         staven(list(kl), [k.N for k in kl.values()], kleuren=kleuren, eenheid="voertuigen", fmt=",.1f"),
         extra=[(n, f"{nl(k.voertuigen)} × {nl(p['log_elektrificatie'])} % × (1 + {nl(p['log_groei'])} %)")
                for n, k in kl.items()], tag=tag(*par),
         uitleg="Bestelauto's en trucks in de buurt × elektrificatiegraad × (1 + groei).")
    stap(2, "Energie per voertuig E", None,
         staven(list(kl), [k.E for k in kl.values()], kleuren=kleuren, eenheid="kWh/voertuig/dag"),
         extra=[(n, f"{nl(k.E)} kWh/dag") for n, k in kl.items()], tag=tag("log_e_dag_bestel", "log_e_dag_truck"),
         uitleg="Dagwaarde per voertuigtype.")
    stap(3, "Vorm v per type", None, lijn({n: k.v for n, k in kl.items()}, kleuren),
         extra=[(n, f"{nl(_piek_per_eenheid(k.E, k.v), 2)} kW/voertuig om {TIJD[int(np.argmax(k.v))]}")
                for n, k in kl.items()], tag=tag("logistiek_bestel", "logistiek_truck"),
         uitleg="Laadprofiel per voertuigtype (depotladen).")
    p_en_checks(4, r.P, kleur(5), r.checks, naam="P[t] per voertuigtype",
                fig=gestapeld({n: k.P for n, k in kl.items()}, kleuren, totaal=r.P))


def kaart6(r: k6_mkb.Resultaat, opties: dict, tag) -> None:
    df = r.sectoren
    kleuren = KLEUR[:len(df)]
    _kop(6)
    _formule("P[t] = Σ over sectoren 4 × E_s × v_s[t], met E_s = E_jaar,s × d_s (N = 1 per sector)")
    stap(1, "Jaarverbruik per sector E_jaar", nl((df["teken"] * df["e_jaar"]).sum() / 1e3), "MWh/jaar netto",
         staven(df["sector"], df["teken"] * df["e_jaar"] / 1e3, kleuren=kleuren, eenheid="MWh/jaar"),
         tag=tag("sectoren", "groei_niet_huish"),
         uitleg="Gemeentetotaal per sector verdeeld naar de buurt, × (1 + groei). Opwek van bedrijven negatief.")
    stap(2, "Naar de referentiedag: d per sector", nl(float(df["E"].abs().sum())), "kWh/dag (bruto)",
         staven(df["sector"], df["d"] * 365, kleuren=kleuren, eenheid="d × 365", fmt=".2f"),
         tag=tag(*r.v.keys(), "i_jaar"),
         uitleg="d = deel van het jaar dat op deze dag valt, uit het sectorprofiel. d × 365 > 1: drukker dan een "
                f"gemiddelde dag. Opwek: uit de instraling, net als kaart {kn(7)}.")
    vorm_tag = tag("nedu_e3") if r.profielbron == "NEDU E3" else tag(*r.v.keys())
    stap(3, f"Vorm per sector v_s ({r.profielbron})", None, fig=lijn(r.v, kleuren), tag=vorm_tag,
         uitleg={"Liander": "Liander open data: elke sector een eigen profiel. Verbruik telt op tot +1, opwek tot −1.",
                 "NEDU E3": "NEDU E3: één profiel voor alle verbruikssectoren (E3A t/m E3D zijn gelijk, bevroren "
                            "meetdata 2011 tot 2013). Opwek houdt de zonvorm."}[r.profielbron])
    stap(4, "Twee opties voor de sectorprofielen", None,
         fig=lijn({n: v.P_tot for n, v in opties.items()}, [KLEUR[0], KLEUR[1]], "kW", fmt=",.0f"),
         extra=[(n, f"max {nl(v.P_tot.max())} kW om {TIJD[int(np.argmax(v.P_tot))]}") for n, v in opties.items()],
         tag=tag(*r.v.keys(), "nedu_e3"),
         uitleg="Zelfde jaarverbruik per sector, andere vorm. Keuze in de zijbalk.")
    p_en_checks(5, r.P_tot, kleur(6), r.checks, naam="P[t] per sector", fig=gestapeld(r.P, kleuren, totaal=r.P_tot))


def stapeling(r: stapeling_model.Resultaat, kleuren: list[str]) -> None:
    i = r.i_piek
    _kop(9)
    _formule(f"P_buurt[t] = som van P[t] over de kaarten (zonder kaart {kn(5)})")
    stap(1, "Piek van de buurt", nl(r.P_tot[i]), "kW", extra=[("om", TIJD[i]), ("laagste", f"{nl(r.P_tot.min())} kW")],
         uitleg="Hoogste kwartier van het gestapelde profiel.")
    stap(2, f"Bijdrage per kaart op het piekkwartier ({TIJD[i]})", None,
         fig=staven(r.tabel["kaart"], r.tabel["op_piek"], kleuren=kleuren, eenheid="kW"),
         uitleg="Welke kaarten de piek bepalen.")
    stap(3, "Eigen piek per kaart en tijdstip", None,
         fig=staven([f"{k} · {TIJD[j]}" for k, j in zip(r.tabel["kaart"], r.tabel["i_extreem"])],
                    r.tabel["extreem"], kleuren=kleuren, eenheid="kW"),
         uitleg="Hoogste kwartier van elke kaart apart; bij zon de grootste opwek. Vallen die samen, dan stapelt "
                "de piek.")
    p_en_checks(4, r.P_tot, KLEUR[0], r.checks, naam="P_buurt[t]", fig=gestapeld(r.P, kleuren, totaal=r.P_tot))


def kaart8(r: k8_batterij.Resultaat, p, tag) -> None:
    k = kleur(8)
    _kop(8)
    _formule("P[t] = N × v[t], met v in kW per kWh opslagcapaciteit; geen E")
    stap(1, "Opslagcapaciteit N", nl(r.N), "kWh",
         extra=[("batterijen", f"{nl(r.batterijen)} (woningen × {nl(p['bat_adoptie'])} %)"),
                ("capaciteit", f"{nl(p['bat_kwh'], 1)} kWh per batterij")],
         tag=tag("buurten", "bat_adoptie", "bat_kwh"),
         uitleg="Woningen × adoptiegraad × capaciteit per batterij.")
    stap(2, "Geen dagenergie E", None,
         uitleg="Een batterij verbruikt netto geen energie: de vorm telt op tot ongeveer 0 (iets meer door verliezen).")
    overschot = float(np.clip(r.pv - r.last, 0, None).sum() / 4)
    stap(3, "Last en zon per batterijwoning", nl(overschot, 2), "kWh zonoverschot/dag",
         lijn({f"last (tab {kn(1)})": r.last, f"zon (tab {kn(7)})": r.pv}, [KLEUR[0], KLEUR[3]], "kW", fmt=".2f"),
         extra=[("zon per batterijwoning", f"{nl(p['bat_kwp_woning'], 1)} kWp")],
         tag=tag("nedu_e1a", "I", "bat_kwp_woning"),
         uitleg=f"Gemiddelde woning uit tab {kn(1)} met de zon van één batterijwoning uit tab {kn(7)}. Alleen het "
                "overschot kan de batterij met zelfconsumptie laden.")
    stap(4, "Day-ahead prijs", f"{int(r.goedkoop.sum())}", "goedkoopste en duurste kwartieren",
         lijn({"prijs": r.prijs}, [KLEUR[1]], "€/MWh", fmt=",.0f"), tag=tag("prijs"),
         extra=[("laden rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.goedkoop)[:3]) + " …"),
                ("ontladen rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.duur)[:3]) + " …")],
         uitleg="Alleen voor zelfconsumptie + day-ahead: laden in de goedkoopste en ontladen in de duurste kwartieren; "
                "aantal = wat nodig is om vol of leeg te gaan.")
    stap(5, "Vorm v per modus", r.modus, "gebruikt (keuze in de zijbalk)",
         lijn({m: md.v for m, md in r.modi.items()}, [KLEUR[0], KLEUR[1]], "kW/kWh", fmt=".3f"),
         extra=[(m, f"Σ v ÷ 4 = {nl(md.v.sum() / 4, 4)}") for m, md in r.modi.items()],
         tag=tag("bat_c", "bat_eta", "prijs"),
         uitleg="Zelfconsumptie: laden bij zonoverschot, ontladen bij tekort. Plus day-ahead: daarnaast laden uit het "
                "net in goedkope kwartieren en ontladen in dure. Positief is laden. Eind-SoC = begin-SoC.")
    stap(6, "Laadtoestand per modus", None,
         fig=lijn({m: md.soc * 100 for m, md in r.modi.items()}, [KLEUR[0], KLEUR[1]], "% SoC", fmt=".0f"),
         tag=tag("bat_c", "bat_eta", "prijs"), uitleg="Hoe vol de batterij is over de dag.")
    p_en_checks(7, r.P, k, r.checks)
