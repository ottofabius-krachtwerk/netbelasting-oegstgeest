"""Eén renderfunctie per kaart. Stappen staan onder elkaar, in rekenvolgorde, in gewone taal.

Symbolen (N, E, v, P) staan alleen klein tussen haakjes; de tekst moet zonder die symbolen te volgen zijn.
"""
import numpy as np
import streamlit as st

from model import k1_basis, k2_koken, k3_warmtepomp, k4_laden_auto, k5_logistiek, k6_mkb, k7_zon, k8_batterij
from model import stapeling as stapeling_model
from model.common import nl
from ui.charts import H_GROOT, KLEUR, MUTED, TIJD, gestapeld, lijn, staven, waterval
from ui.kaarten import kleur, kn, meta
from ui.stappen import badge, kop, p_en_checks, stap

VERLOOP = "% van de dag per kwartier"


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


def _kop(kaart: int, extra: str = "") -> None:
    kop(*meta(kaart), extra=extra)


def _formule(zin: str, symbolen: str) -> None:
    """Rekenregel in gewone taal, met de formule klein erachter."""
    st.markdown(f"<div style='font-size:.9rem;color:#0b0b0b;margin:-.2rem 0 .6rem'>{zin}"
                f"<span style='font-size:.75rem;color:#898781;margin-left:.6rem'>{symbolen}</span></div>",
                unsafe_allow_html=True)


def kaart1(r: k1_basis.Resultaat, tag) -> None:
    k = kleur(1)
    _kop(1)
    _formule("Profiel = aantal woningen × verbruik per woning op deze dag × verloop over de dag",
             "P[t] = 4 × N × E × v[t]")
    stap(1, "Aantal woningen", nl(r.N), "woningen", tag=tag("woningtypen"),
         uitleg="Som van de woningen per woningtype in de buurt (CBS).",
         bron="CBS (woningen per woningtype per buurt)")
    stap(2, "Netto jaarverbruik per woningtype", nl(r.e_netto / 1e3), "MWh/jaar",
         staven(r.types["woningtype"], r.types["e_netto_kwh"] / 1e3, k, "MWh/jaar"), tag=tag("woningtypen"),
         uitleg="Aantal woningen × netto verbruik per woning (Klimaatmonitor: levering min teruglevering).",
         bron="Klimaatmonitor (netto levering per woningtype, PC6, 2025) × CBS (woningen per woningtype)")
    mwh = [r.e_netto / 1e3, r.e_zon_bruto / 1e3, -r.e_wp_huidig / 1e3, -r.e_ev_thuis_huidig / 1e3, 0]
    stap(3, "Van netto naar huishoudelijk jaarverbruik", nl(r.e_jaar_buurt / 1e3), "MWh/jaar",
         waterval(["netto", f"+zon (tab {kn(7)})", f"−warmtepompen (tab {kn(3)})", f"−thuisladen (tab {kn(4)})",
                   "huishoudelijk"], mwh, ["absolute", "relative", "relative", "relative", "total"], "MWh"),
         extra=[("per woning", f"{nl(r.e_jaar)} kWh/jaar")],
         tag=tag("woningtypen", "buurten", "zon_opbrengst", "scop_huidig", "gas_tapwater_koken_m3", "ev_jaarenergie",
                 "ev_aandeel_thuis", "autos_gemeente"),
         uitleg="Zonnestroom die woningen zelf gebruiken zit niet in het netto verbruik, dus die komt erbij. Het "
                "verbruik van bestaande warmtepompen en thuisladen gaat eraf: dat rekenen tab "
                f"{kn(3)} en {kn(4)} volledig zelf. De opwek zelf staat in tab {kn(7)}.",
         bron=f"stap 2; tab {kn(7)} (bruto zonopwek huidig); tab {kn(3)} (huidige warmtepompen); tab {kn(4)} (thuisladen huidige EV's)")
    stap(4, "Verbruik per woning op deze dag", nl(r.E, 2), "kWh per woning",
         extra=[("deel van het jaarverbruik", f"{nl(r.d * 100, 3)} %"),
                ("ten opzichte van een gemiddelde dag", f"{nl(r.d * 365, 2)} ×")],
         tag=tag("nedu_e1a"),
         uitleg="Het NEDU-standaardprofiel zegt welk deel van het jaarverbruik op deze dag valt "
                "(E = E_jaar × d).",
         bron="NEDU standaardprofielen elektriciteit 2025 (E1A_AZI_A, 18-02-2025)")
    stap(5, "Verloop over de dag", _hoogste(r.v), "hoogste kwartier",
         lijn({"huishoudens": _pct(r.v)}, [k], VERLOOP, fmt=".2f"), tag=tag("nedu_e1a"),
         extra=[("hoogste kwartier", f"{nl(r.v.max() * 100, 2)} % van de dag")],
         uitleg="NEDU-profiel E1A_AZI_A: huishoudens zonder teruglevering. Gekozen omdat het jaarverbruik hierboven het "
                "bruto huishoudverbruik is; zo zit er geen eigen verbruik van zon in het verloop, en telt de opwek "
                f"alleen in tab {kn(7)} (v).",
         bron="NEDU standaardprofielen elektriciteit 2025 (E1A_AZI_A, 18-02-2025)")
    p_en_checks(6, r.P, k, r.checks)


def kaart3(r: k3_warmtepomp.Resultaat, varianten: dict, p, tag, p_isolatie: float, labeltabel) -> None:
    k = kleur(3)
    q_par = ("buurten", "gas_tapwater_koken_m3", "calorische_waarde", "ketelrendement")
    cop_par = {"geen": "cop_ae", "all-electric": "cop_ae", "ZLT": "cop_zlt", "MT": "mt_pompfactor"}[r.oplossing]
    _kop(3)
    _formule("Profiel = aantal woningen × stroom per woning op deze dag × verloop over de dag; "
             "stroom = warmtevraag ÷ COP", "P[t] = 4 × N × E × v[t], E = Q_ref ÷ COP")
    stap(1, "Aantal woningen met een warmtepomp", nl(r.N), "woningen", extra=[("warmteoplossing", r.oplossing)],
         tag=tag("buurten", "wp_gemeente") if r.oplossing == "geen" else tag("buurten"),
         uitleg="Bij 'geen': alleen de huidige warmtepompen, het gemeentetotaal verdeeld naar het aandeel woningen in "
                "de buurt (eenvoudige verdeelregel, kan verfijnd worden). Anders alle woningen in de buurt op de "
                "gekozen warmteoplossing (keuze per buurt in de zijbalk).",
         bron="Klimaatmonitor (woningen; huidige warmtepompen in de gemeente) · warmteoplossing: invoer zijbalk")
    stap(2, "Warmtevraag per woning per jaar, uit gas", nl(r.q_jaar_gas), "kWh warmte",
         waterval(["gas", "−tapwater en koken", "ruimteverwarming"], [r.gas, -r.gas_tapwater_koken, 0],
                  ["absolute", "relative", "total"], "m³"),
         extra=[("omrekening", f"× {nl(p['calorische_waarde'] * p['ketelrendement'], 2)} kWh warmte per m³ gas")],
         tag=tag(*q_par),
         uitleg="Gasverbruik per woning min een vast gemiddelde voor tapwater en koken, omgerekend naar nuttige warmte "
                "(calorische waarde × ketelrendement).",
         bron="Klimaatmonitor (gasverbruik per woning) · 100 m³ tapwater en koken: projectaanname")
    lt = labeltabel
    stap(3, "Correctie voor energielabels", nl(r.labelfactor, 3), "× de warmtevraag",
         staven(lt["label"], lt["aandeel_buurt"] * 100, kleuren=[k] * len(lt), eenheid="% adressen", fmt=".0f"),
         extra=[("warmtevraag na correctie", f"{nl(r.q_jaar)} kWh warmte per woning per jaar"),
                ("factoren", " ".join(f"{l} {nl(f, 2)}" for l, f in zip(lt["label"], lt["factor"])))],
         tag=tag("energielabels", "labels_buurt"),
         uitleg="Demo: een factor per energielabel, gewogen met de labelverdeling van de buurt (grafiek) en gedeeld "
                "door het gemeentegemiddelde. Een buurt met de gemeentelijke labelverdeling krijgt factor 1.",
         bron="Zonnedakje (energielabels per adres) · factoren per label: demo")
    stap(4, "Warmtevraag per woning op deze dag", nl(r.q_ref, 1), "kWh warmte",
         lijn({"buitentemperatuur": r.T}, [KLEUR[0]], "°C", fmt=".1f", hlijn=(p["t_stookgrens"], "stookgrens")),
         extra=[("graaddagen deze dag", nl(r.gd_ref, 1)),
                ("ten opzichte van een gemiddelde dag", f"{nl(r.q_ref * 365 / r.q_jaar, 2)} ×" if r.q_jaar else "–"),
                ("isolatie", f"{nl(p_isolatie)} % minder warmtevraag dan nu")],
         tag=tag(*q_par, "T", "t_stookgrens", "gd_jaar"),
         uitleg="Jaarlijkse warmtevraag × graaddagen van deze dag ÷ graaddagen per jaar (KNMI 2025), minus isolatie. "
                "Graaddagen = stookgrens min de gemiddelde buitentemperatuur van de dag (Q_ref).",
         bron="KNMI station 215 (temperatuur 18-02-2025, graaddagen 2025) · isolatie: invoer zijbalk")
    if r.band:
        stap(5, "Verloop over de dag: bandbreedte", r.vorm_bron, "gebruikt (keuze in de zijbalk)",
             lijn({n: _pct(vv) for n, (vv, _) in r.band.items()}, [k, MUTED], VERLOOP, fmt=".2f"),
             extra=[(f"piek {n}", f"{nl(_piek_per_eenheid(r.E, vv), 2)} kW per woning "
                     + ("constant" if np.ptp(vv) == 0 else f"om {TIJD[int(np.argmax(vv))]}"))
                    for n, (vv, _) in r.band.items()],
             tag=tag("nedu_g1a_tap"),
             uitleg="Hoe de stroom over de dag valt, hangt af van buffering in woning en installatie. Vlak: maximale "
                    "buffering (laagste piek). G1A: volgt het stookgedrag van gasgestookte woningen, uit het "
                    "NEDU-gasprofiel op deze dag (hoogste piek).",
         bron="NEDU standaardprofielen aardgas 2025 (G1A, temperatuurafhankelijk deel) · vlak: aanname · warmtepompprofiel in uitwerking")
    else:
        stap(5, "Verloop over de dag", _hoogste(r.v), "hoogste kwartier",
             lijn({"verloop": _pct(r.v)}, [k], VERLOOP, fmt=".2f"), tag=tag("T", "t_stookgrens"),
             extra=[("hoogste kwartier", f"{nl(r.v.max() * 100, 2)} % van de dag")],
             uitleg="Naar rato van het verschil tussen buitentemperatuur en stookgrens per kwartier (ongewijzigd voor "
                    "ZLT en MT).",
         bron="KNMI station 215 (temperatuur 18-02-2025)")
    stap(6, "Stroom per woning op deze dag", nl(r.E, 2), "kWh per woning",
         extra=[("COP", f"{nl(r.cop, 2)} kWh warmte per kWh stroom"),
                ("piek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per woning")],
         tag=tag(cop_par, *q_par),
         uitleg={"geen": "Warmtevraag op deze dag ÷ één COP voor de hele dag, als all-electric.",
                 "all-electric": "Warmtevraag op deze dag ÷ één COP voor de hele dag.",
                 "ZLT": "Warmtevraag op deze dag ÷ de COP van de booster op het ZLT-net.",
                 "MT": "Geen warmtepomp per woning; alleen pompenergie per kWh warmte (placeholder)."}[r.oplossing],
         bron="stap 4 · COP: bron open")
    stap(7, "Warmteoplossingen naast elkaar", None,
         fig=lijn({o: v.P for o, v in varianten.items()}, KLEUR[:len(varianten)], "kW", fmt=",.0f"),
         extra=[(o, f"{nl(v.P.max())} kW ({nl(_piek_per_eenheid(v.E, v.v), 2)} kW per woning)")
                for o, v in varianten.items()],
         tag=tag("T", *q_par, "cop_ae", "cop_zlt", "mt_pompfactor", "nedu_g1a_tap"),
         uitleg="Dezelfde buurt bij elke warmteoplossing; 'geen' is alleen de huidige warmtepompen.",
         bron="stappen 1 tot en met 6, voor elke warmteoplossing")
    fig = None
    if r.band:
        fig = lijn({f"{n}{' (gebruikt)' if n == r.vorm_bron else ''}": P for n, (_, P) in r.band.items()},
                   [k if n == r.vorm_bron else MUTED for n in r.band], "kW", H_GROOT, fmt=",.0f")
    p_en_checks(8, r.P, k, r.checks, fig=fig)


def kaart4(r: k4_laden_auto.Resultaat, p, tag, p_ev_toename: float) -> None:
    k = kleur(4)
    _kop(4)
    _formule("Profiel = aantal elektrische auto's × laadenergie per auto op deze dag × laadverloop over de dag",
             "P[t] = 4 × N × E × v[t], v = (1 − a) × v_ongestuurd + a × v_slim")
    stap(1, "Aantal elektrische auto's", nl(r.N), "auto's",
         extra=[("huidig (jan 2025)", nl(r.n_huidig)),
                ("extra", f"{nl(r.n_extra)} ({nl(p_ev_toename)} % van alle huidige personenauto's)")],
         tag=tag("buurten", "autos_gemeente"),
         uitleg="Huidige EV's (632 in de gemeente, verdeeld naar aandeel personenauto's) plus extra EV's: een "
                "percentage van alle huidige personenauto's in de buurt, bovenop de huidige EV's (zijbalk).",
         bron="Klimaatmonitor (632 BEV, januari 2025) · CBS Kerncijfers wijken en buurten (personenauto's) · extra EV's: invoer zijbalk")
    stap(2, "Laadenergie per auto op deze dag", nl(r.E, 1), "kWh per auto",
         extra=[("× 365", f"{nl(r.E * 365)} kWh per jaar"),
                (f"jaarwaarde gebruikt in tab {kn(1)}", f"{nl(p['ev_jaarenergie'])} kWh")],
         tag=tag("ev_e_dag", "ev_jaarenergie"),
         uitleg="Dagwaarde op een winterwerkdag, thuis en openbaar samen.",
         bron="onderbouwing open (7 tot 9 kWh volgens de rekenkaart)")
    stap(3, "Laadverloop: ongestuurd, slim en gemengd", f"{nl(r.a * 100)} %", "slim laden",
         lijn({"ongestuurd": _pct(r.v_ongestuurd), "slim": _pct(r.v_slim), "gemengd": _pct(r.v)},
              [KLEUR[0], KLEUR[1], KLEUR[2]], VERLOOP, fmt=".2f"),
         extra=[("piek ongestuurd", f"{nl(_piek_per_eenheid(r.E, r.v_ongestuurd), 2)} kW per auto"),
                ("gemengd", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per auto")],
         tag=tag("ev_ongestuurd", "ev_slim", "slim_aandeel"),
         uitleg="Het gemengde verloop weegt ongestuurd en slim laden met het aandeel slim laden (% van alle EV's, "
                "huidig en extra). Aantal en laadenergie veranderen niet. Verlopen: mock tot de ElaadNL-dataset "
                "gekozen is.",
         bron="ElaadNL gemeten aggregaat (dataset open) · aandeel slim laden: invoer zijbalk")
    p_en_checks(4, r.P, k, r.checks)


def kaart7(r: k7_zon.Resultaat, p, tag) -> None:
    k = kleur(7)
    _kop(7)
    _formule("Profiel = opgesteld vermogen × opbrengst per kWp op deze dag × verloop over de dag (negatief: opwek)",
             "P[t] = 4 × N × E × v[t], Σ v = −1")
    stap(1, "Opgesteld vermogen bij woningen", nl(r.N), "kWp",
         extra=[("huidig", f"{nl(r.n_huidig)} kWp"), ("groei", f"{nl(p['zon_groei'])} %")],
         tag=tag("buurten", "zon_groei"),
         uitleg=f"kWp bij woningen in de buurt × (1 + groei t.o.v. het huidige vermogen). Zon van bedrijven staat op "
                f"tab {kn(6)}.",
         bron="Zonnedakje (kWp bij woningen) · groei: invoer zijbalk")
    stap(2, "Opbrengst per kWp op deze dag", nl(r.E, 3), "kWh per kWp",
         lijn({"instraling": r.I}, [KLEUR[3]], "W/m²", fmt=",.0f"),
         extra=[("instraling deze dag", f"{nl(r.i_ref, 2)} kWh/m²"),
                ("ten opzichte van een gemiddelde dag", f"{nl(r.i_ref * 365 / p['i_jaar'], 2)} ×"),
                ("performance ratio", nl(r.E / r.i_ref, 2) if r.i_ref else "–")],
         tag=tag("I", "zon_opbrengst", "i_jaar"),
         uitleg="Jaaropbrengst per kWp × instraling van deze dag ÷ instraling per jaar (KNMI, horizontaal vlak). "
                "kWp en jaaropbrengst komen zoveel mogelijk uit Zonnedakje.",
         bron="Zonnedakje (jaaropbrengst per kWp) · KNMI station 215 (instraling 18-02-2025)")
    stap(3, "Verloop over de dag", _hoogste(r.v), "meeste opwek",
         lijn({"opwek": _pct(r.v)}, [k], VERLOOP, fmt=".2f"),
         extra=[("grootste opwek", f"{nl(_piek_per_eenheid(r.E, r.v), 2)} kW per kWp")], tag=tag("I"),
         uitleg="Volgt de gemeten instraling per uur; negatief omdat het opwek is.",
         bron="KNMI station 215 (instraling per uur, 18-02-2025)")
    p_en_checks(4, r.P, k, r.checks)


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
         bron="Klimaatmonitor (verbruik per sector, gemeente) · BAG gebruiksoppervlak (verdeling naar buurt) · groei: invoer zijbalk")
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
         extra=[("batterijen", f"{nl(r.batterijen)} ({nl(p['bat_adoptie'])} % van de woningen)"),
                ("capaciteit", f"{nl(p['bat_kwh'], 1)} kWh per batterij")],
         tag=tag("buurten", "bat_adoptie", "bat_kwh"),
         uitleg="Woningen × aandeel woningen met een batterij (% van alle woningen) × capaciteit per batterij.",
         bron="Klimaatmonitor (woningen) · aandeel woningen met batterij en capaciteit: invoer zijbalk")
    stap(2, "Geen eigen verbruik", None,
         uitleg="Een batterij verschuift energie in de tijd en verbruikt netto alleen zijn verliezen. Daarom is er "
                "geen verbruik per stuk zoals op de andere tabs.")
    overschot = float(np.clip(r.pv - r.last, 0, None).sum() / 4)
    stap(3, "Verbruik en zon van een woning met batterij", nl(overschot, 2), "kWh zonoverschot op deze dag",
         lijn({f"verbruik (tab {kn(1)})": r.last, f"zon (tab {kn(7)})": r.pv}, [KLEUR[0], KLEUR[3]], "kW", fmt=".2f"),
         extra=[("zonnepanelen per batterijwoning", f"{nl(p['bat_kwp_woning'], 1)} kWp")],
         tag=tag("nedu_e1a", "I", "bat_kwp_woning"),
         uitleg=f"Gemiddelde woning uit tab {kn(1)} met de zon van één batterijwoning uit tab {kn(7)}. Alleen het "
                "overschot kan de batterij met zelfconsumptie laden.",
         bron=f"tab {kn(1)} (verbruik per woning) · tab {kn(7)} (zon per kWp) · zonnepanelen per batterijwoning: invoer zijbalk")
    stap(4, "Day-ahead prijs", f"{int(r.goedkoop.sum())}", "goedkoopste en duurste kwartieren",
         lijn({"prijs": r.prijs}, [KLEUR[1]], "€/MWh", fmt=",.0f"), tag=tag("prijs"),
         extra=[("laden rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.goedkoop)[:3]) + " …"),
                ("ontladen rond", ", ".join(TIJD[i] for i in np.flatnonzero(r.duur)[:3]) + " …")],
         uitleg="Alleen voor zelfconsumptie + day-ahead: laden in de goedkoopste en ontladen in de duurste "
                "kwartieren; zoveel kwartieren als nodig om vol of leeg te gaan.",
         bron="day-ahead prijs Nederland, 18-02-2025 (bron nog te kiezen)")
    stap(5, "Laden en ontladen per kWh batterij", r.modus, "gebruikt (keuze in de zijbalk)",
         lijn({m: md.v for m, md in r.modi.items()}, [KLEUR[0], KLEUR[1]], "kW per kWh", fmt=".3f"),
         extra=[(m, f"verlies {nl(md.v.sum() / 4, 3)} kWh per kWh batterij") for m, md in r.modi.items()],
         tag=tag("bat_c", "bat_eta", "prijs"),
         uitleg="Zelfconsumptie: laden bij zonoverschot, ontladen bij tekort. Plus day-ahead: daarnaast laden uit het "
                "net in goedkope kwartieren en ontladen in dure. Positief is laden; de batterij eindigt de dag zo vol "
                "als hij begon (v).",
         bron="stap 3 en 4 · vermogen en rendement: invoer zijbalk")
    stap(6, "Laadtoestand", None,
         fig=lijn({m: md.soc * 100 for m, md in r.modi.items()}, [KLEUR[0], KLEUR[1]], "% vol", fmt=".0f"),
         tag=tag("bat_c", "bat_eta", "prijs"), uitleg="Hoe vol de batterij is over de dag.",
         bron="stap 5")
    p_en_checks(7, r.P, k, r.checks)
