"""Bouwstenen per tab: stapkaart, P[t] en de checks."""
import numpy as np
import streamlit as st

from model.common import Check, nl
from ui.charts import H_GROOT, TIJD, lijn, toon



LABEL = {"mock": ("mock", "#52514e", "#f0efec"), "placeholder": ("placeholder", "#8a4b00", "#fdeccc")}


def badge(status: str) -> str:
    if status not in LABEL:
        return ""
    tekst, kleur, achter = LABEL[status]
    return (f"<span style='font-size:.68rem;font-weight:500;color:{kleur};background:{achter};"
            f"border-radius:4px;padding:1px 6px;margin-left:6px;vertical-align:1px'>{tekst}</span>")


def stap(nr: int, titel: str, waarde: str | None = None, eenheid: str = "", fig=None,
         extra: list[tuple[str, str]] | None = None, tag: str = "bron", uitleg: str = "", bron: str = "") -> None:
    """Eén rekenstap als rij: links titel, uitleg en resultaat, rechts een kleine grafiek."""
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
            if waarde is not None:
                regels.append(f"<div style='font-size:1.35rem;font-weight:600;line-height:1.25'>{waarde} "
                              f"<span style='font-size:.8rem;font-weight:400;color:#52514e'>{eenheid}</span></div>")
            nevens = " · ".join(f"{label} <b>{w}</b>" if w else label for label, w in extra or [])
            if nevens:
                regels.append(f"<div style='font-size:.8rem;color:#52514e'>{nevens}</div>")
            st.markdown("".join(regels), unsafe_allow_html=True)
        if rechts is not None:
            with rechts:
                toon(fig)


def p_en_checks(nr: int, P, kleur: str, checks: list[Check], naam: str = "Profiel over de dag", fig=None) -> None:
    links, rechts = st.columns([1.7, 1])
    i_max, i_min = int(np.argmax(P)), int(np.argmin(P))
    with links, st.container(border=True):
        kern = (f"constant <b>{nl(P[0])} kW</b>" if np.ptp(P) < 1e-9 else
                f"max <b>{nl(P[i_max])} kW</b> om {TIJD[i_max]} · min <b>{nl(P[i_min])} kW</b> om {TIJD[i_min]}")
        st.markdown(f"**{nr} · {naam}** <span style='color:#52514e;font-size:.85rem;margin-left:.5rem'>{kern}</span>",
                    unsafe_allow_html=True)
        toon(fig if fig is not None else lijn({"profiel": P}, [kleur], "kW", H_GROOT, fmt=",.1f", vlak=True))
    with rechts, st.container(border=True):
        st.markdown(f"**{nr + 1} · Checks**")
        checktabel(checks)


def kop(invoer: str, bronnen: str, extra: str = "") -> None:
    """Bovenaan een tab: invoer en bronnen. De status van de methodiek staat in de kleur van de tabtitel."""
    eerste = f"{extra}<br>" if extra else ""
    st.markdown(
        f"<div style='margin:-.2rem 0 .7rem;font-size:.82rem;color:#52514e;line-height:1.5'>{eerste}"
        f"<b>Invoer</b> {invoer}<br><b>Bronnen</b> {bronnen}</div>", unsafe_allow_html=True)


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
