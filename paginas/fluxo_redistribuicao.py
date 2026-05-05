import pandas as pd

import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_fluxo_monjica, fig_vazia, tabela, obter_rota_osrm


def montar_mapa_fluxo(df):
    if df.empty:
        return fig_vazia("Sem fluxos", altura=600)

    df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"])

    if df.empty:
        return fig_vazia("Sem coordenadas válidas", altura=600)

    # 🔥 limitar para performance
    df = df.head(30)

    # 📍 centro (igual seu padrão)
    centro = {
        "LAT": df["lat_origem"].mean(),
        "LON": df["lon_origem"].mean()
    }

    # 🔵 ORIGEM (igual seu padrão)
    fig = px.scatter_mapbox(
        df,
        lat="lat_origem",
        lon="lon_origem",
        color_discrete_sequence=["#2563eb"],
        hover_name="origem",
        hover_data={
            "tipo_equipamento": True,
            "recomendacao": True,
            "lat_origem": False,
            "lon_origem": False,
        },
        zoom=8 if len(df) > 1 else 12,
        center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
        height=500,
    )

    # 🟢 DESTINO
    fig.add_trace(
        go.Scattermapbox(
            lat=df["lat_destino"],
            lon=df["lon_destino"],
            mode="markers",
            marker=dict(size=10, color="#16a34a"),
            name="Destino",
        )
    )

    # 🔥 ROTAS REAIS (Uber style)
    for _, row in df.iterrows():
        rota = obter_rota_osrm(
            row["lat_origem"],
            row["lon_origem"],
            row["lat_destino"],
            row["lon_destino"]
        )

        if rota[0] is None:
            continue

        lats, lons, dist, tempo = rota

        fig.add_trace(
            go.Scattermapbox(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=3, color="#dc2626"),
                opacity=0.6,
                hovertext=f"{row['origem']} → {row['destino']}<br>{dist:.1f} km | {tempo:.0f} min",
                hoverinfo="text",
                showlegend=False
            )
        )

    # 🎯 estilo igual seu mapa original
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",  # 🔥 mesmo estilo do seu
        ),
        margin=dict(l=10, r=10, t=10, b=10),
    )

    return fig



def layout():
    return html.Div(
        [
            html.H3("Fluxo de Redistribuição", style={"marginTop": "0"}),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Prioridade mínima", style={"fontWeight": "600"}),
                            dcc.Slider(
                                id="filtro-prioridade",
                                min=0,
                                max=1,
                                step=0.05,
                                value=0.3,
                                marks={0: "0", 0.3: "0.3", 0.6: "0.6", 1: "1"}
                            ),
                        ],
                        style={"flex": "2", "minWidth": "320px"},
                    ),
                    html.Div(
                        [
                            html.Label("Recomendação", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-fluxo-recomendacao",
                                options=[
                                    {"label": "Redistribuir", "value": "redistribuir"},
                                    {"label": "Reuso", "value": "reuso"},
                                    {"label": "Recondicionar", "value": "recondicionar"},
                                    {"label": "Descarte", "value": "descarte"},
                                ],
                                value=["redistribuir"],
                                multi=True,
                                placeholder="Selecione",
                            ),
                        ],
                        style={"flex": "1", "minWidth": "260px"},
                    ),
                ],
                style={
                    **PANEL,
                    "display": "flex",
                    "gap": "18px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),

            html.Div(id="cards-fluxo", style=CARD_CONTAINER),

            html.Div(
                dcc.Graph(id="mapa-fluxo"),
                style={**PANEL, "marginBottom": "14px"},
            ),

            html.Div(
                [
                    html.H4("Fluxos priorizados"),
                    tabela("tabela-fluxo", page_size=15),
                ],
                style=PANEL,
            ),
        ]
    )


def register_callbacks(app):
    @app.callback(
        Output("cards-fluxo", "children"),
        Output("mapa-fluxo", "figure"),
        Output("tabela-fluxo", "columns"),
        Output("tabela-fluxo", "data"),
        Input("filtro-prioridade", "value"),
        Input("filtro-fluxo-recomendacao", "value"),
    )
    def atualizar_fluxo(prioridade, recomendacoes):
        df = carregar_fluxo_monjica()

        if df.empty:
            return [], fig_vazia("Sem dados"), [], []

        # 🔥 filtro básico por recomendação
        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]

        if df.empty:
            return [], fig_vazia("Sem dados após filtro"), [], []

        # 🧠 SCORE INTELIGENTE (ranking composto)
        df["score_final"] = (
            df["score_prioridade"] * 0.6 +
            df["nivel_vulnerabilidade"] * 0.3 +
            (df["quantidade_necessaria"].fillna(0) / 10) * 0.1
        )

        # 🔥 NORMALIZA
        df["score_final"] = df["score_final"] / df["score_final"].max()

        # 🚀 TOP N INTELIGENTE
        TOP_N = 200
        df = df.sort_values("score_final", ascending=False).head(TOP_N)

        # 🧠 GARANTE DIVERSIDADE (não só 1 cidade)
        df = df.groupby("destino").head(5)

        # 🔥 REMOVE RUÍDO
        df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"])

        # 📊 métricas
        total = len(df)
        destinos = df["destino"].nunique()
        prioridade_media = round(df["score_final"].mean(), 2)

        cards = [
            card("Fluxos", total, "priorizados", "#2563eb"),
            card("Destinos", destinos, "municípios", "#16a34a"),
            card("Score médio", prioridade_media, "inteligente", "#dc2626"),
            card("Modelo", "Ranking", "auto", "#7c3aed"),
        ]

        # 🔥 MAPA
        fig = montar_mapa_fluxo(df)

        # 📋 tabela
        tabela_df = df[[
            "tipo_equipamento",
            "origem",
            "destino",
            "score_final",
            "recomendacao"
        ]].rename(columns={"score_final": "score"})

        return (
            cards,
            fig,
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )