"""Kaartnamen en weergavevolgorde. De tabs tonen het bordnummer (k1 tot k8, zoals op het whiteboard) in de volgorde van
VOLGORDE, gelijk aan het bordnummer."""
from ui.charts import KLEUR

KAARTEN = {1: "Woningen basis", 2: "Elektrisch koken", 3: "Warmteoplossing", 4: "Laden personenauto's",
           5: "Laden logistiek", 6: "MKB en grootverbruik", 7: "Zonne-opwek", 8: "Thuisbatterij"}
VOLGORDE = [1, 2, 3, 4, 5, 6, 7, 8]  # volgorde van de tabs, van links naar rechts (bordnummers)
# Tabs met een rode titel (bordnummers): woningen basis, warmteoplossing, laden personenauto's, laden logistiek, MKB, zon
ROOD = {1, 3, 4, 5, 6, 7}
POSITIE = {kaart: i + 1 for i, kaart in enumerate(VOLGORDE)}  # plek van links naar rechts, voor de kleuren
NR_STAPELING = 9  # stapeling is bord 9


def kn(kaart: int) -> int:
    """Nummer van een kaart zoals getoond in de tabtitel: het bordnummer."""
    return kaart


def kaartnaam(kaart: int) -> str:
    return f"{kn(kaart)} {KAARTEN[kaart]}"


def kleur(kaart: int) -> str:
    """Vaste kleur per kaart, in categorische volgorde van de tabs."""
    return KLEUR[POSITIE[kaart] - 1]


def meta(kaart: int) -> tuple[str, str]:
    """Korte regels 'Invoer' en 'Bronnen' bovenaan een tab. Bronnen gelden ook waar nu mockdata staat."""
    t = kn
    return {
        2: ("huishoudens per buurt · extra aandeel elektrisch koken · kookenergie per huishouden · verloop koken",
            "Klimaatmonitor (huishoudens) · kookenergie: ECN 2014 en Milieu Centraal · kookverloop: RAMP-kookprofielen NL "
            "(2022), middagpiek verlaagd (aanname)"),
        5: ("e-bestelbussen en e-trucks per buurt (prognose min 2025; alleen de toename) · laadenergie per voertuigtype · "
            "laadprofiel per voertuigtype",
            "invoer zijbalk · laadprofiel: vlak (aanname) · laadenergie: aanname, bron open"),
        4: ("prognose aantal EV's per buurt (scenario laag, middel of hoog; totaal) · aandeel publiek laden · aandeel slim laden thuis en "
            "publiek · laadenergie per auto · laadverloop en spreiding per laadpunt, thuis en publiek, standaard en slim",
            "invoer zijbalk · ElaadNL gegenereerde laadpuntprofielen 2025 · slim thuis: aanname"),
        7: ("jaaropwek huidige zon op woningen en niet-woningen (vaste basis) · resterende dakpotentie zon per buurt, "
            "woningen en niet-woningen · benutting in %, apart voor woningen en niet-woningen (extra) · instraling op "
            "deze dag en per jaar",
            "Zonnedakje (huidige opwek) · Bewerkte data per buurt 1-1-2025 (resterende dakpotentie) · KNMI station 215 "
            "(instraling)"),
        6: (f"verbruik per bedrijfstak (gemeente) · aantal buurten · werkdagen · groei niet-huishoudelijk (MWh per jaar) · "
            f"alleen verbruik; zon van bedrijven in tab {t(7)}",
            "Klimaatmonitor (elektriciteitsverbruik per bedrijfstak, 36 GWh in 2024) · CBS wijk- en buurtkaart 2025 · "
            "verloop verbruik: vlak, alleen werkdagen (aanname)"),
        3: ("woningen per buurt · aandeel woningen met nu al een warmtepomp (alleen de toename telt hier) · gasverbruik "
            "per woning · warmteoplossing en isolatie per buurt · graaddagen · verloop · COP · "
            "temperatuur en pompvermogen warmtenet · warmtebron ZLT-net (aquathermie TEO/TEA, ondiepe geothermie, of buiten "
            "de buurt) · warmteproductie MT-net (collectieve warmtepomp of buiten de buurt) · aandeel gasgestuurde "
            "piek- en backupvoorziening",
            "Klimaatmonitor (gas per woningtype, woningen) · KNMI station 215 (graaddagen 2025) · "
            "buitentemperatuur: aanname −10 °C · verloop: vlak (afgestemd met heatgeeks) · "
            "COP: open"),
        1: (f"woningen en netto verbruik per woningtype · jaaropwek huidige zon bij woningen (alleen voor netto naar "
            f"bruto; de opwek zelf staat in tab {t(7)}) · NEDU-profiel · huidige warmtepompen en EV's zitten in het netto "
            "verbruik",
            "CBS (woningen per woningtype per buurt) · Klimaatmonitor (netto levering per woningtype, 2025) · NEDU "
            "standaardprofielen elektriciteit 2025 (E1A_AZI_A) · Zonnedakje (jaaropwek zon bij woningen)"),
        8: (f"woningen · adoptiegraad · capaciteit en vermogen per batterij · rendement · batterijmodus · uit tab {t(1)}: "
            f"last per woning · uit tab {t(7)}: zon per kWp · day-ahead prijs",
            "open (Essent batterijwaardering, literatuur, NL Flex) · day-ahead prijs: EPEX NL, gemiddelde 5 koudste "
            "werkdagen winter 2025/26 (Energy Quantified)"),
        9: (f"profielen uit alle tabs (1 tot en met 8); verbruik min de opwek uit tab {t(7)} geeft het netto profiel",
            "geen eigen bronnen"),
    }[kaart]


# Openstaande punten per tab (bordnummer; 9 is stapeling), onderaan elke tab in beide weergaven. Kort en in gewone taal.
OPEN_PUNTEN = {
    1: ["Nagaan of de Klimaatmonitor het netto verbruik per woning op 0 afkapt (dan is het bruto verbruik te hoog)",
        "Aandeel woningen met warmtepomp of EV in de NEDU-steekproef (2021 tot 2023)",
        "Zelfde jaar voor zonopwek (Zonnedakje) en netto verbruik",
        "Gemengde panden in Zonnedakje: verdelen naar oppervlakte of toewijzen aan de grootste functie"],
    2: ["Verlaagde middagpiek (12,5 % van de dag) is een aanname",
        "Standaardwaarden voor 2035 en 2050 bevestigen"],
    3: ["COP's van all-electric, ZLT-booster, collectieve warmtepomp en bronwarmtepomp onderbouwen (bron open)",
        "Pompvermogen warmtenet (100 W per woning) verifiëren",
        "Warmtenetten: verloop nu constant, nog geen warmteverlies in het net",
        "Ontwerpdag met constant −10 °C is een aanname"],
    4: ["Laadenergie per auto per werkdag onderbouwen",
        "Aandeel publiek laden (40 %) is een aanname",
        "Aantal EV's in 2025: bronbestand en Klimaatmonitor verschillen",
        "Slim thuisladen (vlak van 01:00 tot 06:00) is een aanname"],
    5: ["Laadenergie per bestelbus (40 kWh) en per truck (150 kWh) zijn placeholders",
        "Laadprofielen per voertuigtype uit een bron halen"],
    6: ["Verdeling over de buurten is nu gelijk; verfijnen met CBS-wijkdata of BAG-gebruiksoppervlak",
        "Verwarming van niet-woningen nog uitwerken",
        "Verloop over de dag is vlak (aanname)"],
    7: ["Keuze ontwerpdag: zonnige echte dag of bewolkte dag",
        "Instraling per jaar naar KNMI (1.220 kWh/m²)",
        "Zonnedakje: potentie in kWh of kWp, en of 'resterend' de huidige panelen uitsluit"],
    8: ["Energiebelasting meenemen bij laden uit het net (groter dan het prijsverschil)",
        "Batterijparameters en adoptiegraad onderbouwen"],
    9: ["Spreiding (95 %-grens) nu alleen voor laden personenauto's",
        "Standaardwaarden voor 2035 en 2050 zijn voorlopig"],
}
