import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import (
    CARD_CONTAINER,
    PANEL,
    card,
    fig_vazia,
    hospitais_df,
    municipios_gdf,
    tabela,
)

opcoes_municipios = [
    {"label": m, "value": m}
    for m in sorted(hospitais_df["MUNICIPIO"].dropna().unique())
]

opcoes_esferas = [
    {"label": e, "value": e}
    for e in sorted(hospitais_df["ESFERA"].dropna().unique())
]

opcoes_potencial = [
    {"label": p, "value": p}
    for p in sorted(hospitais_df["POTENCIAL_REAPROVEITAMENTO"].dropna().unique())
]


def montar_mapa(df, gdf):
    if df.empty:
        return fig_vazia("Sem hospitais com coordenadas para exibir", altura=720)

    fig = go.Figure()

    if gdf is not None and not gdf.empty:
        base = px.choropleth_map(
            gdf,
            geojson=gdf.__geo_interface__,
            locations=gdf.index,
            color_discrete_sequence=["#eef2f7"],
            map_style="carto-positron",
            center={"lat": -22.1, "lon": -42.95},
            zoom=6.4,
            opacity=0.55,
            height=720,
            hover_name="NM_MUN" if "NM_MUN" in gdf.columns else None,
        )

        for trace in base.data:
            trace.marker.line.color = "#64748b"
            trace.marker.line.width = 0.7
            trace.showlegend = False
            fig.add_trace(trace)

    pontos = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="POTENCIAL_REAPROVEITAMENTO",
        size="EQUIPAMENTOS_TOTAL",
        size_max=28,
        hover_name="NOME_HOSPITAL",
        hover_data={
            "ESFERA": True,
            "ENDERECO": True,
            "MUNICIPIO": True,
            "LEITOS": True,
            "EQUIPAMENTOS_TOTAL": True,
            "OCIOSOS": True,
            "MANUTENCAO": True,
            "DESCARTE": True,
            "SCORE_REAPROVEITAMENTO": True,
            "LAT": False,
            "LON": False,
        },
        color_discrete_map={
            "Alto": "#dc2626",
            "Médio": "#f59e0b",
            "Baixo": "#16a34a",
            "Inventário pendente": "#2563eb",
        },
        zoom=6.6,
        center={"lat": -22.1, "lon": -42.95},
        height=720,
    )

    for trace in pontos.data:
        fig.add_trace(trace)

    fig.update_layout(
        title="Mapa de hospitais municipais e estaduais com inventário",
        map={
            "style": "carto-positron",
            "center": {"lat": -22.1, "lon": -42.95},
            "zoom": 6.6,
        },
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Potencial de reaproveitamento",
    )
    return fig


def aplicar_filtros(df, municipios, esferas, potenciais):
    dff = df.copy()

    if municipios:
        dff = dff[dff["MUNICIPIO"].isin(municipios)]
    if esferas:
        dff = dff[dff["ESFERA"].isin(esferas)]
    if potenciais:
        dff = dff[dff["POTENCIAL_REAPROVEITAMENTO"].isin(potenciais)]

    return dff


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Município", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-municipio",
                                options=opcoes_municipios,
                                multi=True,
                                placeholder="Todos",
                            ),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Esfera", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-esfera",
                                options=opcoes_esferas,
                                multi=True,
                                placeholder="Todas",
                            ),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Potencial", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-potencial",
                                options=opcoes_potencial,
                                multi=True,
                                placeholder="Todos",
                            ),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                ],
                style={
                    **PANEL,
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),
            html.Div(id="cards-kpi", style=CARD_CONTAINER),
            html.Div(
                dcc.Graph(id="mapa-hospitais"),
                style={**PANEL, "padding": "8px", "marginBottom": "14px"},
            ),
            html.Div(
                [
                    html.Div(
                        dcc.Graph(id="grafico-esfera"),
                        style={"flex": "1", "minWidth": "320px"},
                    ),
                    html.Div(
                        dcc.Graph(id="grafico-potencial"),
                        style={"flex": "1", "minWidth": "320px"},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "14px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),
            html.Div(
                [
                    html.H3("Base de hospitais e inventário", style={"marginTop": "0"}),
                    tabela("tabela-hospitais", page_size=12),
                ],
                style=PANEL,
            ),
        ]
    )


def register_callbacks(app):
    @app.callback(
        Output("cards-kpi", "children"),
        Output("mapa-hospitais", "figure"),
        Output("grafico-esfera", "figure"),
        Output("grafico-potencial", "figure"),
        Output("tabela-hospitais", "columns"),
        Output("tabela-hospitais", "data"),
        Input("filtro-municipio", "value"),
        Input("filtro-esfera", "value"),
        Input("filtro-potencial", "value"),
    )
    def atualizar(municipios, esferas, potenciais):
        dff = aplicar_filtros(hospitais_df, municipios, esferas, potenciais)

        total = len(dff)
        equipamentos = int(dff["EQUIPAMENTOS_TOTAL"].sum())
        ociosos = int(dff["OCIOSOS"].sum())
        manutencao = int(dff["MANUTENCAO"].sum())
        pendentes = int((dff["POTENCIAL_REAPROVEITAMENTO"] == "Inventário pendente").sum())
        taxa_reuso = 0 if equipamentos == 0 else round(((ociosos + manutencao) / equipamentos) * 100, 1)

        cards = [
            card("Hospitais mapeados", f"{total}", "unidades com coordenadas válidas", "#2563eb"),
            card("Equipamentos cadastrados", f"{equipamentos}", "inventário total informado", "#0f766e"),
            card("Potencial de reuso", f"{taxa_reuso}%", "ociosos + manutenção sobre total", "#f59e0b"),
            card("Inventário pendente", f"{pendentes}", "unidades a qualificar no piloto", "#7c3aed"),
        ]

        fig_mapa = montar_mapa(dff, municipios_gdf)

        esfera = dff.groupby("ESFERA", as_index=False).agg(
            HOSPITAIS=("ID_HOSPITAL", "count"),
            EQUIPAMENTOS=("EQUIPAMENTOS_TOTAL", "sum"),
        )

        potencial = dff.groupby("POTENCIAL_REAPROVEITAMENTO", as_index=False).agg(
            HOSPITAIS=("ID_HOSPITAL", "count")
        )

        fig_esfera = (
            px.bar(
                esfera,
                x="ESFERA",
                y="HOSPITAIS",
                text="HOSPITAIS",
                color="ESFERA",
                title="Hospitais por esfera",
            )
            if not esfera.empty
            else fig_vazia("Sem dados")
        )

        fig_potencial = (
            px.bar(
                potencial,
                x="POTENCIAL_REAPROVEITAMENTO",
                y="HOSPITAIS",
                text="HOSPITAIS",
                color="POTENCIAL_REAPROVEITAMENTO",
                title="Hospitais por potencial",
            )
            if not potencial.empty
            else fig_vazia("Sem dados")
        )

        for fig in [fig_esfera, fig_potencial]:
            fig.update_layout(
                height=420,
                margin=dict(l=10, r=10, t=50, b=10),
                showlegend=False,
            )

        tabela_df = dff[
            [
                "NOME_HOSPITAL",
                "ESFERA",
                "PORTE",
                "ENDERECO",
                "MUNICIPIO",
                "REGIAO",
                "LEITOS",
                "LEITOS_REFERENCIA",
                "TELEFONE_REFERENCIA",
                "EQUIPAMENTOS_TOTAL",
                "OCIOSOS",
                "MANUTENCAO",
                "DESCARTE",
                "POTENCIAL_REAPROVEITAMENTO",
                "SCORE_REAPROVEITAMENTO",
            ]
        ].sort_values(["MUNICIPIO", "NOME_HOSPITAL"])

        return (
            cards,
            fig_mapa,
            fig_esfera,
            fig_potencial,
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
