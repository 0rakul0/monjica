import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_monjica, fig_vazia, municipios_gdf, secao_intro, tabela

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


def montar_mapa_monjica(df):
    if df.empty:
        return fig_vazia("Sem dados territoriais MONJICA", altura=500)

    mapa_df = (
        df.dropna(subset=["lat_origem", "lon_origem"])
        .groupby(["origem", "REGIAO_ORIGEM", "recomendacao", "lat_origem", "lon_origem"], as_index=False)
        .agg(
            equipamentos=("id", "count"),
            score_medio=("score_prioridade", "mean"),
        )
    )

    if mapa_df.empty:
        return fig_vazia("Sem coordenadas validas para o mapa MONJICA", altura=500)

    fig = go.Figure()

    if municipios_gdf is not None and not municipios_gdf.empty:
        base = px.choropleth_map(
            municipios_gdf,
            geojson=municipios_gdf.__geo_interface__,
            locations=municipios_gdf.index,
            color="REGIAO_SAUDE",
            color_discrete_map=CORES_REGIAO,
            map_style="carto-positron",
            center={"lat": -22.1, "lon": -42.95},
            zoom=6.4,
            opacity=0.18,
            height=500,
            hover_name="NM_MUN" if "NM_MUN" in municipios_gdf.columns else None,
            hover_data={"REGIAO_SAUDE": True},
        )
        for trace in base.data:
            trace.marker.line.color = "#94a3b8"
            trace.marker.line.width = 0.8
            trace.showlegend = False
            fig.add_trace(trace)

    pontos = px.scatter_map(
        mapa_df,
        lat="lat_origem",
        lon="lon_origem",
        color="recomendacao",
        hover_name="origem",
        hover_data={
            "REGIAO_ORIGEM": True,
            "equipamentos": True,
            "score_medio": ":.2f",
            "lat_origem": False,
            "lon_origem": False,
        },
        color_discrete_map={
            "redistribuir": "#dc2626",
            "reuso": "#16a34a",
            "recondicionar": "#f59e0b",
            "descarte": "#64748b",
        },
        zoom=6.6,
        center={"lat": -22.1, "lon": -42.95},
        height=500,
        title="Distribuicao territorial das prioridades MONJICA",
    )
    for trace in pontos.data:
        trace.marker.size = 9
        fig.add_trace(trace)

    fig.update_layout(
        map={"style": "carto-positron", "center": {"lat": -22.1, "lon": -42.95}, "zoom": 6.6},
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Recomendacao",
    )
    return fig


def layout():
    return html.Div(
        [
            secao_intro(
                "Inteligencia MONJICA",
                "Esta etapa concentra a camada analitica do projeto e traduz o inventario em apoio estruturado a decisao. O objetivo nao e automatizar a governanca, e sim organizar criterios tecnicos e territoriais para priorizar acoes no piloto.",
                objetivo="demonstrar a plausibilidade do componente de IA do projeto, conectando score, criticidade e recomendacao a uma logica de triagem rastreavel.",
                encontra="filtros por recomendacao e regiao, indicadores executivos, leitura territorial das prioridades e tabela com explicacao do modelo.",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Recomendacao", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-recomendacao",
                                options=[
                                    {"label": "Redistribuir", "value": "redistribuir"},
                                    {"label": "Reuso", "value": "reuso"},
                                    {"label": "Recondicionar", "value": "recondicionar"},
                                    {"label": "Descarte", "value": "descarte"},
                                ],
                                multi=True,
                                placeholder="Todas",
                            ),
                        ],
                        style={"minWidth": "250px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Regiao de origem", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-regiao-monjica", multi=True, placeholder="Todas as regioes"),
                        ],
                        style={"minWidth": "280px", "flex": "1"},
                    ),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-monjica", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="mapa-monjica"), style={**PANEL, "marginBottom": "14px"}),
            html.Div(
                [
                    html.Div(dcc.Graph(id="grafico-prioridade"), style={"flex": "1", "minWidth": "360px"}),
                    html.Div(dcc.Graph(id="grafico-regiao-monjica"), style={"flex": "1", "minWidth": "360px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(
                [
                    html.H4("Quantitativo por regiao"),
                    html.Div(
                        "Este quadro resume o volume de equipamentos analisados por regiao de origem, junto do score medio observado no filtro atual.",
                        style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"},
                    ),
                    tabela("tabela-regiao-monjica", page_size=10),
                ],
                style={**PANEL, "marginBottom": "14px"},
            ),
            html.Div(
                [
                    html.H4("Equipamentos priorizados"),
                    html.Div(
                        "A tabela abaixo mostra os equipamentos analisados com score, recomendacao e explicacao do modelo. Esta etapa sustenta a narrativa de apoio a decisao do edital, deixando claro como a priorizacao pode ser auditada e validada institucionalmente.",
                        style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"},
                    ),
                    tabela("tabela-monjica", page_size=15),
                ],
                style=PANEL,
            ),
        ]
    )


def register_callbacks(app):
    @app.callback(
        Output("filtro-regiao-monjica", "options"),
        Input("filtro-recomendacao", "value"),
    )
    def carregar_opcoes_regiao(_):
        df = carregar_monjica()
        if df.empty:
            return []
        return [{"label": r, "value": r} for r in sorted(df["REGIAO_ORIGEM"].dropna().unique())]

    @app.callback(
        Output("cards-monjica", "children"),
        Output("mapa-monjica", "figure"),
        Output("grafico-prioridade", "figure"),
        Output("grafico-regiao-monjica", "figure"),
        Output("tabela-regiao-monjica", "columns"),
        Output("tabela-regiao-monjica", "data"),
        Output("tabela-monjica", "columns"),
        Output("tabela-monjica", "data"),
        Input("filtro-recomendacao", "value"),
        Input("filtro-regiao-monjica", "value"),
    )
    def atualizar_monjica(filtro, regioes):
        df = carregar_monjica()
        if filtro:
            df = df[df["recomendacao"].isin(filtro)]
        if regioes:
            df = df[df["REGIAO_ORIGEM"].isin(regioes)]

        if df.empty:
            vazio = fig_vazia("Sem dados MONJICA")
            return [], vazio, vazio, vazio, [], [], [], []

        total = len(df)
        redistribuir = len(df[df["recomendacao"] == "redistribuir"])
        reuso = len(df[df["recomendacao"] == "reuso"])
        recondicionar = len(df[df["recomendacao"] == "recondicionar"])
        descarte = len(df[df["recomendacao"] == "descarte"])

        regiao_df = (
            df.groupby("REGIAO_ORIGEM", as_index=False)
            .agg(
                equipamentos=("id", "count"),
                score_medio=("score_prioridade", "mean"),
                redistribuir=("recomendacao", lambda s: int((s == "redistribuir").sum())),
                recondicionar=("recomendacao", lambda s: int((s == "recondicionar").sum())),
            )
            .sort_values(["score_medio", "equipamentos"], ascending=False)
        )
        regiao_lider = regiao_df.iloc[0]["REGIAO_ORIGEM"] if not regiao_df.empty else "Sem dados"
        score_lider = round(regiao_df.iloc[0]["score_medio"], 2) if not regiao_df.empty else 0

        cards = [
            card("Equipamentos analisados", f"{total}", "processados pelo MONJICA", "#2563eb"),
            card("Redistribuicao prioritaria", f"{redistribuir}", "alta prioridade social", "#dc2626"),
            card("Reuso direto", f"{reuso}", "baixo custo de reaproveitamento", "#16a34a"),
            card("Recondicionar", f"{recondicionar}", "requer triagem tecnica", "#f59e0b"),
            card("Regiao mais critica", regiao_lider, f"score medio {score_lider}", "#7c3aed"),
            card("Descarte", f"{descarte}", "baixa viabilidade de reuso", "#64748b"),
        ]

        fig_mapa = montar_mapa_monjica(df)
        top = df.sort_values("score_prioridade", ascending=False).head(20)
        fig_prioridade = px.bar(
            top,
            x="score_prioridade",
            y="tipo_equipamento",
            color="recomendacao",
            orientation="h",
            title="Top equipamentos por prioridade",
        )
        fig_prioridade.update_layout(height=460, margin=dict(l=10, r=10, t=50, b=10))

        fig_regiao = (
            px.bar(
                regiao_df,
                x="equipamentos",
                y="REGIAO_ORIGEM",
                orientation="h",
                text="equipamentos",
                color="REGIAO_ORIGEM",
                hover_data={"score_medio": ":.2f", "redistribuir": True, "recondicionar": True},
                color_discrete_map=CORES_REGIAO,
                title="Quantitativo de equipamentos por regiao de origem",
            )
            if not regiao_df.empty
            else fig_vazia("Sem dados regionais")
        )
        fig_regiao.update_layout(height=460, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

        tabela_regiao_df = regiao_df.rename(
            columns={
                "REGIAO_ORIGEM": "Regiao",
                "equipamentos": "Equipamentos analisados",
                "score_medio": "Score medio",
                "redistribuir": "Redistribuir",
                "recondicionar": "Recondicionar",
            }
        ).sort_values("Equipamentos analisados", ascending=False)
        if "Score medio" in tabela_regiao_df.columns:
            tabela_regiao_df["Score medio"] = tabela_regiao_df["Score medio"].round(2)

        tabela_df = df[
            [
                "REGIAO_ORIGEM",
                "tipo_equipamento",
                "estado_atual",
                "origem",
                "score_reuso",
                "score_criticidade",
                "score_prioridade",
                "recomendacao",
                "explicacao_modelo",
            ]
        ].rename(
            columns={
                "REGIAO_ORIGEM": "Regiao",
                "tipo_equipamento": "Tipo de equipamento",
                "estado_atual": "Estado atual",
                "origem": "Municipio de origem",
                "score_reuso": "Score de reuso",
                "score_criticidade": "Score de criticidade",
                "score_prioridade": "Score de prioridade",
                "recomendacao": "Recomendacao",
                "explicacao_modelo": "Explicacao do modelo",
            }
        ).sort_values("Score de prioridade", ascending=False)

        return (
            cards,
            fig_mapa,
            fig_prioridade,
            fig_regiao,
            [{"name": c, "id": c} for c in tabela_regiao_df.columns],
            tabela_regiao_df.to_dict("records"),
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
