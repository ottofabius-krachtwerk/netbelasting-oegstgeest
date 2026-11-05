"""Kaartnamen en weergavevolgorde. Intern blijft het bordnummer (k1 tot k8); de UI nummert van eenvoudig naar complex."""
from ui.charts import KLEUR

KAARTEN = {1: "Woningen basis", 2: "Elektrisch koken", 3: "Warmtepomp", 4: "Laden personenauto's",
           5: "Laden logistiek", 6: "MKB en grootverbruik", 7: "Zonne-opwek", 8: "Thuisbatterij"}
VOLGORDE = [2, 1, 4, 8, 3, 7, 5, 6]  # volgorde van de tabs (bordnummers); de UI nummert van links naar rechts
# Tabs met een rode titel (bordnummers): woningen basis, warmtepomp, laden personenauto's, laden logistiek, MKB, zon
ROOD = {1, 3, 4, 5, 6, 7}
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


def meta(kaart: int) -> tuple[str, str]:
    """Korte regels 'Invoer' en 'Bronnen' bovenaan een tab. Bronnen gelden ook waar nu mockdata staat."""
    t = kn
    return {
        2: ("huishoudens per buurt · extra aandeel elektrisch koken · kookenergie per huishouden · verloop koken",
            "Klimaatmonitor (huishoudens) · kookenergie: ECN 2014 en Milieu Centraal · kookverloop: RAMP-kookprofielen NL "
            "(2022), middagpiek verlaagd (aanname)"),
        5: ("extra e-bestelbussen en e-trucks per buurt (aantal; alleen de toename) · laadenergie per voertuigtype · "
            "laadprofiel per voertuigtype",
            "invoer zijbalk · laadprofiel: vlak (aanname) · laadenergie: aanname, bron open"),
        4: ("prognose aantal EV's per buurt (scenario laag, middel of hoog; totaal) · aandeel publiek laden · aandeel slim laden thuis en "
            "publiek · laadenergie per auto · laadverloop en spreiding per laadpunt, thuis en publiek, standaard en slim",
            "invoer zijbalk · ElaadNL gegenereerde laadpuntprofielen 2025 · slim thuis: aanname"),
        7: ("resterende dakpotentie zon per buurt (alle daken) · benutting in % (alleen de toename) · instraling op deze "
            "dag en per jaar",
            "Zonnedakje (resterende dakpotentie) · KNMI station 215 (instraling)"),
        6: (f"verbruik per bedrijfstak (gemeente) · aantal buurten · werkdagen · groei niet-huishoudelijk (MWh per jaar) · "
            f"zon op overige daken, verloop gelijk aan tab {t(7)}",
            "Klimaatmonitor (elektriciteitsverbruik per bedrijfstak, 36 GWh in 2024) · CBS wijk- en buurtkaart 2025 · "
            "Zonnedakje (overige daken) · verloop verbruik: vlak, alleen werkdagen (aanname)"),
        3: ("woningen per buurt · aandeel woningen met nu al een warmtepomp (alleen de toename telt hier) · gasverbruik "
            "per woning · warmteoplossing en isolatie per buurt · graaddagen · verloop · COP · "
            "temperatuur en pompvermogen warmtenet · warmtebron MT-net (aquathermie TEO/TEA, ondiepe geothermie, of buiten "
            "beschouwing) · aandeel gasgestuurde piek- en backupvoorziening",
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
            "open (Essent batterijwaardering, literatuur, NL Flex) · day-ahead prijs: EPEX NL, gemiddelde 5 koudste "
            "werkdagen winter 2025/26 (Energy Quantified)"),
        9: ("profielen uit alle tabs (1 tot en met 8)",
            "geen eigen bronnen"),
    }[kaart]
