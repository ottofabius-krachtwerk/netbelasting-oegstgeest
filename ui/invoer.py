"""Invoervelden in de zijbalk, met hun standaardwaarden. Data en aannames staan in parameters.csv en buurten.csv.

ALGEMEEN geldt voor alle buurten samen, PER_BUURT krijgt per buurt een eigen veld (met dezelfde standaardwaarde).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Veld:
    kaart: int  # bordnummer van de tab waar het veld bij hoort
    label: str
    eenheid: str
    standaard: float
    min: float
    max: float
    stap: float
    uitleg: str = ""


ALGEMEEN = {
    "koken_penetratie_groei": Veld(2, "Extra huishoudens met elektrisch koken",
                                   "% van alle huishoudens in de buurt, bovenop het huidige aandeel", 0, 0, 100, 1),
    "t_net_zlt": Veld(3, "Temperatuur ZLT-warmtenet", "°C watertemperatuur van het net", 25, 5, 45, 1,
                      "Projectaanname: bron levert 25 °C"),
    "mt_gas_pct": Veld(3, "Piek- en backupvoorziening (gas)", "% van de piekvraag warmte van het MT-net", 0, 0, 100, 5),
    "pomp_w_woning": Veld(3, "Pompvermogen warmtenet", "W per aangesloten woning; constant", 100, 0, 500, 5,
                         "Voorlopige aanname van 100 W; wordt nog geverifieerd (bron open)"),
    "publiek_aandeel": Veld(4, "Aandeel publiek laden", "% van de laadenergie in de buurt; de rest laadt thuis",
                            40, 0, 100, 5, "Standaard 40 % is een aanname (bron open)"),
    "slim_thuis": Veld(4, "Aandeel slim laden thuis", "% van de laadenergie thuis", 0, 0, 100, 5),
    "slim_publiek": Veld(4, "Aandeel slim laden publiek", "% van de laadenergie bij publieke laadpunten", 0, 0, 100, 5),
    "groei_niet_huish": Veld(6, "Groei verbruik niet-huishoudelijk gemeente",
                             "MWh per jaar, bovenop het huidige verbruik; gelijk verdeeld over de buurten",
                             0, -20000, 100000, 100),
    "bat_adoptie": Veld(8, "Woningen met thuisbatterij", "% van alle woningen in de buurt", 10, 0, 100, 1),
}

PER_BUURT = {
    "wp_aandeel_huidig": Veld(3, "Woningen met nu al een warmtepomp",
                              "% van alle woningen; die gaan niet nog eens over", 0, 0, 100, 1),
    "isolatie_reductie": Veld(3, "Isolatie", "% minder warmtevraag per woning dan nu", 0, 0, 80, 1),
    "log_bestel_extra": Veld(5, "Extra e-bestelbussen", "aantal dat in de buurt laadt", 0, 0, 10000, 1),
    "log_truck_extra": Veld(5, "Extra e-trucks", "aantal dat in de buurt laadt", 0, 0, 10000, 1),
    "zon_benutting_pct": Veld(7, "Extra zon", "% van de resterende dakpotentie, alle daken in de buurt", 0, 0, 50, 1),
}
WARMTEOPLOSSING = "geen"  # standaard per buurt in zichtjaar 2025
EV_SCENARIO = "middel"  # standaard prognose voor het aantal EV's (laag, middel of hoog), voor alle buurten
JAREN = (2025, 2035, 2050)
JAAR = JAREN[0]  # standaard zichtjaar

# Standaardwaarden per zichtjaar: bij het kiezen van een zichtjaar staan deze velden op de waarde van dat jaar. Eigen
# wijzigingen vervallen bij een jaarwissel (het jaar zit in de sleutel van het veld). Velden die hier niet staan, hebben
# in alle jaren de standaardwaarde van het Veld zelf. 2025 is de huidige situatie.
# LET OP: de waarden voor 2035 en 2050 zijn voorlopige aannames (nog te onderbouwen en met Otto af te stemmen).
STANDAARD_PER_JAAR = {
    "koken_penetratie_groei": {2025: 0, 2035: 25, 2050: 75},
    "slim_thuis": {2025: 0, 2035: 25, 2050: 50},
    "slim_publiek": {2025: 0, 2035: 25, 2050: 50},
    "groei_niet_huish": {2025: 0, 2035: 3600, 2050: 7200},  # MWh per jaar; ruim 10 en 20 % van 36 GWh
    "bat_adoptie": {2025: 10, 2035: 20, 2050: 35},
    "isolatie_reductie": {2025: 0, 2035: 10, 2050: 20},
    "log_bestel_extra": {2025: 0, 2035: 10, 2050: 30},
    "log_truck_extra": {2025: 0, 2035: 2, 2050: 8},
    "zon_benutting_pct": {2025: 0, 2035: 20, 2050: 40},
}
# De warmteoplossing wisselt bewust niet mee met het zichtjaar (blijft de eigen keuze per buurt).


def standaard(naam: str, veld: Veld, jaar: int) -> float:
    """Standaardwaarde van een invoerveld in het gekozen zichtjaar."""
    return float(STANDAARD_PER_JAAR.get(naam, {}).get(jaar, veld.standaard))


NAMEN = set(ALGEMEEN) | set(PER_BUURT) | {"warmteoplossing", "pomp_kw_buurt", "ev_scenario"}  # geen data: telt niet mee in de status
