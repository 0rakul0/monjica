from dash import Input, Output, dcc, html

from services.srts_service import preparar_saida_srts
from ui.components import box_titulo, dropdown_filtro, secao_filtros, tabela_padrao
from ui.styles import GRAPH_BOX_STYLE, SECTION_STYLE


def layout_srts(opcoes_municipios, opcoes_regioes, opcoes_caps):
    return html.Div([
        secao_filtros(
            dropdown_filtro("filtro-srt-municipio", "Município", opcoes_municipios),
            dropdown_filtro("filtro-srt-regiao", "Região", opcoes_regioes),
            dropdown_filtro(
                "filtro-srt-tipo",
                "Tipo",
                [
                    {"label": "RTs", "value": "RTs"},
                    {"label": "UAI", "value": "UAI"},
                    {"label": "UAA", "value": "UAA"},
                ],
            ),
            dropdown_filtro("filtro-srt-caps", "TIPO_CAPS", opcoes_caps),
        ),
        html.Div(
            box_titulo("RTs / UAI / UAA", "Cada mapa destaca apenas os municípios com aquele recurso.")
            + [html.Div(id="cards-srt", style={"display": "flex", "gap": "12px", "flexWrap": "wrap"})],
            style=SECTION_STYLE,
        ),

        html.Div([
            html.Div(dcc.Graph(id="mapa-srt-rts", config={"displayModeBar": True, "displaylogo": False}), style={"flex": "1", "minWidth": "360px"}),
            html.Div(dcc.Graph(id="mapa-srt-uai", config={"displayModeBar": True, "displaylogo": False}), style={"flex": "1", "minWidth": "360px"}),
            html.Div(dcc.Graph(id="mapa-srt-uaa", config={"displayModeBar": True, "displaylogo": False}), style={"flex": "1", "minWidth": "360px"}),
        ], style={**GRAPH_BOX_STYLE, "display": "flex", "gap": "12px", "flexWrap": "wrap"}),

        html.Div([
            html.Div(dcc.Graph(id="grafico-srt-tipo"), style={"flex": "1", "minWidth": "360px"}),
            html.Div(dcc.Graph(id="grafico-srt-regiao"), style={"flex": "1", "minWidth": "360px"}),
        ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),

        html.Div([
            html.Div(
                box_titulo("Resumo por tipo") + [tabela_padrao("tabela-srt-tipo")],
                style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"},
            ),
            html.Div(
                box_titulo("Unidades RTs / UAI / UAA") + [tabela_padrao("tabela-srt-unidades", page_size=12)],
                style={**SECTION_STYLE, "width": "100%"},
            ),
        ]),
    ], style={"paddingTop": "18px"})


def registrar_callbacks(app, srt_df, geo_municipios):
    @app.callback(
        Output("cards-srt", "children"),
        Output("mapa-srt-rts", "figure"),
        Output("mapa-srt-uai", "figure"),
        Output("mapa-srt-uaa", "figure"),
        Output("grafico-srt-tipo", "figure"),
        Output("grafico-srt-regiao", "figure"),
        Output("tabela-srt-tipo", "columns"),
        Output("tabela-srt-tipo", "data"),
        Output("tabela-srt-unidades", "columns"),
        Output("tabela-srt-unidades", "data"),
        Input("filtro-srt-municipio", "value"),
        Input("filtro-srt-regiao", "value"),
        Input("filtro-srt-tipo", "value"),
        Input("filtro-srt-caps", "value"),
    )
    def atualizar(municipios, regioes, tipos, caps):
        saida = preparar_saida_srts(
            srt_df,
            geo_municipios,
            municipios=municipios,
            regioes=regioes,
            tipos=tipos,
            tipos_caps=caps,
        )
        return (
            saida["cards"],
            saida["fig_mapa_rts"],
            saida["fig_mapa_uai"],
            saida["fig_mapa_uaa"],
            saida["fig_tipo"],
            saida["fig_regiao"],
            [{"name": c, "id": c} for c in saida["resumo_tipo"].columns],
            saida["resumo_tipo"].to_dict("records"),
            [{"name": c, "id": c} for c in saida["unidades"].columns],
            saida["unidades"].to_dict("records"),
        )