import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_fluxo_monjica, fig_vazia, municipios_gdf, secao_intro, tabela

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


def agregar_fluxos(df, prioridade_minima):
    if df.empty:
        return df, df

    base = df.copy()
    base["score_final"] = (
        base["score_prioridade"] * 0.6
        + base["nivel_vulnerabilidade"] * 0.3
        + (base["quantidade_necessaria"].fillna(0) / 10) * 0.1
    )
    max_score = base["score_final"].max()
    if max_score and max_score > 0:
        base["score_final"] = base["score_final"] / max_score
    else:
        base["score_final"] = 0

    elegiveis = base[base["score_final"] >= prioridade_minima].copy()
    if elegiveis.empty:
        return base, elegiveis

    agrupado = (
        elegiveis.groupby(
            [
                "REGIAO_ORIGEM",
                "origem",
                "lat_origem",
                "lon_origem",
                "REGIAO_DESTINO",
                "destino",
                "lat_destino",
                "lon_destino",
                "tipo_equipamento",
                "recomendacao",
            ],
            as_index=False,
        )
        .agg(
            equipamentos=("id", "count"),
            score_medio=("score_prioridade", "mean"),
            score_final=("score_final", "mean"),
            vulnerabilidade_media=("nivel_vulnerabilidade", "mean"),
            quantidade_necessaria=("quantidade_necessaria", "max"),
        )
        .sort_values(["score_final", "equipamentos"], ascending=False)
    )

    # Mantem diversidade territorial sem achatar tudo em um unico destino.
    agrupado = agrupado.groupby(["destino", "tipo_equipamento"], as_index=False, group_keys=False).head(3)
    agrupado = agrupado.head(150).copy()
    return base, agrupado


def montar_mapa_fluxo(df):
    if df.empty:
        return fig_vazia("Sem fluxos", altura=600)

    df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"]).copy()
    if df.empty:
        return fig_vazia("Sem coordenadas validas", altura=600)

    mapa_df = df.head(40).copy()
    centro = {"LAT": mapa_df["lat_origem"].mean(), "LON": mapa_df["lon_origem"].mean()}
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
            zoom=6.2,
            opacity=0.16,
            height=560,
            hover_name="NM_MUN" if "NM_MUN" in municipios_gdf.columns else None,
            hover_data={"REGIAO_SAUDE": True},
        )
        for trace in base.data:
            trace.marker.line.color = "#94a3b8"
            trace.marker.line.width = 0.8
            trace.showlegend = False
            fig.add_trace(trace)

    origens = px.scatter_map(
        mapa_df,
        lat="lat_origem",
        lon="lon_origem",
        color="REGIAO_ORIGEM",
        hover_name="origem",
        hover_data={
            "REGIAO_ORIGEM": True,
            "REGIAO_DESTINO": True,
            "tipo_equipamento": True,
            "recomendacao": True,
            "equipamentos": True,
            "score_final": ":.2f",
            "lat_origem": False,
            "lon_origem": False,
        },
        zoom=6.2 if len(mapa_df) > 1 else 11,
        center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
        height=560,
    )
    for trace in origens.data:
        trace.marker.size = 8
        trace.marker.opacity = 0.95
        fig.add_trace(trace)

    fig.add_trace(
        go.Scattermap(
            lat=mapa_df["lat_destino"],
            lon=mapa_df["lon_destino"],
            mode="markers",
            marker=dict(size=8, color="#166534"),
            name="Destino",
            hovertemplate="Destino<br>%{lat:.3f}, %{lon:.3f}<extra></extra>",
        )
    )

    line_lats = []
    line_lons = []
    hover_texts = []
    for _, row in mapa_df.iterrows():
        line_lats.extend([row["lat_origem"], row["lat_destino"], None])
        line_lons.extend([row["lon_origem"], row["lon_destino"], None])
        hover_texts.extend(
            [
                (
                    f"{row['origem']} -> {row['destino']}"
                    f"<br>{row['tipo_equipamento']}"
                    f"<br>{row['equipamentos']} equipamentos"
                    f"<br>score {row['score_final']:.2f}"
                ),
                (
                    f"{row['origem']} -> {row['destino']}"
                    f"<br>{row['tipo_equipamento']}"
                    f"<br>{row['equipamentos']} equipamentos"
                    f"<br>score {row['score_final']:.2f}"
                ),
                None,
            ]
        )

    fig.add_trace(
        go.Scattermap(
            lat=line_lats,
            lon=line_lons,
            mode="lines",
            line=dict(width=1.2, color="#dc2626"),
            opacity=0.35,
            text=hover_texts,
            hoverinfo="text",
            showlegend=False,
            name="Fluxo estimado",
        )
    )
    fig.update_layout(
        map={"style": "carto-positron", "center": {"lat": -22.1, "lon": -42.95}, "zoom": 6.2},
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def layout():
    return html.Div(
        [
            secao_intro(
                "Fluxo de Redistribuição",
                "Esta etapa transforma prioridade analítica em rota de ação territorial. Aqui você encontra os fluxos mais relevantes entre origem e destino, com base no score do modelo, na vulnerabilidade regional e na demanda estimada, para apoiar decisões de redistribuição e logística.",
                objetivo="demonstrar como o diagnóstico e a priorização podem ser convertidos em uma agenda operacional de redistribuição dentro do piloto.",
                encontra="filtros por região, prioridade mínima e recomendação, além de mapa de fluxos e tabela de encaminhamentos priorizados.",
            ),
            html.Div(
                [
                    html.Div([html.Label("Região", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-regiao-fluxo", multi=True, placeholder="Todas as regiões")], style={"flex": "1", "minWidth": "260px"}),
                    html.Div([html.Label("Prioridade mínima", style={"fontWeight": "600"}), dcc.Slider(id="filtro-prioridade", min=0, max=1, step=0.05, value=0.1, marks={0: "0", 0.1: "0.1", 0.3: "0.3", 0.6: "0.6", 1: "1"})], style={"flex": "2", "minWidth": "320px"}),
                    html.Div([html.Label("Recomendação", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-fluxo-recomendacao", options=[{"label": "Redistribuir", "value": "redistribuir"}, {"label": "Reuso", "value": "reuso"}, {"label": "Recondicionar", "value": "recondicionar"}, {"label": "Descarte", "value": "descarte"}], value=["redistribuir"], multi=True, placeholder="Selecione")], style={"flex": "1", "minWidth": "260px"}),
                ],
                style={**PANEL, "display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-fluxo", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="mapa-fluxo", config={"scrollZoom": True}), style={**PANEL, "marginBottom": "14px"}),
            html.Div(
                [
                    html.H4("Fluxos priorizados"),
                    html.Div(
                        "Diferentemente da aba de inteligência, esta etapa não mostra equipamentos individuais, e sim fluxos agregados por origem, destino, tipo e recomendação. Isso permite transformar milhares de equipamentos elegíveis em uma agenda operacional legível.",
                        style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"},
                    ),
                    tabela("tabela-fluxo", page_size=15),
                ],
                style=PANEL,
            ),
        ]
    )


def register_callbacks(app):
    @app.callback(Output("filtro-regiao-fluxo", "options"), Input("filtro-fluxo-recomendacao", "value"))
    def carregar_opcoes_regiao(_):
        df = carregar_fluxo_monjica()
        valores = sorted(set(df["REGIAO_ORIGEM"].dropna().tolist()) | set(df["REGIAO_DESTINO"].dropna().tolist()))
        return [{"label": r, "value": r} for r in valores]

    @app.callback(
        Output("cards-fluxo", "children"),
        Output("mapa-fluxo", "figure"),
        Output("tabela-fluxo", "columns"),
        Output("tabela-fluxo", "data"),
        Input("filtro-regiao-fluxo", "value"),
        Input("filtro-prioridade", "value"),
        Input("filtro-fluxo-recomendacao", "value"),
    )
    def atualizar_fluxo(regioes, prioridade, recomendacoes):
        df = carregar_fluxo_monjica()
        if df.empty:
            return [], fig_vazia("Sem dados"), [], []
        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]
        if regioes:
            df = df[(df["REGIAO_ORIGEM"].isin(regioes)) | (df["REGIAO_DESTINO"].isin(regioes))]
        if df.empty:
            return [], fig_vazia("Sem dados após filtro"), [], []

        base, fluxos = agregar_fluxos(df, prioridade)
        if fluxos.empty:
            return [], fig_vazia("Nenhum fluxo acima da prioridade mínima"), [], []

        equipamentos_elegiveis = len(base[base["score_final"] >= prioridade])
        fluxos_total = len(fluxos)
        destinos = fluxos["destino"].nunique()
        origens = fluxos["origem"].nunique()
        regioes_total = len(set(fluxos["REGIAO_ORIGEM"].dropna().tolist()) | set(fluxos["REGIAO_DESTINO"].dropna().tolist()))
        equipamentos_em_rotas = int(fluxos["equipamentos"].sum())
        prioridade_media = round(fluxos["score_final"].mean(), 2) if fluxos_total else 0

        cards = [
            card("Equipamentos elegiveis", f"{equipamentos_elegiveis}", "itens individuais acima do corte", "#2563eb"),
            card("Fluxos agregados", f"{fluxos_total}", "rotas consolidadas para operacao", "#dc2626"),
            card("Equipamentos em fluxos", f"{equipamentos_em_rotas}", "volume representado nas rotas exibidas", "#0f766e"),
            card("Origens", f"{origens}", "municipios de origem no filtro", "#7c3aed"),
            card("Destinos", f"{destinos}", "municipios de destino no filtro", "#16a34a"),
            card("Regioes", f"{regioes_total}", "origem ou destino no filtro", "#9333ea"),
            card("Score medio", f"{prioridade_media}", "dos fluxos agregados", "#ea580c"),
        ]

        fig = montar_mapa_fluxo(fluxos)
        tabela_df = fluxos[
            [
                "REGIAO_ORIGEM",
                "origem",
                "REGIAO_DESTINO",
                "destino",
                "tipo_equipamento",
                "equipamentos",
                "quantidade_necessaria",
                "score_final",
                "recomendacao",
            ]
        ].rename(
            columns={
                "REGIAO_ORIGEM": "Região origem",
                "origem": "Origem",
                "REGIAO_DESTINO": "Região destino",
                "destino": "Destino",
                "tipo_equipamento": "Equipamento",
                "equipamentos": "Qtd equipamentos",
                "quantidade_necessaria": "Necessidade destino",
                "score_final": "Score",
                "recomendacao": "Recomendação",
            }
        ).sort_values(["Score", "Qtd equipamentos"], ascending=False)
        tabela_df["Score"] = tabela_df["Score"].round(2)

        return cards, fig, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
