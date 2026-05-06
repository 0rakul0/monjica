import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_fluxo_monjica, fig_vazia, obter_rota_osrm, secao_intro, tabela

OPCOES_REGIOES_FLUXO = []


def montar_mapa_fluxo(df):
    if df.empty:
        return fig_vazia("Sem fluxos", altura=600)
    df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"])
    if df.empty:
        return fig_vazia("Sem coordenadas válidas", altura=600)

    df = df.head(30)
    centro = {"LAT": df["lat_origem"].mean(), "LON": df["lon_origem"].mean()}
    fig = px.scatter_mapbox(df, lat="lat_origem", lon="lon_origem", color="REGIAO_ORIGEM", hover_name="origem", hover_data={"REGIAO_ORIGEM": True, "REGIAO_DESTINO": True, "tipo_equipamento": True, "recomendacao": True, "lat_origem": False, "lon_origem": False}, zoom=8 if len(df) > 1 else 12, center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])}, height=500)
    fig.add_trace(go.Scattermapbox(lat=df["lat_destino"], lon=df["lon_destino"], mode="markers", marker=dict(size=10, color="#16a34a"), name="Destino"))
    for _, row in df.iterrows():
        rota = obter_rota_osrm(row["lat_origem"], row["lon_origem"], row["lat_destino"], row["lon_destino"])
        if rota[0] is None:
            continue
        lats, lons, dist, tempo = rota
        fig.add_trace(go.Scattermapbox(lat=lats, lon=lons, mode="lines", line=dict(width=3, color="#dc2626"), opacity=0.6, hovertext=f"{row['origem']} -> {row['destino']}<br>{dist:.1f} km | {tempo:.0f} min", hoverinfo="text", showlegend=False))
    fig.update_layout(mapbox=dict(style="carto-positron"), margin=dict(l=10, r=10, t=10, b=10))
    return fig


def layout():
    return html.Div(
        [
            secao_intro("Fluxo de Redistribuição", "Esta etapa transforma prioridade analítica em rota de ação territorial. Aqui você encontra os fluxos mais relevantes entre origem e destino, com base no score do modelo, na vulnerabilidade regional e na demanda estimada, para apoiar decisões de redistribuição e logística."),
            html.Div(
                [
                    html.Div([html.Label("Região", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-regiao-fluxo", multi=True, placeholder="Todas as regiões")], style={"flex": "1", "minWidth": "260px"}),
                    html.Div([html.Label("Prioridade mínima", style={"fontWeight": "600"}), dcc.Slider(id="filtro-prioridade", min=0, max=1, step=0.05, value=0.3, marks={0: "0", 0.3: "0.3", 0.6: "0.6", 1: "1"})], style={"flex": "2", "minWidth": "320px"}),
                    html.Div([html.Label("Recomendação", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-fluxo-recomendacao", options=[{"label": "Redistribuir", "value": "redistribuir"}, {"label": "Reuso", "value": "reuso"}, {"label": "Recondicionar", "value": "recondicionar"}, {"label": "Descarte", "value": "descarte"}], value=["redistribuir"], multi=True, placeholder="Selecione")], style={"flex": "1", "minWidth": "260px"}),
                ],
                style={**PANEL, "display": "flex", "gap": "18px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-fluxo", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="mapa-fluxo"), style={**PANEL, "marginBottom": "14px"}),
            html.Div([html.H4("Fluxos priorizados"), html.Div("A tabela resume os fluxos com maior score composto, combinando prioridade do modelo, vulnerabilidade territorial e necessidade estimada.", style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"}), tabela("tabela-fluxo", page_size=15)], style=PANEL),
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

        df["score_final"] = (df["score_prioridade"] * 0.6 + df["nivel_vulnerabilidade"] * 0.3 + (df["quantidade_necessaria"].fillna(0) / 10) * 0.1)
        df["score_final"] = df["score_final"] / df["score_final"].max()
        df = df[df["score_final"] >= prioridade]
        df = df.sort_values("score_final", ascending=False).head(200)
        df = df.groupby("destino").head(5)
        df = df.dropna(subset=["lat_origem", "lon_origem", "lat_destino", "lon_destino"])

        total = len(df)
        destinos = df["destino"].nunique()
        regioes_total = len(set(df["REGIAO_ORIGEM"].dropna().tolist()) | set(df["REGIAO_DESTINO"].dropna().tolist()))
        prioridade_media = round(df["score_final"].mean(), 2) if total else 0

        cards = [
            card("Fluxos", total, "priorizados", "#2563eb"),
            card("Regiões", regioes_total, "origem ou destino no filtro", "#7c3aed"),
            card("Destinos", destinos, "municípios", "#16a34a"),
            card("Score médio", prioridade_media, "inteligente", "#dc2626"),
        ]

        fig = montar_mapa_fluxo(df)
        tabela_df = df[["REGIAO_ORIGEM", "origem", "REGIAO_DESTINO", "destino", "tipo_equipamento", "score_final", "recomendacao"]].rename(columns={"REGIAO_ORIGEM": "Região origem", "REGIAO_DESTINO": "Região destino", "origem": "Origem", "destino": "Destino", "tipo_equipamento": "Equipamento", "score_final": "Score", "recomendacao": "Recomendação"})
        return cards, fig, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
