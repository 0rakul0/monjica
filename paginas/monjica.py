import plotly.express as px
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_monjica, fig_vazia, secao_intro, tabela


def layout():
    return html.Div(
        [
            secao_intro(
                "Inteligência MONJICA",
                "Esta etapa concentra a camada analítica do projeto. Aqui você encontra a priorização dos equipamentos "
                "processados pelo modelo, com recomendações de redistribuição, reuso, recondicionamento ou descarte, "
                "sempre como apoio à decisão e não como substituto da validação institucional e técnica.",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Recomendação", style={"fontWeight": "600"}),
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
                        style={"minWidth": "250px"},
                    )
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "marginBottom": "14px"},
            ),
            html.Div(id="cards-monjica", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="grafico-prioridade"), style={**PANEL, "marginBottom": "14px"}),
            html.Div(
                [
                    html.H4("Equipamentos priorizados"),
                    html.Div(
                        "A tabela abaixo mostra os equipamentos analisados com seus scores e explicações do modelo para facilitar triagem técnica e governança.",
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
        Output("cards-monjica", "children"),
        Output("grafico-prioridade", "figure"),
        Output("tabela-monjica", "columns"),
        Output("tabela-monjica", "data"),
        Input("filtro-recomendacao", "value"),
    )
    def atualizar_monjica(filtro):
        df = carregar_monjica()
        if filtro:
            df = df[df["recomendacao"].isin(filtro)]

        if df.empty:
            return [], fig_vazia("Sem dados MONJICA"), [], []

        total = len(df)
        redistribuir = len(df[df["recomendacao"] == "redistribuir"])
        reuso = len(df[df["recomendacao"] == "reuso"])
        recondicionar = len(df[df["recomendacao"] == "recondicionar"])
        descarte = len(df[df["recomendacao"] == "descarte"])

        cards = [
            card("Equipamentos analisados", f"{total}", "processados pelo MONJICA", "#2563eb"),
            card("Redistribuição prioritária", f"{redistribuir}", "alta prioridade social", "#dc2626"),
            card("Reuso direto", f"{reuso}", "baixo custo de reaproveitamento", "#16a34a"),
            card("Recondicionar", f"{recondicionar}", "requer triagem técnica", "#f59e0b"),
            card("Descarte", f"{descarte}", "baixa viabilidade de reuso", "#64748b"),
        ]

        top = df.sort_values("score_prioridade", ascending=False).head(20)
        fig = px.bar(top, x="score_prioridade", y="tipo_equipamento", color="recomendacao", orientation="h", title="Top equipamentos por prioridade")
        fig.update_layout(height=500, margin=dict(l=10, r=10, t=50, b=10))

        tabela_df = df[
            [
                "tipo_equipamento",
                "estado_atual",
                "origem",
                "score_reuso",
                "score_criticidade",
                "score_prioridade",
                "recomendacao",
                "explicacao_modelo",
            ]
        ].sort_values("score_prioridade", ascending=False)

        return cards, fig, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
