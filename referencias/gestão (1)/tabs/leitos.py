from dash import Input, Output, dcc, html

from services.leitos_service import preparar_saida_leitos
from ui.components import box_titulo, dropdown_filtro, secao_filtros, tabela_padrao
from ui.styles import GRAPH_BOX_STYLE, SECTION_STYLE


def layout_leitos(opcoes_municipios, opcoes_regioes, opcoes_tipos):
    return html.Div([
        secao_filtros(
            dropdown_filtro("filtro-leitos-municipio", "Município", opcoes_municipios),
            dropdown_filtro("filtro-leitos-regiao", "Região", opcoes_regioes),
            dropdown_filtro("filtro-leitos-tipo", "Tipo", opcoes_tipos),
        ),
        html.Div(box_titulo("Rede de leitos do estado", "Mapa e distribuição dos leitos por tipo, município e região.") + [html.Div(id="cards-rede-leitos", style={"display": "flex", "gap": "12px", "flexWrap": "wrap"})], style=SECTION_STYLE),
        html.Div(dcc.Graph(id="mapa-unidades-leitos"), style=GRAPH_BOX_STYLE),
        html.Div([
            html.Div(dcc.Graph(id="grafico-tipo-leitos"), style={"flex": "1", "minWidth": "360px"}),
            html.Div(dcc.Graph(id="grafico-regiao-leitos"), style={"flex": "1", "minWidth": "360px"}),
        ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
        html.Div([
            html.Div(box_titulo("Quantitativo por tipo de leito") + [tabela_padrao("tabela-tipo-leitos")], style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"}),
            html.Div(box_titulo("Resumo por região de saúde") + [tabela_padrao("tabela-regiao-leitos")], style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"}),
            html.Div(box_titulo("Unidades de leitos") + [tabela_padrao("tabela-unidades-leitos", page_size=12)], style={**SECTION_STYLE, "width": "100%"}),
        ]),
    ], style={"paddingTop": "18px"})


def registrar_callbacks(app, leitos_df, geo_municipios):
    @app.callback(
        Output("cards-rede-leitos", "children"),
        Output("mapa-unidades-leitos", "figure"),
        Output("grafico-tipo-leitos", "figure"),
        Output("grafico-regiao-leitos", "figure"),
        Output("tabela-tipo-leitos", "columns"),
        Output("tabela-tipo-leitos", "data"),
        Output("tabela-regiao-leitos", "columns"),
        Output("tabela-regiao-leitos", "data"),
        Output("tabela-unidades-leitos", "columns"),
        Output("tabela-unidades-leitos", "data"),
        Input("filtro-leitos-municipio", "value"),
        Input("filtro-leitos-regiao", "value"),
        Input("filtro-leitos-tipo", "value"),
    )
    def atualizar(municipios, regioes, tipos):
        saida = preparar_saida_leitos(leitos_df, geo_municipios, municipios, regioes, tipos)
        return (
            saida["cards"],
            saida["fig_mapa"],
            saida["fig_tipo"],
            saida["fig_regiao"],
            [{"name": c, "id": c} for c in saida["resumo_tipo"].columns],
            saida["resumo_tipo"].to_dict("records"),
            [{"name": c, "id": c} for c in saida["resumo_regiao"].columns],
            saida["resumo_regiao"].to_dict("records"),
            [{"name": c, "id": c} for c in saida["unidades"].columns],
            saida["unidades"].to_dict("records"),
        )
