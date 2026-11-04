"""Kaartnamen en weergavevolgorde. Intern blijft het bordnummer (k1 tot k8); de UI nummert van eenvoudig naar complex."""
from ui.charts import KLEUR

KAARTEN = {1: "Woningen basis", 2: "Elektrisch koken", 3: "Warmtepomp", 4: "Laden personenauto's",
           5: "Laden logistiek", 6: "MKB en grootverbruik", 7: "Zonne-opwek", 8: "Thuisbatterij"}
VOLGORDE = [2, 1, 4, 8, 3, 7, 5, 6]  # volgorde van de tabs (bordnummers); de UI nummert van links naar rechts
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
VASTGESTELD = {k: True for k in VOLGORDE[:6]}  # tab 1 tot en met 6: koken, woningen, laden, batterij, warmtepomp, zon


def meta(kaart: int) -> tuple[str, str]:
    """Korte regels 'Invoer' en 'Bronnen' bovenaan een tab. Bronnen gelden ook waar nu mockdata staat."""
    t = kn
    return {
        2: ("huishoudens per buurt · extra aandeel elektrisch koken · kookenergie per huishouden · verloop koken",
            "Klimaatmonitor (huishoudens) · kookverloop en kookenergie: open (Liander/BAT, monitoring aardgasvrije "
            "wijken, TNO, Milieu Centraal)"),
        5: ("bestelauto's en trucks per buurt · elektrificatie en groei logistiek · laadenergie per voertuigtype · "
            "laadverloop per voertuigtype",
            "CBS 85239NED (bestelauto's Zuid-Holland, via bedrijfsvestigingen naar buurt) · laadprofiel ElaadNL "
            "(te bevestigen) · laadenergie: open"),
        4: ("extra EV's per buurt (aantal; alleen de toename) · aandeel slim laden · laadenergie per auto · "
            "laadverloop ongestuurd en slim",
            "invoer zijbalk · ElaadNL gemeten "
            "aggregaat (dataset open)"),
        7: ("resterende dakpotentie zon per buurt (alle daken) · benutting in % (alleen de toename) · instraling op deze "
            "dag en per jaar",
            "Zonnedakje (resterende dakpotentie) · KNMI station 215 (instraling)"),
        6: (f"jaarverbruik per sector per buurt · groei niet-huishoudelijk · sectorprofielen · verloop opwek gelijk "
            f"aan tab {t(7)}",
            "Klimaatmonitor (verbruik per sector, 36 GWh in 2024) · BAG gebruiksoppervlak (naar buurt) · sectorprofielen: "
            "keuze Liander open data (per sector) of NEDU standaardprofielen elektriciteit 2025 (E3)"),
        3: ("woningen per buurt · aandeel woningen met nu al een warmtepomp (alleen de toename telt hier) · gasverbruik "
            "per woning · warmteoplossing en isolatie per buurt · graaddagen · verloop · COP · "
            "temperatuur en pompvermogen warmtenet · opwek MT (restwarmte of elektrisch in de buurt)",
            "Klimaatmonitor (gas per woningtype, woningen) · KNMI station 215 (graaddagen 2025) · "
            "buitentemperatuur: aanname −10 °C · verloop: vlak tot gemeten aggregaatprofiel warmtepompen (mock) · "
            "COP: open"),
        1: (f"woningen en netto verbruik per woningtype · NEDU-profiel · jaaropwek huidige zon bij woningen en opwek "
            f"op deze dag (rekenwijze tab {t(7)}) · huidige warmtepompen en EV's zitten in het netto verbruik",
            "CBS (woningen per woningtype per buurt) · Klimaatmonitor (netto levering per woningtype, 2025) · NEDU "
            "standaardprofielen elektriciteit 2025 (E1A_AZI_A) · Zonnedakje (jaaropwek zon bij woningen) · KNMI station 215 "
            "(instraling)"),
        8: (f"woningen · adoptiegraad · capaciteit en vermogen per batterij · rendement · batterijmodus · uit tab {t(1)}: "
            f"last per woning · uit tab {t(7)}: zon per kWp · day-ahead prijs",
            "open (Essent batterijwaardering, literatuur, NL Flex) · day-ahead prijs: mock"),
        9: (f"profielen uit tab {t(2)}, {t(4)}, {t(7)}, {t(6)}, {t(3)}, {t(1)} en {t(8)} (zonder tab {t(5)})",
            "geen eigen bronnen"),
    }[kaart]
