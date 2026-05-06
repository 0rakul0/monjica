from dash import Dash, dcc, html

from paginas import (
    clinicas_familia,
    fluxo_redistribuicao,
    hospitais,
    monjica,
    unidades_saude,
    visao_geral,
)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "MONJICA - Inventario e Redistribuicao"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1(
                    "MONJICA - Piloto RJ de Reaproveitamento em Saude",
                    style={"margin": "0 0 4px 0", "fontSize": "30px"},
                ),
                html.Div(
                    "Diagnostico territorial, triagem tecnica e redistribuicao inteligente de equipamentos medico-hospitalares na rede publica do Rio de Janeiro.",
                    style={"color": "#475569", "fontSize": "15px"},
                ),
            ],
            style={"marginBottom": "18px"},
        ),
        dcc.Tabs(
            value="tab-visao-geral",
            children=[
                dcc.Tab(label="Visao geral", value="tab-visao-geral", children=[visao_geral.layout()]),
                dcc.Tab(label="Hospitais", value="tab-hospitais", children=[hospitais.layout()]),
                dcc.Tab(label="Clinicas da Familia", value="tab-clinicas-familia", children=[clinicas_familia.layout()]),
                dcc.Tab(label="Unidades de saude", value="tab-unidades-saude", children=[unidades_saude.layout()]),
                dcc.Tab(label="Inteligencia MONJICA", value="tab-monjica", children=[monjica.layout()]),
                dcc.Tab(label="Fluxo de Redistribuicao", value="tab-fluxo", children=[fluxo_redistribuicao.layout()]),
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

visao_geral.register_callbacks(app)
hospitais.register_callbacks(app)
clinicas_familia.register_callbacks(app)
unidades_saude.register_callbacks(app)
monjica.register_callbacks(app)
fluxo_redistribuicao.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8053)
