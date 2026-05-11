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
    secao_intro,
    tabela,
)

opcoes_municipios = [
    {"label": m, "value": m}
    for m in sorted(hospitais_df["MUNICIPIO"].dropna().unique())
]
opcoes_regioes = [
    {"label": r, "value": r}
    for r in sorted(hospitais_df["REGIAO"].dropna().unique())
]
opcoes_esferas = [
    {"label": e, "value": e}
    for e in sorted(hospitais_df["ESFERA"].dropna().unique())
]
opcoes_potencial = [
    {"label": p, "value": p}
    for p in sorted(hospitais_df["POTENCIAL_REAPROVEITAMENTO"].dropna().unique())
]

CORES_REGIAO = {
    "REGIÃO BAÍA DA ILHA GRANDE": "#0f766e",
    "REGIÃO BAIXADA LITORÂNEA": "#0891b2",
    "REGIÃO CENTRO-SUL": "#7c3aed",
    "REGIÃO MÉDIO PARAÍBA": "#2563eb",
    "REGIÃO METROPOLITANA I": "#dc2626",
    "REGIÃO METROPOLITANA II": "#ea580c",
    "REGIÃO NORTE": "#16a34a",
    "REGIÃO NOROESTE": "#ca8a04",
    "REGIÃO SERRANA": "#9333ea",
    "A classificar": "#64748b",
}


def montar_mapa(df, gdf):
    if df.empty:
        return fig_vazia("Sem hospitais com coordenadas para exibir", altura=720)

    fig = go.Figure()
    if gdf is not None and not gdf.empty:
        base = px.choropleth_map(
            gdf,
            geojson=gdf.__geo_interface__,
            locations=gdf.index,
            color="REGIAO_SAUDE",
            color_discrete_map=CORES_REGIAO,
            map_style="carto-positron",
            center={"lat": -22.1, "lon": -42.95},
            zoom=6.4,
            opacity=0.18,
            height=720,
            hover_name="NM_MUN" if "NM_MUN" in gdf.columns else None,
            hover_data={"REGIAO_SAUDE": True},
        )
        for trace in base.data:
            trace.marker.line.color = "#94a3b8"
            trace.marker.line.width = 0.8
            trace.showlegend = False
            fig.add_trace(trace)

    pontos = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="POTENCIAL_REAPROVEITAMENTO",
        hover_name="NOME_HOSPITAL",
        hover_data={
            "REGIAO": True,
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
        trace.marker.size = 9
        fig.add_trace(trace)

    fig.update_layout(
        title="Mapa estadual com regiões de saúde e hospitais mapeados",
        map={"style": "carto-positron", "center": {"lat": -22.1, "lon": -42.95}, "zoom": 6.6},
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Potencial de reaproveitamento",
    )
    return fig


def aplicar_filtros(df, regioes, municipios, esferas, potenciais):
    dff = df.copy()
    if regioes:
        dff = dff[dff["REGIAO"].isin(regioes)]
    if municipios:
        dff = dff[dff["MUNICIPIO"].isin(municipios)]
    if esferas:
        dff = dff[dff["ESFERA"].isin(esferas)]
    if potenciais:
        dff = dff[dff["POTENCIAL_REAPROVEITAMENTO"].isin(potenciais)]
    return dff


def resumo_regional(dff):
    if dff.empty:
        return pd.DataFrame(columns=["REGIAO", "HOSPITAIS", "EQUIPAMENTOS", "OCIOSOS", "MANUTENCAO", "SCORE_MEDIO", "INDICE_REAPROVEITAMENTO"])

    regiao = dff.groupby("REGIAO", as_index=False).agg(
        HOSPITAIS=("ID_HOSPITAL", "count"),
        EQUIPAMENTOS=("EQUIPAMENTOS_TOTAL", "sum"),
        OCIOSOS=("OCIOSOS", "sum"),
        MANUTENCAO=("MANUTENCAO", "sum"),
        SCORE_MEDIO=("SCORE_REAPROVEITAMENTO", "mean"),
    )
    regiao["INDICE_REAPROVEITAMENTO"] = (
        ((regiao["OCIOSOS"] + regiao["MANUTENCAO"]) / regiao["EQUIPAMENTOS"].replace(0, pd.NA)) * 100
    ).fillna(0).round(1)
    return regiao.sort_values(["INDICE_REAPROVEITAMENTO", "SCORE_MEDIO"], ascending=False)


def layout():
    return html.Div(
        [
            secao_intro(
                "Visão Geral",
                "Esta etapa apresenta a fotografia territorial do projeto: onde estão os hospitais mapeados, como eles se distribuem pelas regiões de saúde do Rio de Janeiro e quais sinais iniciais de reaproveitamento aparecem no inventário atual. Aqui você encontra filtros, mapa estadual, indicadores executivos e comparações entre regiões para orientar prioridades do piloto.",
                objetivo="sustentar o diagnóstico situacional e territorial do piloto no RJ, identificando onde o problema se concentra e quais regiões devem ser priorizadas.",
                encontra="mapa estadual, filtros por região, município, esfera e potencial, além de indicadores comparativos para leitura macro da rede.",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Região", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-regiao-visao", options=opcoes_regioes, multi=True, placeholder="Todas"),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Município", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-municipio", options=opcoes_municipios, multi=True, placeholder="Todos"),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Esfera", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-esfera", options=opcoes_esferas, multi=True, placeholder="Todas"),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Potencial", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-potencial", options=opcoes_potencial, multi=True, placeholder="Todos"),
                        ],
                        style={"minWidth": "220px", "flex": "1"},
                    ),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-kpi", style=CARD_CONTAINER),
            html.Div(
                [
                    html.Div(dcc.Graph(id="mapa-hospitais"), style={**PANEL, "padding": "8px", "marginBottom": "14px",
                                                                    "flex": "1", "minWidth": "320px"}),
                    html.Div(dcc.Graph(id="grafico-regiao"), style={"flex": "1", "minWidth": "320px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(
                [
                    html.Div(dcc.Graph(id="grafico-esfera"), style={"flex": "1", "minWidth": "320px"}),
                    html.Div(dcc.Graph(id="grafico-potencial"), style={"flex": "1", "minWidth": "320px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(
                [html.H3("Base de hospitais e inventário", style={"marginTop": "0"}), tabela("tabela-hospitais", page_size=12)],
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
        Output("grafico-regiao", "figure"),
        Output("tabela-hospitais", "columns"),
        Output("tabela-hospitais", "data"),
        Input("filtro-regiao-visao", "value"),
        Input("filtro-municipio", "value"),
        Input("filtro-esfera", "value"),
        Input("filtro-potencial", "value"),
    )
    def atualizar(regioes, municipios, esferas, potenciais):
        dff = aplicar_filtros(hospitais_df, regioes, municipios, esferas, potenciais)
        total = len(dff)
        equipamentos = int(dff["EQUIPAMENTOS_TOTAL"].sum())
        manutencao = int(dff["MANUTENCAO"].sum())
        ociosos = int(dff["OCIOSOS"].sum())
        pendentes = int((dff["POTENCIAL_REAPROVEITAMENTO"] == "Inventário pendente").sum())
        taxa_reuso = 0 if equipamentos == 0 else round(((ociosos + manutencao) / equipamentos) * 100, 1)

        regiao_df = resumo_regional(dff)
        if regiao_df.empty:
            regiao_lider = "Sem dados"
            detalhe_regiao = "sem base no filtro atual"
        else:
            lider = regiao_df.iloc[0]
            regiao_lider = lider["REGIAO"]
            detalhe_regiao = f"{lider['INDICE_REAPROVEITAMENTO']}% de reaproveitamento estimado"

        cards = [
            card("Hospitais mapeados", f"{total}", "unidades com coordenadas válidas", "#2563eb"),
            card("Equipamentos cadastrados", f"{equipamentos}", "inventário total informado", "#0f766e"),
            card("Potencial de reuso", f"{taxa_reuso}%", "ociosos + manutenção sobre total", "#f59e0b"),
            card("Região com maior índice", regiao_lider, detalhe_regiao, "#7c3aed"),
            card("Inventário pendente", f"{pendentes}", "unidades a qualificar no piloto", "#64748b"),
        ]

        fig_mapa = montar_mapa(dff, municipios_gdf)
        esfera = dff.groupby("ESFERA", as_index=False).agg(HOSPITAIS=("ID_HOSPITAL", "count"))
        potencial = dff.groupby("POTENCIAL_REAPROVEITAMENTO", as_index=False).agg(HOSPITAIS=("ID_HOSPITAL", "count"))

        fig_esfera = px.bar(esfera, x="ESFERA", y="HOSPITAIS", text="HOSPITAIS", color="ESFERA", title="Hospitais por esfera") if not esfera.empty else fig_vazia("Sem dados")
        fig_potencial = px.bar(potencial, x="POTENCIAL_REAPROVEITAMENTO", y="HOSPITAIS", text="HOSPITAIS", color="POTENCIAL_REAPROVEITAMENTO", title="Hospitais por potencial") if not potencial.empty else fig_vazia("Sem dados")
        fig_regiao = px.bar(regiao_df, x="INDICE_REAPROVEITAMENTO", y="REGIAO", orientation="h", text="INDICE_REAPROVEITAMENTO", color="REGIAO", color_discrete_map=CORES_REGIAO, title="Índice estimado de reaproveitamento por região") if not regiao_df.empty else fig_vazia("Sem dados regionais")

        for fig in [fig_esfera, fig_potencial, fig_regiao]:
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

        tabela_df = dff[
            ["NOME_HOSPITAL", "ESFERA", "PORTE", "ENDERECO", "MUNICIPIO", "REGIAO", "LEITOS", "LEITOS_REFERENCIA", "TELEFONE_REFERENCIA", "EQUIPAMENTOS_TOTAL", "OCIOSOS", "MANUTENCAO", "DESCARTE", "POTENCIAL_REAPROVEITAMENTO", "SCORE_REAPROVEITAMENTO"]
        ].sort_values(["REGIAO", "MUNICIPIO", "NOME_HOSPITAL"])

        return cards, fig_mapa, fig_esfera, fig_potencial, fig_regiao, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
