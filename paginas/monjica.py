import plotly.express as px
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, carregar_monjica, fig_vazia, secao_intro, tabela


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
            html.Div(
                [
                    html.Div(dcc.Graph(id="grafico-prioridade"), style={"flex": "1", "minWidth": "360px"}),
                    html.Div(dcc.Graph(id="grafico-regiao-monjica"), style={"flex": "1", "minWidth": "360px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
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
        Output("grafico-prioridade", "figure"),
        Output("grafico-regiao-monjica", "figure"),
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
            return [], vazio, vazio, [], []

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
                x="score_medio",
                y="REGIAO_ORIGEM",
                orientation="h",
                text="equipamentos",
                color="REGIAO_ORIGEM",
                title="Score medio por regiao de origem",
            )
            if not regiao_df.empty
            else fig_vazia("Sem dados regionais")
        )
        fig_regiao.update_layout(height=460, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

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
            fig_prioridade,
            fig_regiao,
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
