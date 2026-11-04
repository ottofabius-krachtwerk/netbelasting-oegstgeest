"""Eén Plotly-stijl voor alle tabs."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# Categorische volgorde (gevalideerd palet); kaart k krijgt slot k.
KLEUR = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INKT, INKT2, MUTED, GRID, AS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

UUR = np.arange(96) / 4
TIJD = [f"{i // 4:02d}:{(i % 4) * 15:02d}" for i in range(96)]
H_KLEIN, H_GROOT = 170, 300


def _opmaak(fig: go.Figure, hoogte: int, eenheid: str = "", tijdas: bool = True, legenda: bool = False) -> go.Figure:
    fig.update_layout(
        height=hoogte, margin=dict(l=4, r=4, t=4, b=4), separators=",.",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=11, color=INKT2),
        showlegend=legenda, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=10)),
        hoverlabel=dict(font=dict(family=FONT, size=11)), bargap=0.15,
    )
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AS, zerolinewidth=1, tickfont=dict(color=MUTED),
                     title=dict(text=eenheid, font=dict(size=10, color=MUTED)), ticksuffix=" ")
    fig.update_xaxes(showgrid=False, linecolor=AS, tickfont=dict(color=MUTED))
    if tijdas:
        fig.update_xaxes(range=[0, 24], tickvals=list(range(0, 25, 6)),
                         ticktext=[f"{u:02d}:00" for u in range(0, 25, 6)])
        fig.update_layout(hovermode="x unified")
    return fig


def lijn(reeksen: dict, kleuren=None, eenheid: str = "", hoogte: int = H_KLEIN, fmt: str = ".4f",
         vlak: bool = False, tickformat: str | None = None, hlijn: tuple[float, str] | None = None) -> go.Figure:
    kleuren = kleuren or KLEUR
    fig = go.Figure()
    for i, (naam, y) in enumerate(reeksen.items()):
        k = kleuren[i % len(kleuren)]
        fig.add_scatter(x=UUR, y=np.asarray(y), name=naam, mode="lines", line=dict(color=k, width=2, shape="hv"),
                        fill="tozeroy" if vlak else None, fillcolor=k + "26", customdata=TIJD,
                        hovertemplate=f"%{{y:{fmt}}}<extra>{naam}</extra>")
    if hlijn:
        fig.add_hline(y=hlijn[0], line=dict(color=MUTED, width=1, dash="dot"),
                      annotation=dict(text=hlijn[1], font=dict(size=10, color=MUTED)), annotation_position="top left")
    fig = _opmaak(fig, hoogte, eenheid, legenda=len(reeksen) > 1)
    if tickformat:
        fig.update_yaxes(tickformat=tickformat)
    return fig


def balans(verbruik, opwek, netto, kleuren, eenheid: str = "kW", hoogte: int = H_GROOT,
           namen=("verbruik", "opwek", "netto")) -> go.Figure:
    """Verbruik (vlak boven 0) en opwek (vlak onder 0) in één figuur, met het netto profiel als dikke lijn."""
    fig = go.Figure()
    for naam, y, k, vlak in zip(namen, (verbruik, opwek, netto), kleuren, (True, True, False)):
        fig.add_scatter(x=UUR, y=np.asarray(y), name=naam, mode="lines", customdata=TIJD,
                        line=dict(color=k, width=1 if vlak else 2.5, shape="hv"),
                        fill="tozeroy" if vlak else None, fillcolor=k + "40",
                        hovertemplate=f"%{{y:,.0f}} {eenheid}<extra>{naam}</extra>")
    return _opmaak(fig, hoogte, eenheid, legenda=True)


def staven(labels, waarden, kleur=KLEUR[0], eenheid: str = "", hoogte: int = H_KLEIN, fmt: str = ",.0f",
           kleuren=None) -> go.Figure:
    fig = go.Figure(go.Bar(y=list(labels), x=list(waarden), orientation="h", marker_color=kleuren or kleur,
                           hovertemplate=f"%{{x:{fmt}}} {eenheid}<extra>%{{y}}</extra>"))
    fig = _opmaak(fig, hoogte, tijdas=False)
    fig.update_xaxes(title=dict(text=eenheid, font=dict(size=10, color=MUTED)), showgrid=True, gridcolor=GRID)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)", title=None, tickmode="array",
                     tickvals=list(labels), ticktext=list(labels))
    return fig


def waterval(labels, waarden, maten, eenheid: str = "", hoogte: int = H_KLEIN) -> go.Figure:
    fig = go.Figure(go.Waterfall(
        x=list(labels), y=list(waarden), measure=list(maten),
        increasing=dict(marker=dict(color=KLEUR[0])), decreasing=dict(marker=dict(color=KLEUR[7])),
        totals=dict(marker=dict(color=INKT2)), connector=dict(line=dict(color=AS, width=1)),
        hovertemplate=f"%{{y:,.0f}} {eenheid}<extra>%{{x}}</extra>"))
    fig = _opmaak(fig, hoogte, eenheid, tijdas=False)
    fig.update_xaxes(tickangle=0, tickfont=dict(size=10))
    return fig


def gestapeld(reeksen: dict, kleuren, eenheid: str = "kW", hoogte: int = H_GROOT, totaal=None) -> go.Figure:
    fig = go.Figure()
    for (naam, y), k in zip(reeksen.items(), kleuren):
        fig.add_bar(x=UUR + 0.125, y=np.asarray(y), name=naam, marker_color=k, width=0.25,
                    hovertemplate=f"%{{y:,.0f}} {eenheid}<extra>{naam}</extra>")
    if totaal is not None:
        fig.add_scatter(x=UUR + 0.125, y=np.asarray(totaal), name="Totaal", mode="lines",
                        line=dict(color=INKT, width=2), hovertemplate=f"%{{y:,.0f}} {eenheid}<extra>Totaal</extra>")
    fig.update_layout(barmode="relative", bargap=0)
    return _opmaak(fig, hoogte, eenheid, legenda=True)


def toon(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
