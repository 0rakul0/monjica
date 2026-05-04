from dash import Input, Output, dcc, html

from services.caps_service import preparar_saida_caps
from ui.components import box_titulo, dropdown_filtro, secao_filtros, tabela_padrao
from ui.styles import GRAPH_BOX_STYLE, SECTION_STYLE


def layout_caps(opcoes_municipios, opcoes_regioes, opcoes_tipos):
    return html.Div([
        secao_filtros(
            dropdown_filtro("filtro-caps-municipio", "Município", opcoes_municipios),
            dropdown_filtro("filtro-caps-regiao", "Região", opcoes_regioes),
            dropdown_filtro("filtro-caps-tipo", "Tipo de CAPS", opcoes_tipos),
        ),
        html.Div(box_titulo("Rede CAPS do estado", "Mapa e distribuição das unidades CAPS por tipo, município e região.") + [html.Div(id="cards-rede-caps", style={"display": "flex", "gap": "12px", "flexWrap": "wrap"})], style=SECTION_STYLE),
        html.Div(dcc.Graph(id="mapa-unidades-caps"), style=GRAPH_BOX_STYLE),
        html.Div([
            html.Div(dcc.Graph(id="grafico-tipo-caps"), style={"flex": "1", "minWidth": "360px"}),
            html.Div(dcc.Graph(id="grafico-regiao-caps"), style={"flex": "1", "minWidth": "360px"}),
        ], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
        html.Div([
            html.Div(box_titulo("Quantitativo por tipo de CAPS") + [tabela_padrao("tabela-tipo-caps")], style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"}),
            html.Div(box_titulo("Resumo por região de saúde") + [tabela_padrao("tabela-regiao-caps")], style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"}),
            html.Div(box_titulo("Unidades CAPS") + [tabela_padrao("tabela-unidades-caps", page_size=12)], style={**SECTION_STYLE, "width": "100%"}),
        ]),
    ], style={"paddingTop": "18px"})


def registrar_callbacks(app, caps_df, geo_municipios):
    @app.callback(
        Output("cards-rede-caps", "children"),
        Output("mapa-unidades-caps", "figure"),
        Output("grafico-tipo-caps", "figure"),
        Output("grafico-regiao-caps", "figure"),
        Output("tabela-tipo-caps", "columns"),
        Output("tabela-tipo-caps", "data"),
        Output("tabela-regiao-caps", "columns"),
        Output("tabela-regiao-caps", "data"),
        Output("tabela-unidades-caps", "columns"),
        Output("tabela-unidades-caps", "data"),
        Input("filtro-caps-municipio", "value"),
        Input("filtro-caps-regiao", "value"),
        Input("filtro-caps-tipo", "value"),
    )
    def atualizar(municipios, regioes, tipos):
        saida = preparar_saida_caps(caps_df, geo_municipios, municipios, regioes, tipos)
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
