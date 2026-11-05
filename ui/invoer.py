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
    "pomp_w_woning": Veld(3, "Pompvermogen warmtenet", "W per aangesloten woning; constant", 50, 0, 500, 5),
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
WARMTEOPLOSSING = "geen"  # standaard per buurt
EV_SCENARIO = "middel"  # standaard prognose voor het aantal EV's (laag, middel of hoog), voor alle buurten
JAAR = 2025  # voorlopig vast; een keuze voor 2035 en 2050 volgt

NAMEN = set(ALGEMEEN) | set(PER_BUURT) | {"warmteoplossing", "pomp_kw_buurt", "ev_scenario"}  # geen data: telt niet mee in de status
