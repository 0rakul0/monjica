from dash import Dash, dcc, html

from config import APP_TITLE, PORT
from ui.styles import APP_STYLE, BRANCO, AZUL, ROXO, LARANJA
from database.consultas import (
    carregar_caps_db,
    carregar_leitos_db,
    carregar_srts_db,
    carregar_geo_municipios_db,
)
from tabs.cobertura import layout_cobertura, registrar_callbacks as registrar_callbacks_cobertura
from tabs.caps import layout_caps, registrar_callbacks as registrar_callbacks_caps
from tabs.leitos import layout_leitos, registrar_callbacks as registrar_callbacks_leitos
from tabs.srts import layout_srts, registrar_callbacks as registrar_callbacks_srts


caps_df = carregar_caps_db()
leitos_df = carregar_leitos_db()
srts_df = carregar_srts_db()
geo_municipios = carregar_geo_municipios_db()


opcoes_municipios_cobertura = (
    [{"label": c, "value": c} for c in sorted(geo_municipios["MUNICIPIO_CAPS"].dropna().unique())]
    if not geo_municipios.empty and "MUNICIPIO_CAPS" in geo_municipios.columns
    else []
)

opcoes_municipios_caps = (
    [{"label": c, "value": c} for c in sorted(caps_df["MUNICIPIO_CAPS"].dropna().unique())]
    if not caps_df.empty and "MUNICIPIO_CAPS" in caps_df.columns
    else []
)
opcoes_regioes_caps = (
    [{"label": c, "value": c} for c in sorted(caps_df["REGIAO_CAPS"].dropna().unique())]
    if not caps_df.empty and "REGIAO_CAPS" in caps_df.columns
    else []
)
opcoes_tipos_caps = (
    [{"label": c, "value": c} for c in sorted(caps_df["TIPO_CAPS"].dropna().unique())]
    if not caps_df.empty and "TIPO_CAPS" in caps_df.columns
    else []
)

opcoes_municipios_leitos = (
    [{"label": c, "value": c} for c in sorted(leitos_df["MUNICIPIO_UNIDADE"].dropna().unique())]
    if not leitos_df.empty and "MUNICIPIO_UNIDADE" in leitos_df.columns
    else []
)
opcoes_regioes_leitos = (
    [{"label": c, "value": c} for c in sorted(leitos_df["REGIAO_UNIDADE"].dropna().unique())]
    if not leitos_df.empty and "REGIAO_UNIDADE" in leitos_df.columns
    else []
)
opcoes_tipos_leitos = (
    [{"label": c, "value": c} for c in sorted(leitos_df["TIPO_UNIDADE"].dropna().unique())]
    if not leitos_df.empty and "TIPO_UNIDADE" in leitos_df.columns
    else []
)

opcoes_municipios_srt = (
    [{"label": c, "value": c} for c in sorted(srts_df["MUNICIPIO_UNIDADE"].dropna().unique())]
    if not srts_df.empty and "MUNICIPIO_UNIDADE" in srts_df.columns
    else []
)
opcoes_regioes_srt = (
    [{"label": c, "value": c} for c in sorted(srts_df["REGIAO_UNIDADE"].dropna().unique())]
    if not srts_df.empty and "REGIAO_UNIDADE" in srts_df.columns
    else []
)
opcoes_caps_srt = (
    [{"label": c, "value": c} for c in sorted(srts_df["TIPO_CAPS"].dropna().unique())]
    if not srts_df.empty and "TIPO_CAPS" in srts_df.columns
    else []
)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = APP_TITLE

app.layout = html.Div(
    [
        html.H1("Painel de Interseção CAPS", style={"marginBottom": "6px"}),
        html.Div(
            "Estrutura modular: cada aba em um script, com filtros próprios e consultas centralizadas no banco.",
            style={"color": "#4b5563", "marginBottom": "18px"},
        ),
        dcc.Tabs(
            id="tabs-principais",
            value="tab-cobertura",
            children=[
                dcc.Tab(
                    label="Cobertura do estado",
                    value="tab-cobertura",
                    style={"padding": "12px", "fontWeight": "600", "backgroundColor": BRANCO},
                    selected_style={
                        "padding": "12px",
                        "fontWeight": "700",
                        "backgroundColor": "#eff6ff",
                        "color": AZUL,
                    },
                    children=[layout_cobertura(opcoes_municipios_cobertura)],
                ),
                dcc.Tab(
                    label="Onde estão os CAPS",
                    value="tab-caps",
                    style={"padding": "12px", "fontWeight": "600", "backgroundColor": BRANCO},
                    selected_style={
                        "padding": "12px",
                        "fontWeight": "700",
                        "backgroundColor": "#f5f3ff",
                        "color": ROXO,
                    },
                    children=[layout_caps(opcoes_municipios_caps, opcoes_regioes_caps, opcoes_tipos_caps)],
                ),
                dcc.Tab(
                    label="Onde estão os leitos",
                    value="tab-leitos",
                    style={"padding": "12px", "fontWeight": "600", "backgroundColor": BRANCO},
                    selected_style={
                        "padding": "12px",
                        "fontWeight": "700",
                        "backgroundColor": "#ecfeff",
                        "color": "#0f766e",
                    },
                    children=[layout_leitos(opcoes_municipios_leitos, opcoes_regioes_leitos, opcoes_tipos_leitos)],
                ),
                dcc.Tab(
                    label="RTs / UAI / UAA",
                    value="tab-srts",
                    style={"padding": "12px", "fontWeight": "600", "backgroundColor": BRANCO},
                    selected_style={
                        "padding": "12px",
                        "fontWeight": "700",
                        "backgroundColor": "#fff7ed",
                        "color": LARANJA,
                    },
                    children=[layout_srts(opcoes_municipios_srt, opcoes_regioes_srt, opcoes_caps_srt)],
                 ),
            ],
        ),
    ],
    style=APP_STYLE,
)

registrar_callbacks_cobertura(app, geo_municipios, caps_df)
registrar_callbacks_caps(app, caps_df, geo_municipios)
registrar_callbacks_leitos(app, leitos_df, geo_municipios)
registrar_callbacks_srts(app, srts_df, geo_municipios)

if __name__ == "__main__":
    app.run(debug=True, port=PORT)