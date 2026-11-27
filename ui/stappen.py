"""Bouwstenen per tab: stapkaart, P[t] en de checks."""
import numpy as np
import streamlit as st

from model.common import Check, nl
from ui.charts import H_GROOT, TIJD, lijn, toon
from ui.kaarten import BRON_LINKS

# Compacte weergave: per tab alleen de bronnen en de grafieken; uitleg, rekenregels, checks en vaste waarden vallen weg.
# De invoer in de zijbalk blijft gelijk.
COMPACT = True


def _bronregel(bron: str) -> str:
    return (f"<div style='font-size:.74rem;color:#898781;line-height:1.3;margin:.1rem 0 .2rem'><b>Bron</b> {bron}</div>"
            if bron else "")


def _grafiek(titel: str, fig, bron: str = "", tag: str = "") -> None:
    """Compact: titel, grafiek en bron in één kader."""
    with st.container(border=True):
        st.markdown(f"<div style='font-weight:600'>{titel}{badge(tag)}</div>{_bronregel(bron)}", unsafe_allow_html=True)
        toon(fig)


def kerncijfers(rij: list[tuple[str, str, str]]) -> None:
    """Compact: een rij met de belangrijkste getallen van de tab (label, waarde, eenheid)."""
    if not COMPACT or not rij:
        return
    for kol, (label, waarde, eenheid) in zip(st.columns(len(rij)), rij):
        kol.metric(label, f"{waarde} {eenheid}".strip(), border=True)


LABEL = {"mock": ("mock", "#52514e", "#f0efec"), "placeholder": ("placeholder", "#8a4b00", "#fdeccc")}


def badge(status: str) -> str:
    if status not in LABEL:
        return ""
    tekst, kleur, achter = LABEL[status]
    return (f"<span style='font-size:.68rem;font-weight:500;color:{kleur};background:{achter};"
            f"border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:1px'>{tekst}</span>")


def stap(nr: int, titel: str, waarde: str | None = None, eenheid: str = "", fig=None,
         extra: list[tuple[str, str]] | None = None, tag: str = "bron", uitleg: str = "", bron: str = "",
         reken: list[str] | None = None, noot: str = "", kern: bool = False) -> None:
    """Eén rekenstap als rij: links titel, uitleg, rekenregels en resultaat, rechts een kleine grafiek.

    Compact: alleen de grafiek, en alleen bij een kernstap (kern=True)."""
    if COMPACT:
        if kern and fig is not None:
            _grafiek(titel, fig, bron, tag)
        return
    with st.container(border=True):
        links, rechts = st.columns([1, 1.6], vertical_alignment="center") if fig is not None else (st.container(), None)
        with links:
            regels = [f"<div style='font-weight:600'>{nr} · {titel}{badge(tag)}</div>"]
            if uitleg:
                regels.append(f"<div style='font-size:.82rem;color:#52514e;line-height:1.35;margin:.2rem 0 .2rem'>"
                              f"{uitleg}</div>")
            if bron:
                regels.append(f"<div style='font-size:.74rem;color:#898781;line-height:1.3;margin:0 0 .35rem'>"
                              f"<b>Bron</b> {bron}</div>")
            if noot:
                regels.append(f"<div style='font-size:.74rem;color:#8a4b00;line-height:1.35;margin:0 0 .35rem'>"
                              f"<b>Nog uitwerken</b> {noot}</div>")
            if waarde is not None:
                regels.append(f"<div style='font-size:1.35rem;font-weight:600;line-height:1.25'>{waarde} "
                              f"<span style='font-size:.8rem;font-weight:400;color:#52514e'>{eenheid}</span></div>")
            nevens = " · ".join(f"{label} <b>{w}</b>" if w else label for label, w in extra or [])
            if nevens:
                regels.append(f"<div style='font-size:.8rem;color:#52514e'>{nevens}</div>")
            regels.append(rekenregels(reken))
            st.markdown("".join(regels), unsafe_allow_html=True)
        if rechts is not None:
            with rechts:
                toon(fig)


def rekenregels(reken: list[str] | None) -> str:
    """Berekening met de ingevulde getallen, één regel per som, zodat elke stap na te rekenen is."""
    if not reken:
        return ""
    return ("<div style='font-family:ui-monospace,Menlo,monospace;font-size:.78rem;color:#0b0b0b;"
            "background:#f0efec;border-radius:4px;padding:.35rem .5rem;margin:.4rem 0 .5rem;line-height:1.55'>"
            + "<br>".join(reken) + "</div>")


def p_en_checks(nr: int, P, kleur: str, checks: list[Check], naam: str = "Profiel over de dag", fig=None,
                reken: list[str] | None = None, noot: str = "", eenheid: str = "kW", dec: int = 0,
                compact: bool = True) -> None:
    """Profiel en checks. Compact: alleen het profiel, en niet als een kernstap hetzelfde profiel al toont."""
    if COMPACT:
        if compact:
            _grafiek(naam, fig if fig is not None else lijn({"profiel": P}, [kleur], eenheid, H_GROOT, fmt=",.1f", vlak=True))
        return
    links, rechts = st.columns([1.7, 1])
    i_max, i_min = int(np.argmax(P)), int(np.argmin(P))
    with links, st.container(border=True):
        kern = (f"constant <b>{nl(P[0], dec)} {eenheid}</b>" if np.ptp(P) < 1e-9 else
                f"max <b>{nl(P[i_max], dec)} {eenheid}</b> om {TIJD[i_max]} · min <b>{nl(P[i_min], dec)} {eenheid}</b> "
                f"om {TIJD[i_min]}")
        st.markdown(f"**{nr} · {naam}** <span style='color:#52514e;font-size:.85rem;margin-left:.5rem'>{kern}</span>",
                    unsafe_allow_html=True)
        toon(fig if fig is not None else lijn({"profiel": P}, [kleur], eenheid, H_GROOT, fmt=",.1f", vlak=True))
        if reken:
            st.markdown(rekenregels(reken), unsafe_allow_html=True)
    with rechts, st.container(border=True):
        st.markdown(f"**{nr + 1} · Checks**")
        checktabel(checks)


def _met_links(bron: str) -> str:
    """Maak van de bronnaam een link (nieuw tabblad) als er een link voor is (BRON_LINKS in ui/kaarten.py)."""
    for als, tekst, url in BRON_LINKS:
        if als in bron and tekst in bron:
            bron = bron.replace(tekst, f"<a href='{url}' target='_blank'>{tekst}</a>", 1)
    return bron


def kop(invoer: str, bronnen: str, extra: str = "") -> None:
    """Bovenaan een tab: invoer en bronnen. De status van de methodiek staat in de kleur van de tabtitel."""
    eerste = f"{extra}<br>" if extra and bronnen else extra
    # bronnen onder elkaar: één regel per bron (in meta gescheiden door " · ")
    lijst = ("<ul style='margin:.1rem 0 0 1rem;padding:0'>"
             + "".join(f"<li>{_met_links(x)}</li>" for x in bronnen.split(" · ")) + "</ul>")
    invoerregel = "" if COMPACT else f"<b>Invoer</b> {invoer}<br>"
    bronregel = f"<b>Bronnen</b>{lijst}" if bronnen else ""  # zonder eigen bronnen geen kopje
    st.markdown(f"<div style='margin:-.2rem 0 .7rem;font-size:.82rem;color:#52514e;line-height:1.5'>{eerste}"
                f"{invoerregel}{bronregel}</div>", unsafe_allow_html=True)


def banner(status: str, tekst: str) -> None:
    st.markdown(f"{badge(status)} <span style='color:#52514e;font-size:.85rem'>{tekst}</span>",
                unsafe_allow_html=True)


def checktabel(checks: list[Check]) -> None:
    rijen = "".join(
        f"<tr><td>{c.naam}</td><td class='r'>{c.waarde}</td><td class='r'>{c.norm}</td>"
        f"<td class='{'ok' if c.ok else 'fout'}'>{'✓ ok' if c.ok else '✗ fout'}</td></tr>" for c in checks)
    st.markdown(
        "<style>.chk{width:100%;border-collapse:collapse;font-size:.78rem}"
        ".chk th{color:#898781;font-weight:500;text-align:left;border-bottom:1px solid #c3c2b7;padding:3px 4px}"
        ".chk td{border-bottom:1px solid #e1e0d9;padding:4px;vertical-align:top}"
        ".chk .r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}"
        ".chk .ok{color:#006300;white-space:nowrap}.chk .fout{color:#d03b3b;font-weight:600;white-space:nowrap}</style>"
        f"<table class='chk'><tr><th>Check</th><th class='r'>Waarde</th><th class='r'>Norm</th><th></th></tr>"
        f"{rijen}</table>", unsafe_allow_html=True)
    n = sum(c.ok for c in checks)
    st.caption(f"{n} van {len(checks)} geslaagd")


def open_punten(punten: list[str]) -> None:
    """Korte lijst met openstaande punten onderaan een tab."""
    if not punten:
        return
    regels = "".join(f"<li>{x}</li>" for x in punten)
    with st.container(border=True):
        st.markdown("<div style='font-weight:600;color:#8a4b00'>Openstaande punten</div>"
                    "<ul style='font-size:.8rem;color:#52514e;margin:.2rem 0 0 1rem;padding:0;line-height:1.45'>"
                    f"{regels}</ul>", unsafe_allow_html=True)
