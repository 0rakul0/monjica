import plotly.express as px
from dash import Input, Output, dcc, html

from services.cobertura_service import preparar_saida_cobertura
from ui.components import box_titulo, dropdown_filtro, secao_filtros, tabela_padrao
from ui.styles import GRAPH_BOX_STYLE, SECTION_STYLE


def layout_cobertura(opcoes_municipios):
    return html.Div([
        secao_filtros(
            dropdown_filtro("filtro-cob-status", "Status CAPS", [{"label": "Com CAPS", "value": "Com CAPS"}, {"label": "Sem CAPS", "value": "Sem CAPS"}]),
            dropdown_filtro("filtro-cob-municipio", "Município", opcoes_municipios),
        ),
        html.Div(box_titulo("Cobertura do estado", "Municípios com CAPS (verde) e sem CAPS (vermelho).") + [html.Div(id="cards-cobertura-municipal", style={"display": "flex", "gap": "12px", "flexWrap": "wrap"})], style=SECTION_STYLE),
        html.Div(dcc.Graph(id="mapa-caps-municipio"), style=GRAPH_BOX_STYLE),
        html.Div([html.Div(dcc.Graph(id="grafico-cobertura-regiao"), style={"flex": "1", "minWidth": "360px"})], style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
        html.Div([
            html.Div(box_titulo("Municípios com CAPS") + [tabela_padrao("tabela-caps-por-municipio")], style={**SECTION_STYLE, "width": "100%", "marginBottom": "16px"}),
            html.Div(box_titulo("Municípios sem CAPS") + [tabela_padrao("tabela-municipios-sem-caps")], style={**SECTION_STYLE, "width": "100%"}),
        ]),
    ])


def registrar_callbacks(app, geo_municipios, caps_df):
    @app.callback(
        Output("cards-cobertura-municipal", "children"),
        Output("mapa-caps-municipio", "figure"),
        Output("grafico-cobertura-regiao", "figure"),
        Output("tabela-caps-por-municipio", "columns"),
        Output("tabela-caps-por-municipio", "data"),
        Output("tabela-municipios-sem-caps", "columns"),
        Output("tabela-municipios-sem-caps", "data"),
        Input("filtro-cob-status", "value"),
        Input("filtro-cob-municipio", "value"),
    )
    def atualizar(status_caps, municipios_sel):
        saida = preparar_saida_cobertura(geo_municipios, caps_df, status_caps, municipios_sel)
        com_caps = saida["com_caps"]
        sem_caps = saida["sem_caps"]
        return (
            saida["cards"],
            saida["fig_mapa"],
            saida["fig_regiao"],
            [{"name": c, "id": c} for c in com_caps.columns],
            com_caps.to_dict("records"),
            [{"name": c, "id": c} for c in sem_caps.columns],
            sem_caps.to_dict("records"),
        )
