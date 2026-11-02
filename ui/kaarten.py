"""Kaartnamen en weergavevolgorde. Intern blijft het bordnummer (k1 tot k8); de UI nummert van eenvoudig naar complex."""
from ui.charts import KLEUR

KAARTEN = {1: "Woningen basis", 2: "Elektrisch koken", 3: "Warmtepomp", 4: "Laden personenauto's",
           5: "Laden logistiek", 6: "MKB en grootverbruik", 7: "Zonne-opwek", 8: "Thuisbatterij"}
VOLGORDE = [2, 5, 4, 7, 6, 3, 1, 8]  # van eenvoudig (dagwaarde, geen afhankelijkheden) naar complex
NR = {kaart: i + 1 for i, kaart in enumerate(VOLGORDE)}
NR_STAPELING = len(VOLGORDE) + 1


def kn(kaart: int) -> int:
    """Weergavenummer van een kaart."""
    return NR[kaart]


def kaartnaam(kaart: int) -> str:
    return f"{kn(kaart)} {KAARTEN[kaart]}"


def kleur(kaart: int) -> str:
    """Vaste kleur per kaart, in categorische volgorde van de tabs."""
    return KLEUR[kn(kaart) - 1]


# Methodiek vastgesteld (True) of open (False), per kaart. Stapeling = 9.
VASTGESTELD = {2: True}


def meta(kaart: int) -> tuple[str, str]:
    """Korte regels 'Invoer' en 'Bronnen' bovenaan een tab. Bronnen gelden ook waar nu mockdata staat."""
    t = kn
    return {
        2: ("huishoudens per buurt · groei penetratie elektrisch koken · dagenergie koken · kookprofiel",
            "Klimaatmonitor (huishoudens) · kookprofiel en dagenergie: open (Liander/BAT, monitoring aardgasvrije "
            "wijken, TNO, Milieu Centraal)"),
        5: ("bestelauto's en trucks per buurt · elektrificatie en groei logistiek · dagenergie per voertuigtype · "
            "laadprofiel per voertuigtype",
            "CBS 85239NED (bestelauto's Zuid-Holland, via bedrijfsvestigingen naar buurt) · laadprofiel ElaadNL "
            "(te bevestigen) · dagenergie: open"),
        4: ("personenauto's per buurt · huidige BEV gemeente · EV toename per buurt (% personenauto's) · aandeel slim laden · dagenergie per auto · "
            "laadprofielen ongestuurd en slim",
            "Klimaatmonitor (632 BEV, jan 2025) · CBS Kerncijfers wijken en buurten (personenauto's) · ElaadNL gemeten "
            "aggregaat (dataset open)"),
        7: ("kWp bij woningen per buurt · groei zonnepanelen · jaaropbrengst per kWp · instraling referentiedag en jaar",
            "Zonnedakje (kWp en jaaropbrengst; zoveel mogelijk deze bron) · controle CBS 85005NED · KNMI station 215 "
            "(instraling)"),
        6: (f"jaarverbruik per sector per buurt · groei niet-huishoudelijk · sectorprofielen · vorm opwek-sector gelijk "
            f"aan tab {t(7)}",
            "Klimaatmonitor (verbruik per sector, 36 GWh in 2024) · BAG gebruiksoppervlak (naar buurt) · sectorprofielen: "
            "keuze Liander open data (per sector) of NEDU standaardprofielen elektriciteit 2025 (E3)"),
        3: ("woningen per buurt · huidige warmtepompen gemeente · gasverbruik per woning · energielabels · warmteoplossing "
            f"en isolatie per buurt · graaddagen · vorm (vlak of G1A) · COP · levert energie huidige warmtepompen aan tab "
            f"{t(1)}",
            "Klimaatmonitor (gas per woningtype, warmtepompen, woningen) · Zonnedakje (energielabels) · KNMI station 215 "
            "(temperatuur, wind, graaddagen 2025) · "
            "vorm: bandbreedte vlak tot NEDU standaardprofielen aardgas 2025 (G1A, temperatuurafhankelijk deel); "
            "opwekprofiel warmtepomp in uitwerking · COP: open"),
        1: (f"woningen en netto verbruik per woningtype · NEDU-profiel · uit tab {t(7)}: bruto zonopwek huidig · "
            f"uit tab {t(3)}: energie huidige warmtepompen · uit tab {t(4)}: thuisladen huidige EV's",
            "CBS (woningen per woningtype per buurt) · Klimaatmonitor (netto levering per woningtype, 2025) · NEDU "
            "standaardprofielen elektriciteit 2025 (E1A_AZI_A)"),
        8: (f"woningen · adoptiegraad · capaciteit en vermogen per batterij · rendement · batterijmodus · uit tab {t(1)}: "
            f"last per woning · uit tab {t(7)}: zon per kWp · day-ahead prijs",
            "open (Essent batterijwaardering, literatuur, NL Flex) · day-ahead prijs: mock"),
        9: (f"P[t] uit tab {t(2)}, {t(4)}, {t(7)}, {t(6)}, {t(3)}, {t(1)} en {t(8)} (zonder tab {t(5)})",
            "geen eigen bronnen"),
    }[kaart]
