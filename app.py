from dash import Dash, dcc, html

from paginas import (
    visao_geral,
    hospitais,
    unidades_saude,
    monjica,
    fluxo_redistribuicao,
)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "MONJICA - Inventário e Redistribuição"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    "MONJICA - Inventário Hospitalar Inteligente",
                    style={"margin": "0 0 4px 0", "fontSize": "30px"},
                ),
                html.Div(
                    "Triagem, monitoramento e redistribuição inteligente de equipamentos médico-hospitalares.",
                    style={"color": "#475569", "fontSize": "15px"},
                ),
            ],
            style={"marginBottom": "18px"},
        ),

        dcc.Tabs(
            value="tab-visao-geral",
            children=[
                dcc.Tab(
                    label="Visão geral",
                    value="tab-visao-geral",
                    children=[visao_geral.layout()],
                ),
                dcc.Tab(
                    label="Hospitais",
                    value="tab-hospitais",
                    children=[hospitais.layout()],
                ),
                dcc.Tab(
                    label="Unidades de saúde",
                    value="tab-unidades-saude",
                    children=[unidades_saude.layout()],
                ),
                dcc.Tab(
                    label="Inteligência MONJICA",
                    value="tab-monjica",
                    children=[monjica.layout()],
                ),
                dcc.Tab(
                    label="Fluxo de Redistribuição",
                    value="tab-fluxo",
                    children=[fluxo_redistribuicao.layout()],
                ),
            ],
        ),
    ],
    style={
        "backgroundColor": "#f8fafc",
        "minHeight": "100vh",
        "padding": "18px",
        "fontFamily": "Arial, sans-serif",
        "color": "#111827",
    },
)

# Registra callbacks de cada página
visao_geral.register_callbacks(app)
hospitais.register_callbacks(app)
unidades_saude.register_callbacks(app)
monjica.register_callbacks(app)
fluxo_redistribuicao.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8053)
