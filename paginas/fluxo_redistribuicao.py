import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_fluxo_monjica, fig_vazia, tabela


def montar_mapa_fluxo(df):
    if df.empty:
        return fig_vazia("Sem fluxos para exibir", altura=700)

    df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"]).copy()

    if df.empty:
        return fig_vazia("Sem fluxos com coordenadas válidas", altura=700)

    fig = go.Figure()

    # Linhas origem -> destino
    for _, row in df.iterrows():
        prioridade = float(row.get("score_prioridade") or 0)

        fig.add_trace(
            go.Scattermapbox(
                lat=[row["lat_origem"], row["lat_destino"]],
                lon=[row["lon_origem"], row["lon_destino"]],
                mode="lines",
                line=dict(width=2 + prioridade * 5, color="#dc2626"),
                opacity=0.55,
                hoverinfo="text",
                text=(
                    f"<b>{row['tipo_equipamento']}</b><br>"
                    f"Origem: {row['origem']}<br>"
                    f"Destino: {row['destino']}<br>"
                    f"Prioridade: {prioridade:.2f}<br>"
                    f"Vulnerabilidade: {row.get('nivel_vulnerabilidade', 'N/A')}<br>"
                    f"Demanda: {row.get('quantidade_necessaria', 'N/A')}"
                ),
                showlegend=False,
            )
        )

    # Origens
    fig.add_trace(
        go.Scattermapbox(
            lat=df["lat_origem"],
            lon=df["lon_origem"],
            mode="markers",
            marker=dict(size=9, color="#2563eb"),
            name="Origem",
            text=df["origem"],
            hoverinfo="text",
        )
    )

    # Destinos
    destinos = (
        df.groupby(["destino", "lat_destino", "lon_destino"], as_index=False)
        .agg(
            fluxos=("id", "count"),
            prioridade_media=("score_prioridade", "mean"),
        )
    )

    fig.add_trace(
        go.Scattermapbox(
            lat=destinos["lat_destino"],
            lon=destinos["lon_destino"],
            mode="markers",
            marker=dict(
                size=12 + destinos["fluxos"] * 2,
                color="#16a34a",
            ),
            name="Destino sugerido",
            text=[
                f"<b>{r.destino}</b><br>Fluxos: {r.fluxos}<br>Prioridade média: {r.prioridade_media:.2f}"
                for r in destinos.itertuples()
            ],
            hoverinfo="text",
        )
    )

    centro = {
        "lat": float(pd.concat([df["lat_origem"], df["lat_destino"]]).mean()),
        "lon": float(pd.concat([df["lon_origem"], df["lon_destino"]]).mean()),
    }

    fig.update_layout(
        title="Fluxo de Redistribuição MONJICA: origem → destino sugerido",
        mapbox=dict(style="carto-positron", center=centro, zoom=6),
        margin=dict(l=10, r=10, t=50, b=10),
        height=700,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
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
                                value=0.5,
                                marks={0: "0", 0.5: "0.5", 1: "1"},
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
            return [], fig_vazia("Sem dados de fluxo"), [], []

        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]

        df = df[df["score_prioridade"] >= prioridade]
        df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"])

        total = len(df)
        destinos = df["destino"].nunique() if not df.empty else 0
        prioridade_media = 0 if df.empty else round(df["score_prioridade"].mean(), 2)
        sem_coord = len(carregar_fluxo_monjica()) - len(carregar_fluxo_monjica().dropna(subset=["lat_destino", "lon_destino"]))

        cards = [
            card("Fluxos filtrados", f"{total}", "equipamentos com rota sugerida", "#2563eb"),
            card("Destinos sugeridos", f"{destinos}", "municípios priorizados", "#16a34a"),
            card("Prioridade média", f"{prioridade_media}", "score MONJICA médio", "#dc2626"),
            card("Sem coordenada destino", f"{sem_coord}", "verificar padronização municipal", "#f59e0b"),
        ]

        fig = montar_mapa_fluxo(df)

        tabela_df = df[
            [
                "tipo_equipamento",
                "origem",
                "destino",
                "score_prioridade",
                "recomendacao",
                "nivel_vulnerabilidade",
                "quantidade_necessaria",
            ]
        ].sort_values("score_prioridade", ascending=False)

        return (
            cards,
            fig,
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
