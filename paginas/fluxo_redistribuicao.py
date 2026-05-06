import plotly.express as px
import plotly.graph_objects as go
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_fluxo_monjica, fig_vazia, municipios_gdf, obter_rota_osrm, secao_intro, tabela

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


def distancia_haversine_km(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    except Exception:
        return None
    raio = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * raio * asin(sqrt(a))


@lru_cache(maxsize=256)
def obter_rota_cache(lat1, lon1, lat2, lon2):
    return obter_rota_osrm(lat1, lon1, lat2, lon2)


def montar_mapa_fluxo(df, destino_alvo=None, tipo_alvo=None, origem_alvo=None):
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
        custom_data=["destino", "tipo_equipamento", "origem", "recomendacao", "score_final", "equipamentos"],
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
            customdata=mapa_df[["destino", "tipo_equipamento", "origem", "recomendacao", "score_final", "equipamentos"]].values,
            hovertemplate=(
                "Destino: %{customdata[0]}"
                "<br>Equipamento: %{customdata[1]}"
                "<br>Doador sugerido: %{customdata[2]}"
                "<br>Recomendacao: %{customdata[3]}"
                "<br>Score: %{customdata[4]:.2f}"
                "<extra></extra>"
            ),
        )
    )

    line_lats = []
    line_lons = []
    hover_texts = []
    sel_lats = []
    sel_lons = []
    sel_texts = []
    for _, row in mapa_df.iterrows():
        texto = (
            f"{row['origem']} -> {row['destino']}"
            f"<br>{row['tipo_equipamento']}"
            f"<br>{row['equipamentos']} equipamentos"
            f"<br>score {row['score_final']:.2f}"
        )
        selecionado = (
            destino_alvo
            and tipo_alvo
            and row["destino"] == destino_alvo
            and row["tipo_equipamento"] == tipo_alvo
            and (origem_alvo is None or row["origem"] == origem_alvo)
        )
        alvo_lats = sel_lats if selecionado else line_lats
        alvo_lons = sel_lons if selecionado else line_lons
        alvo_textos = sel_texts if selecionado else hover_texts
        alvo_lats.extend([row["lat_origem"], row["lat_destino"], None])
        alvo_lons.extend([row["lon_origem"], row["lon_destino"], None])
        alvo_textos.extend([texto, texto, None])

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
    if sel_lats:
        fig.add_trace(
            go.Scattermap(
                lat=sel_lats,
                lon=sel_lons,
                mode="lines",
                line=dict(width=2.8, color="#7f1d1d"),
                opacity=0.75,
                text=sel_texts,
                hoverinfo="text",
                showlegend=False,
                name="Fluxo selecionado",
            )
        )
    fig.update_layout(
        map={"style": "carto-positron", "center": {"lat": -22.1, "lon": -42.95}, "zoom": 6.2},
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def montar_mini_mapa_doadores(df, destino_alvo, tipo_alvo=None, rota_detalhada=False):
    if df.empty:
        return fig_vazia("Sem doadores viaveis para o destino selecionado", altura=420)

    dff = df[df["destino"] == destino_alvo].copy()
    if tipo_alvo:
        dff = dff[dff["tipo_equipamento"] == tipo_alvo].copy()
    dff = dff.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"]).copy()
    if dff.empty:
        return fig_vazia("Sem coordenadas para o detalhamento", altura=420)

    destino_row = dff.iloc[0]
    centro = {"lat": float(destino_row["lat_destino"]), "lon": float(destino_row["lon_destino"])}
    fig = go.Figure()

    origens = px.scatter_map(
        dff,
        lat="lat_origem",
        lon="lon_origem",
        color="REGIAO_ORIGEM",
        hover_name="origem",
        hover_data={"equipamentos": True, "score_final": ":.2f", "lat_origem": False, "lon_origem": False},
        center=centro,
        zoom=7.4,
        height=420,
    )
    for trace in origens.data:
        trace.marker.size = 9
        fig.add_trace(trace)

    fig.add_trace(
        go.Scattermap(
            lat=[destino_row["lat_destino"]],
            lon=[destino_row["lon_destino"]],
            mode="markers",
            marker=dict(size=11, color="#166534"),
            name="Destino",
            hovertemplate=f"Destino: {destino_alvo}<br>Equipamento: {tipo_alvo or 'todos os tipos'}<extra></extra>",
        )
    )

    detalhadas = dff.sort_values(["score_final", "equipamentos"], ascending=False).head(8).copy()
    for _, row in detalhadas.iterrows():
        texto = (
            f"{row['origem']} -> {row['destino']}"
            f"<br>{row['tipo_equipamento']}"
            f"<br>{row['equipamentos']} equipamentos"
            f"<br>score {row['score_final']:.2f}"
        )
        if rota_detalhada:
            rota = obter_rota_cache(row["lat_origem"], row["lon_origem"], row["lat_destino"], row["lon_destino"])
            if rota[0] is not None:
                lats, lons, dist, tempo = rota
                fig.add_trace(
                    go.Scattermap(
                        lat=lats,
                        lon=lons,
                        mode="lines",
                        line=dict(width=2.0, color="#b91c1c"),
                        opacity=0.6,
                        hovertext=f"{texto}<br>{dist:.1f} km | {tempo:.0f} min",
                        hoverinfo="text",
                        showlegend=False,
                    )
                )
                continue
        fig.add_trace(
            go.Scattermap(
                lat=[row["lat_origem"], row["lat_destino"]],
                lon=[row["lon_origem"], row["lon_destino"]],
                mode="lines",
                line=dict(width=1.8, color="#b91c1c"),
                opacity=0.5,
                hovertext=texto,
                hoverinfo="text",
                showlegend=False,
            )
        )
    fig.update_layout(
        title="Doadores viaveis para o destino selecionado",
        map={"style": "carto-positron", "center": centro, "zoom": 7.4},
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
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
                    html.Div([html.Label("Destino", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-destino-fluxo", placeholder="Selecione um destino para detalhar")], style={"flex": "1", "minWidth": "280px"}),
                    html.Div([html.Label("Tipo de equipamento", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-tipo-equipamento-fluxo", placeholder="Selecione um tipo de equipamento")], style={"flex": "1", "minWidth": "300px"}),
                ],
                style={**PANEL, "display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-fluxo", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="mapa-fluxo", config={"scrollZoom": True}), style={**PANEL, "marginBottom": "14px"}),
            html.Div(
                [
                    html.H4("Doadores viaveis para o destino selecionado"),
                    html.Div(
                        "Clique em um ponto de origem ou destino no mapa para abrir os doadores possiveis daquele destino. A leitura abaixo ajuda a transformar o fluxo agregado em uma lista concreta de candidatos para operacionalizacao.",
                        style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"},
                    ),
                    html.Div(id="detalhe-fluxo-selecionado", style={"marginBottom": "10px"}),
                    dcc.Graph(id="mapa-doadores-fluxo"),
                    tabela("tabela-doadores-fluxo", page_size=10),
                ],
                style={**PANEL, "marginBottom": "14px"},
            ),
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
        Output("filtro-destino-fluxo", "options"),
        Output("filtro-destino-fluxo", "value"),
        Input("filtro-regiao-fluxo", "value"),
        Input("filtro-prioridade", "value"),
        Input("filtro-fluxo-recomendacao", "value"),
        Input("mapa-fluxo", "clickData"),
    )
    def carregar_opcoes_destino(regioes, prioridade, recomendacoes, click_data):
        df = carregar_fluxo_monjica()
        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]
        if regioes:
            df = df[(df["REGIAO_ORIGEM"].isin(regioes)) | (df["REGIAO_DESTINO"].isin(regioes))]
        if df.empty:
            return [], None
        _, fluxos = agregar_fluxos(df, prioridade or 0)
        if fluxos.empty:
            return [], None
        destinos = sorted(fluxos["destino"].dropna().unique())
        opcoes = [{"label": d, "value": d} for d in destinos]
        valor = None
        if click_data and click_data.get("points"):
            custom = click_data["points"][0].get("customdata")
            if custom and len(custom) >= 1 and custom[0] in destinos:
                valor = custom[0]
        return opcoes, valor

    @app.callback(
        Output("filtro-tipo-equipamento-fluxo", "options"),
        Output("filtro-tipo-equipamento-fluxo", "value"),
        Input("filtro-regiao-fluxo", "value"),
        Input("filtro-prioridade", "value"),
        Input("filtro-fluxo-recomendacao", "value"),
        Input("filtro-destino-fluxo", "value"),
        Input("mapa-fluxo", "clickData"),
    )
    def carregar_opcoes_tipo(regioes, prioridade, recomendacoes, destino_selecionado, click_data):
        df = carregar_fluxo_monjica()
        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]
        if regioes:
            df = df[(df["REGIAO_ORIGEM"].isin(regioes)) | (df["REGIAO_DESTINO"].isin(regioes))]
        if destino_selecionado:
            df = df[df["destino"] == destino_selecionado]
        if df.empty:
            return [], None
        _, fluxos = agregar_fluxos(df, prioridade or 0)
        if fluxos.empty:
            return [], None
        tipos = sorted(fluxos["tipo_equipamento"].dropna().unique())
        opcoes = [{"label": t, "value": t} for t in tipos]
        valor = None
        if click_data and click_data.get("points"):
            custom = click_data["points"][0].get("customdata")
            if custom and len(custom) >= 2 and custom[1] in tipos:
                valor = custom[1]
        return opcoes, valor

    @app.callback(
        Output("cards-fluxo", "children"),
        Output("mapa-fluxo", "figure"),
        Output("detalhe-fluxo-selecionado", "children"),
        Output("mapa-doadores-fluxo", "figure"),
        Output("tabela-doadores-fluxo", "columns"),
        Output("tabela-doadores-fluxo", "data"),
        Output("tabela-fluxo", "columns"),
        Output("tabela-fluxo", "data"),
        Input("filtro-regiao-fluxo", "value"),
        Input("filtro-prioridade", "value"),
        Input("filtro-fluxo-recomendacao", "value"),
        Input("filtro-destino-fluxo", "value"),
        Input("filtro-tipo-equipamento-fluxo", "value"),
        Input("mapa-fluxo", "clickData"),
    )
    def atualizar_fluxo(regioes, prioridade, recomendacoes, destino_selecionado, tipo_equipamento_selecionado, click_data):
        df = carregar_fluxo_monjica()
        if df.empty:
            vazio = fig_vazia("Sem dados")
            return [], vazio, html.Div("Sem dados de fluxo.", style={"color": "#64748b"}), vazio, [], [], [], []
        if recomendacoes:
            df = df[df["recomendacao"].isin(recomendacoes)]
        if regioes:
            df = df[(df["REGIAO_ORIGEM"].isin(regioes)) | (df["REGIAO_DESTINO"].isin(regioes))]
        if destino_selecionado:
            df = df[df["destino"] == destino_selecionado]
        if tipo_equipamento_selecionado:
            df = df[df["tipo_equipamento"] == tipo_equipamento_selecionado]
        if df.empty:
            vazio = fig_vazia("Sem dados após filtro")
            return [], vazio, html.Div("Sem dados para os filtros atuais.", style={"color": "#64748b"}), vazio, [], [], [], []

        base, fluxos = agregar_fluxos(df, prioridade)
        if fluxos.empty:
            vazio = fig_vazia("Nenhum fluxo acima da prioridade mínima")
            return [], vazio, html.Div("Nenhum fluxo ficou acima do corte atual.", style={"color": "#64748b"}), vazio, [], [], [], []

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

        destino_alvo = None
        tipo_alvo = None
        origem_alvo = None
        fig_detalhe = fig_vazia("Clique em um ponto do mapa para ver os doadores", altura=420)

        detalhe = html.Div("Selecione um destino ou clique em um ponto do mapa para ver doadores viaveis.", style={"color": "#64748b"})
        tabela_doadores_df = fluxos.iloc[0:0].copy()
        if destino_selecionado and not (click_data and click_data.get("points")):
            doadores = fluxos[fluxos["destino"] == destino_selecionado].copy()
            if tipo_equipamento_selecionado:
                doadores = doadores[doadores["tipo_equipamento"] == tipo_equipamento_selecionado].copy()
            doadores = doadores.sort_values(["score_final", "equipamentos"], ascending=False)
            doadores["distancia_km"] = doadores.apply(
                lambda row: distancia_haversine_km(row["lat_origem"], row["lon_origem"], row["lat_destino"], row["lon_destino"]),
                axis=1,
            )
            doadores["rank_viabilidade"] = range(1, len(doadores) + 1)
            total_doadores = doadores["origem"].nunique()
            total_equip = int(doadores["equipamentos"].sum()) if not doadores.empty else 0
            detalhe = html.Div(
                [
                    html.Div(f"Destino selecionado: {destino_selecionado}", style={"fontWeight": "700", "marginBottom": "4px"}),
                    html.Div(f"Tipo de equipamento: {tipo_equipamento_selecionado or 'todos os tipos'}", style={"marginBottom": "4px"}),
                    html.Div(f"Rotas viaveis no filtro atual: {len(doadores)}", style={"marginBottom": "4px"}),
                    html.Div(f"Doadores viaveis: {total_doadores} | Equipamentos nas rotas: {total_equip}", style={"color": "#475569"}),
                ]
            )
            fig_detalhe = montar_mini_mapa_doadores(doadores, destino_selecionado, tipo_equipamento_selecionado, rota_detalhada=True)
            tabela_doadores_df = doadores[
                [
                    "rank_viabilidade",
                    "REGIAO_ORIGEM",
                    "origem",
                    "REGIAO_DESTINO",
                    "destino",
                    "tipo_equipamento",
                    "equipamentos",
                    "distancia_km",
                    "score_final",
                    "recomendacao",
                ]
            ].rename(
                columns={
                    "rank_viabilidade": "Rank",
                    "REGIAO_ORIGEM": "Região origem",
                    "origem": "Doador",
                    "REGIAO_DESTINO": "Região destino",
                    "destino": "Destino",
                    "tipo_equipamento": "Equipamento",
                    "equipamentos": "Qtd equipamentos",
                    "distancia_km": "Distância estimada (km)",
                    "score_final": "Score",
                    "recomendacao": "Recomendação",
                }
            )
            tabela_doadores_df["Distância estimada (km)"] = tabela_doadores_df["Distância estimada (km)"].round(1)
            tabela_doadores_df["Score"] = tabela_doadores_df["Score"].round(2)

        if click_data and click_data.get("points"):
            custom = click_data["points"][0].get("customdata")
            if custom and len(custom) >= 2:
                destino_alvo = custom[0]
                tipo_alvo = custom[1]
                origem_alvo = custom[2] if len(custom) >= 3 else None
                doadores = fluxos[
                    (fluxos["destino"] == destino_alvo)
                    & (fluxos["tipo_equipamento"] == tipo_alvo)
                ].copy()
                doadores = doadores.sort_values(["score_final", "equipamentos"], ascending=False)
                doadores["distancia_km"] = doadores.apply(
                    lambda row: distancia_haversine_km(row["lat_origem"], row["lon_origem"], row["lat_destino"], row["lon_destino"]),
                    axis=1,
                )
                doadores["rank_viabilidade"] = range(1, len(doadores) + 1)
                total_doadores = doadores["origem"].nunique()
                total_equip = int(doadores["equipamentos"].sum()) if not doadores.empty else 0
                detalhe = html.Div(
                    [
                        html.Div(f"Destino selecionado: {destino_alvo}", style={"fontWeight": "700", "marginBottom": "4px"}),
                        html.Div(f"Tipo de equipamento: {tipo_alvo}", style={"marginBottom": "4px"}),
                        html.Div(f"Doadores viaveis: {total_doadores} | Equipamentos nas rotas: {total_equip}", style={"color": "#475569"}),
                    ]
                )
                fig_detalhe = montar_mini_mapa_doadores(doadores, destino_alvo, tipo_alvo, rota_detalhada=True)
                tabela_doadores_df = doadores[
                    [
                        "rank_viabilidade",
                        "REGIAO_ORIGEM",
                        "origem",
                        "REGIAO_DESTINO",
                        "destino",
                        "tipo_equipamento",
                        "equipamentos",
                        "distancia_km",
                        "score_final",
                        "recomendacao",
                    ]
                ].rename(
                    columns={
                        "rank_viabilidade": "Rank",
                        "REGIAO_ORIGEM": "Região origem",
                        "origem": "Doador",
                        "REGIAO_DESTINO": "Região destino",
                        "destino": "Destino",
                        "tipo_equipamento": "Equipamento",
                        "equipamentos": "Qtd equipamentos",
                        "distancia_km": "Distância estimada (km)",
                        "score_final": "Score",
                        "recomendacao": "Recomendação",
                    }
                )
                tabela_doadores_df["Distância estimada (km)"] = tabela_doadores_df["Distância estimada (km)"].round(1)
                tabela_doadores_df["Score"] = tabela_doadores_df["Score"].round(2)

        fig = montar_mapa_fluxo(fluxos, destino_alvo=destino_alvo, tipo_alvo=tipo_alvo, origem_alvo=origem_alvo)
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

        return (
            cards,
            fig,
            detalhe,
            fig_detalhe,
            [{"name": c, "id": c} for c in tabela_doadores_df.columns],
            tabela_doadores_df.to_dict("records"),
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
