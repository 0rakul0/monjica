from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html


BASE_DIR = Path(__file__).resolve().parent
DATA_ENTRADA = BASE_DIR / "data" / "entrada" / "hospitais_inventario.csv"
INVENTARIO_EQUIPAMENTOS = BASE_DIR / "data" / "entrada" / "inventario_equipamentos_municipais_rj_cnes_202603.csv"
REFERENCIA_LOCAL_HOSPITAIS = BASE_DIR / "data" / "entrada" / "referencia_local_hospitais.csv"
UNIDADES_SAUDE = BASE_DIR / "data" / "entrada" / "unidades_saude_municipais_rj_cnes_202603.csv"
REFERENCIA_XLSX = BASE_DIR / "referencias" / "gestão (1)" / "dados" / "brutos" / "endereço_caps.xlsx"
MUNICIPIOS_SHP = BASE_DIR / "referencias" / "gestão (1)" / "dados" / "territoriais" / "RJ_Municipios_2024.shp"

COLUNAS_BASE = [
    "ID_HOSPITAL",
    "NOME_HOSPITAL",
    "ESFERA",
    "ENDERECO",
    "MUNICIPIO",
    "REGIAO",
    "LAT",
    "LON",
    "LEITOS",
    "EQUIPAMENTOS_TOTAL",
    "OPERACIONAIS",
    "OCIOSOS",
    "MANUTENCAO",
    "DESCARTE",
    "POTENCIAL_REAPROVEITAMENTO",
    "SCORE_REAPROVEITAMENTO",
]

CARD_CONTAINER = {"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"}
PANEL = {"backgroundColor": "#ffffff", "border": "1px solid #e5e7eb", "borderRadius": "8px", "padding": "14px"}


def normalizar_coord(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip().replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return None
    while abs(numero) > 180:
        numero = numero / 10
    return numero


def chave_cnes(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto.zfill(7)


def inferir_esfera(nome):
    texto = str(nome or "").upper()
    if "ESTADUAL" in texto or "INSTITUTO ESTADUAL" in texto:
        return "Estadual"
    if "MUNICIPAL" in texto or "MUNIPAL" in texto:
        return "Municipal"
    return "A classificar"


def inferir_potencial(row):
    ociosos = row.get("OCIOSOS", 0) or 0
    manutencao = row.get("MANUTENCAO", 0) or 0
    descarte = row.get("DESCARTE", 0) or 0
    total = row.get("EQUIPAMENTOS_TOTAL", 0) or 0
    if total <= 0:
        return "Inventario pendente"
    taxa = (ociosos + manutencao) / total
    if descarte / total >= 0.5:
        return "Baixo"
    if taxa >= 0.3:
        return "Alto"
    if taxa >= 0.1:
        return "Medio"
    return "Baixo"


def calcular_score(row):
    total = row.get("EQUIPAMENTOS_TOTAL", 0) or 0
    if total <= 0:
        return 0
    ociosos = row.get("OCIOSOS", 0) or 0
    manutencao = row.get("MANUTENCAO", 0) or 0
    descarte = row.get("DESCARTE", 0) or 0
    score = ((ociosos * 1.0) + (manutencao * 0.6) - (descarte * 0.4)) / total
    return max(0, min(100, round(score * 100, 1)))


def inferir_porte(row):
    leitos = int(row.get("LEITOS", 0) or 0)
    equipamentos = int(row.get("EQUIPAMENTOS_TOTAL", 0) or 0)
    if leitos > 0:
        if leitos <= 50:
            return "Pequeno porte", "classificado por leitos CNES"
        if leitos <= 150:
            return "Medio porte", "classificado por leitos CNES"
        return "Grande porte", "classificado por leitos CNES"
    if equipamentos <= 50:
        return "Pequeno porte", "estimativa preliminar por inventario"
    if equipamentos <= 200:
        return "Medio porte", "estimativa preliminar por inventario"
    return "Grande porte", "estimativa preliminar por inventario"


def carregar_hospitais():
    if DATA_ENTRADA.exists():
        df = pd.read_csv(DATA_ENTRADA, dtype={"ID_HOSPITAL": str})
    elif REFERENCIA_XLSX.exists():
        df_ref = pd.read_excel(REFERENCIA_XLSX, sheet_name="leitos")
        df = pd.DataFrame(
            {
                "ID_HOSPITAL": df_ref.get("id_hospital"),
                "NOME_HOSPITAL": df_ref.get("Hospital"),
                "ESFERA": df_ref.get("Hospital").apply(inferir_esfera),
                "ENDERECO": df_ref.get("Endereço"),
                "MUNICIPIO": df_ref.get("Município"),
                "REGIAO": df_ref.get("Região").ffill(),
                "LAT": df_ref.get("LAT"),
                "LON": df_ref.get("LOG"),
                "LEITOS": df_ref.get("Leitos"),
                "EQUIPAMENTOS_TOTAL": 0,
                "OPERACIONAIS": 0,
                "OCIOSOS": 0,
                "MANUTENCAO": 0,
                "DESCARTE": 0,
                "POTENCIAL_REAPROVEITAMENTO": "Inventario pendente",
                "SCORE_REAPROVEITAMENTO": 0,
            }
        )
    else:
        df = pd.DataFrame(columns=COLUNAS_BASE)

    for coluna in COLUNAS_BASE:
        if coluna not in df.columns:
            df[coluna] = 0 if coluna in {"LEITOS", "EQUIPAMENTOS_TOTAL", "OPERACIONAIS", "OCIOSOS", "MANUTENCAO", "DESCARTE", "SCORE_REAPROVEITAMENTO"} else "Nao informado"

    df["ID_HOSPITAL"] = df["ID_HOSPITAL"].apply(chave_cnes)
    df["LAT"] = df["LAT"].apply(normalizar_coord)
    df["LON"] = df["LON"].apply(normalizar_coord)
    for coluna in ["LEITOS", "EQUIPAMENTOS_TOTAL", "OPERACIONAIS", "OCIOSOS", "MANUTENCAO", "DESCARTE"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)

    df["ESFERA"] = df["ESFERA"].fillna("A classificar").replace("", "A classificar")
    df["POTENCIAL_REAPROVEITAMENTO"] = df.apply(inferir_potencial, axis=1)
    df["SCORE_REAPROVEITAMENTO"] = df.apply(calcular_score, axis=1)
    df["MUNICIPIO"] = df["MUNICIPIO"].fillna("Nao informado")
    df["REGIAO"] = df["REGIAO"].fillna("Nao informada")
    df["ENDERECO"] = df["ENDERECO"].fillna("Nao informado")
    df["NOME_HOSPITAL"] = df["NOME_HOSPITAL"].fillna("Nao informado")
    porte = df.apply(inferir_porte, axis=1, result_type="expand")
    df["PORTE"] = porte[0]
    df["CRITERIO_PORTE"] = porte[1]
    return df.dropna(subset=["LAT", "LON"]).copy()


def carregar_inventario_equipamentos():
    colunas = [
        "CO_CNES",
        "NO_FANTASIA",
        "NO_MUNICIPIO",
        "DS_TIPO_EQUIPAMENTO",
        "DS_EQUIPAMENTO",
        "QT_EXISTENTE",
        "QT_USO",
        "QT_SUS",
        "QT_OCIOSO_ESTIMADO",
    ]
    if not INVENTARIO_EQUIPAMENTOS.exists():
        return pd.DataFrame(columns=colunas)
    df = pd.read_csv(INVENTARIO_EQUIPAMENTOS, dtype={"CO_CNES": str})
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = 0 if coluna.startswith("QT_") else "Nao informado"
    df["CO_CNES"] = df["CO_CNES"].apply(chave_cnes)
    for coluna in ["QT_EXISTENTE", "QT_USO", "QT_SUS", "QT_OCIOSO_ESTIMADO"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)
    df["MANUTENCAO"] = 0
    df["DESCARTE"] = 0
    df["PARA_INSTALACAO"] = 0
    return df


def carregar_referencia_local():
    if not REFERENCIA_LOCAL_HOSPITAIS.exists():
        return pd.DataFrame(columns=["ID_HOSPITAL"])
    df = pd.read_csv(REFERENCIA_LOCAL_HOSPITAIS, dtype={"ID_HOSPITAL": str})
    df["ID_HOSPITAL"] = df["ID_HOSPITAL"].apply(chave_cnes)
    df = df.rename(columns={"LAT": "LAT_REFERENCIA", "LOG": "LON_REFERENCIA"})
    if "LEITOS_REFERENCIA" in df.columns:
        df["LEITOS_REFERENCIA"] = pd.to_numeric(df["LEITOS_REFERENCIA"], errors="coerce").fillna(0).astype(int)
    return df


def carregar_unidades_saude():
    colunas = [
        "CO_CNES",
        "NO_FANTASIA",
        "NO_RAZAO_SOCIAL",
        "CATEGORIA_UNIDADE",
        "DS_TIPO_ESTABELECIMENTO",
        "ENDERECO",
        "NO_BAIRRO",
        "NO_MUNICIPIO",
        "NU_TELEFONE",
        "NO_EMAIL",
        "LAT",
        "LON",
    ]
    if not UNIDADES_SAUDE.exists():
        return pd.DataFrame(columns=colunas)
    df = pd.read_csv(UNIDADES_SAUDE, dtype={"CO_CNES": str})
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = "Nao informado"
    df["CO_CNES"] = df["CO_CNES"].apply(chave_cnes)
    df["LAT"] = df["LAT"].apply(normalizar_coord)
    df["LON"] = df["LON"].apply(normalizar_coord)
    df["NO_MUNICIPIO"] = df["NO_MUNICIPIO"].fillna("Nao informado")
    df["CATEGORIA_UNIDADE"] = df["CATEGORIA_UNIDADE"].fillna("Nao classificada")
    return df.dropna(subset=["LAT", "LON"]).copy()


def carregar_municipios():
    if not MUNICIPIOS_SHP.exists():
        return None
    gdf = gpd.read_file(MUNICIPIOS_SHP)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")
    return gdf.to_crs("EPSG:4326")


def fig_vazia(titulo, altura=480):
    fig = go.Figure()
    fig.update_layout(
        title=titulo,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": titulo, "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5, "showarrow": False}],
        height=altura,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def montar_mapa(df, gdf):
    if df.empty:
        return fig_vazia("Sem hospitais com coordenadas para exibir", altura=720)

    fig = go.Figure()
    if gdf is not None and not gdf.empty:
        base = px.choropleth_map(
            gdf,
            geojson=gdf.__geo_interface__,
            locations=gdf.index,
            color_discrete_sequence=["#eef2f7"],
            map_style="carto-positron",
            center={"lat": -22.1, "lon": -42.95},
            zoom=6.4,
            opacity=0.55,
            height=720,
            hover_name="NM_MUN" if "NM_MUN" in gdf.columns else None,
        )
        for trace in base.data:
            trace.marker.line.color = "#64748b"
            trace.marker.line.width = 0.7
            trace.showlegend = False
            fig.add_trace(trace)

    pontos = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="POTENCIAL_REAPROVEITAMENTO",
        size="EQUIPAMENTOS_TOTAL",
        size_max=28,
        hover_name="NOME_HOSPITAL",
        hover_data={
            "ESFERA": True,
            "ENDERECO": True,
            "MUNICIPIO": True,
            "LEITOS": True,
            "EQUIPAMENTOS_TOTAL": True,
            "OCIOSOS": True,
            "MANUTENCAO": True,
            "DESCARTE": True,
            "SCORE_REAPROVEITAMENTO": True,
            "LAT": False,
            "LON": False,
        },
        color_discrete_map={
            "Alto": "#dc2626",
            "Medio": "#f59e0b",
            "Baixo": "#16a34a",
            "Inventario pendente": "#2563eb",
        },
        zoom=6.6,
        center={"lat": -22.1, "lon": -42.95},
        height=720,
    )
    for trace in pontos.data:
        fig.add_trace(trace)

    fig.update_layout(
        title="Mapa de hospitais municipais e estaduais com inventario",
        map={"style": "carto-positron", "center": {"lat": -22.1, "lon": -42.95}, "zoom": 6.6},
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Potencial de reaproveitamento",
    )
    return fig


def montar_mapa_hospital(df_hospitais, cnes_selecionado=None):
    if df_hospitais is None or df_hospitais.empty:
        return fig_vazia("Sem hospitais com coordenadas", altura=420)
    df = df_hospitais.dropna(subset=["LAT", "LON"]).copy()
    if df.empty:
        return fig_vazia("Hospitais sem coordenadas", altura=420)
    df["SELECIONADO"] = df["ID_HOSPITAL"].eq(chave_cnes(cnes_selecionado))
    centro = df[df["SELECIONADO"]].iloc[0] if df["SELECIONADO"].any() else df.iloc[0]
    fig = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="SELECIONADO",
        color_discrete_map={True: "#dc2626", False: "#2563eb"},
        custom_data=["ID_HOSPITAL"],
        hover_name="NOME_HOSPITAL",
        hover_data={"ENDERECO": True, "MUNICIPIO": True, "PORTE": True, "EQUIPAMENTOS_TOTAL": True, "SELECIONADO": False, "LAT": False, "LON": False},
        zoom=8 if len(df) > 1 else 13,
        center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
        height=420,
    )
    fig.update_traces(marker={"size": 14})
    fig.update_layout(
        title="Hospitais da regiao selecionada",
        map={"style": "carto-positron", "center": {"lat": float(centro["LAT"]), "lon": float(centro["LON"])}, "zoom": 8 if len(df) > 1 else 13},
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
    )
    return fig


def card(titulo, valor, detalhe, cor):
    return html.Div(
        [
            html.Div(titulo, style={"fontSize": "12px", "color": "#475569", "marginBottom": "6px"}),
            html.Div(valor, style={"fontSize": "25px", "fontWeight": "700", "color": cor}),
            html.Div(detalhe, style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"}),
        ],
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderLeft": f"6px solid {cor}",
            "borderRadius": "8px",
            "padding": "14px",
            "flex": "1 1 210px",
            "minWidth": "190px",
        },
    )


def texto_ou_nao_informado(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return "Nao informado"
    return str(valor).strip()


def tabela(id_tabela, page_size=12):
    return dash_table.DataTable(
        id=id_tabela,
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        export_format="xlsx",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Arial", "fontSize": "13px", "whiteSpace": "normal", "maxWidth": "360px"},
        style_header={"fontWeight": "700", "backgroundColor": "#f1f5f9"},
    )


hospitais_df = carregar_hospitais()
inventario_df = carregar_inventario_equipamentos()
referencia_local_df = carregar_referencia_local()
if not referencia_local_df.empty:
    hospitais_df = hospitais_df.merge(referencia_local_df, on="ID_HOSPITAL", how="left")
    hospitais_df["REGIAO"] = hospitais_df.get("REGIAO_REFERENCIA", hospitais_df["REGIAO"]).fillna(hospitais_df["REGIAO"])
else:
    hospitais_df["LEITOS_REFERENCIA"] = 0
    hospitais_df["TELEFONE_REFERENCIA"] = "Nao informado"
    hospitais_df["REGIAO_REFERENCIA"] = "Nao informada"
municipios_gdf = carregar_municipios()
unidades_saude_df = carregar_unidades_saude()

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "MVP Inventario Hospitalar"

opcoes_municipios = [{"label": m, "value": m} for m in sorted(hospitais_df["MUNICIPIO"].dropna().unique())]
opcoes_esferas = [{"label": e, "value": e} for e in sorted(hospitais_df["ESFERA"].dropna().unique())]
opcoes_potencial = [{"label": p, "value": p} for p in sorted(hospitais_df["POTENCIAL_REAPROVEITAMENTO"].dropna().unique())]
opcoes_hospitais = [
    {"label": f"{row.NOME_HOSPITAL} - {row.MUNICIPIO}", "value": row.ID_HOSPITAL}
    for row in hospitais_df.sort_values(["MUNICIPIO", "NOME_HOSPITAL"]).itertuples()
]
opcoes_regioes_hospitais = [{"label": r, "value": r} for r in sorted(hospitais_df["REGIAO"].dropna().unique())]
opcoes_tipos_unidades = [{"label": t, "value": t} for t in sorted(unidades_saude_df["CATEGORIA_UNIDADE"].dropna().unique())]
opcoes_municipios_unidades = [{"label": m, "value": m} for m in sorted(unidades_saude_df["NO_MUNICIPIO"].dropna().unique())]


def layout_visao_geral():
    return html.Div(
        [
            html.Div(
                [
                    html.Div([html.Label("Municipio", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-municipio", options=opcoes_municipios, multi=True, placeholder="Todos")], style={"minWidth": "220px", "flex": "1"}),
                    html.Div([html.Label("Esfera", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-esfera", options=opcoes_esferas, multi=True, placeholder="Todas")], style={"minWidth": "220px", "flex": "1"}),
                    html.Div([html.Label("Potencial", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-potencial", options=opcoes_potencial, multi=True, placeholder="Todos")], style={"minWidth": "220px", "flex": "1"}),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-kpi", style=CARD_CONTAINER),
            html.Div(dcc.Graph(id="mapa-hospitais"), style={**PANEL, "padding": "8px", "marginBottom": "14px"}),
            html.Div(
                [
                    html.Div(dcc.Graph(id="grafico-esfera"), style={"flex": "1", "minWidth": "320px"}),
                    html.Div(dcc.Graph(id="grafico-potencial"), style={"flex": "1", "minWidth": "320px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div([html.H3("Base de hospitais e inventario", style={"marginTop": "0"}), tabela("tabela-hospitais", page_size=12)], style=PANEL),
        ]
    )


def layout_hospitais():
    valor_padrao = opcoes_hospitais[0]["value"] if opcoes_hospitais else None
    return html.Div(
        [
            dcc.Store(id="hospital-clicado-mapa"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Regiao", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-regiao-hospital", options=opcoes_regioes_hospitais, placeholder="Todas as regioes"),
                        ],
                        style={"minWidth": "260px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Hospital", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-hospital-detalhe", options=opcoes_hospitais, value=valor_padrao, placeholder="Selecione um hospital"),
                        ],
                        style={"minWidth": "360px", "flex": "2"},
                    ),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-hospital", style=CARD_CONTAINER),
            html.Div(
                [
                    html.Div(dcc.Graph(id="mapa-hospital-detalhe"), style={"flex": "1", "minWidth": "360px"}),
                    html.Div(dcc.Graph(id="grafico-status-hospital"), style={"flex": "1", "minWidth": "360px"}),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(dcc.Graph(id="grafico-tipo-equipamento-hospital"), style={**PANEL, "padding": "8px", "marginBottom": "14px"}),
            html.Div(
                [
                    html.H3("Quantitativo por equipamento", style={"marginTop": "0"}),
                    html.Div(
                        "Manutencao, descarte e para instalacao nao constam no CNES; aparecem zerados ate validacao tecnica ou integracao com sistema de engenharia clinica.",
                        style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"},
                    ),
                    tabela("tabela-equipamentos-hospital", page_size=14),
                ],
                style=PANEL,
            ),
        ]
    )


def layout_unidades_saude():
    return html.Div(
        [
            dcc.Store(id="unidade-clicada-mapa"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Tipo de unidade", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-tipo-unidade", options=opcoes_tipos_unidades, multi=True, placeholder="Todos"),
                        ],
                        style={"minWidth": "260px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Municipio", style={"fontWeight": "600"}),
                            dcc.Dropdown(id="filtro-municipio-unidade", options=opcoes_municipios_unidades, multi=True, placeholder="Todos"),
                        ],
                        style={"minWidth": "260px", "flex": "1"},
                    ),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-unidades-saude", style=CARD_CONTAINER),
            html.Div(
                [
                    html.Div(dcc.Graph(id="mapa-unidades-saude"), style={"flex": "2", "minWidth": "460px"}),
                    html.Div(
                        [
                            html.H3("Unidade selecionada", style={"marginTop": "0"}),
                            html.Div(id="detalhe-unidade-saude"),
                        ],
                        style={**PANEL, "flex": "1", "minWidth": "320px"},
                    ),
                ],
                style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(dcc.Graph(id="grafico-unidades-categoria"), style={**PANEL, "padding": "8px", "marginBottom": "14px"}),
            html.Div([html.H3("Microdados das unidades", style={"marginTop": "0"}), tabela("tabela-unidades-saude", page_size=15)], style=PANEL),
        ]
    )


app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("MVP - Mapa de Inventario Hospitalar", style={"margin": "0 0 4px 0", "fontSize": "30px"}),
                html.Div(
                    "Triagem territorial de hospitais municipais e estaduais para apoiar reaproveitamento, recondicionamento e redistribuicao de equipamentos.",
                    style={"color": "#475569", "fontSize": "15px"},
                ),
            ],
            style={"marginBottom": "18px"},
        ),
        dcc.Tabs(
            value="tab-visao-geral",
            children=[
                dcc.Tab(label="Visao geral", value="tab-visao-geral", children=[layout_visao_geral()]),
                dcc.Tab(label="Hospitais", value="tab-hospitais", children=[layout_hospitais()]),
                dcc.Tab(label="Unidades de saude", value="tab-unidades-saude", children=[layout_unidades_saude()]),
            ],
        ),
    ],
    style={"backgroundColor": "#f8fafc", "minHeight": "100vh", "padding": "18px", "fontFamily": "Arial, sans-serif", "color": "#111827"},
)


def aplicar_filtros(df, municipios, esferas, potenciais):
    dff = df.copy()
    if municipios:
        dff = dff[dff["MUNICIPIO"].isin(municipios)]
    if esferas:
        dff = dff[dff["ESFERA"].isin(esferas)]
    if potenciais:
        dff = dff[dff["POTENCIAL_REAPROVEITAMENTO"].isin(potenciais)]
    return dff


@app.callback(
    Output("cards-kpi", "children"),
    Output("mapa-hospitais", "figure"),
    Output("grafico-esfera", "figure"),
    Output("grafico-potencial", "figure"),
    Output("tabela-hospitais", "columns"),
    Output("tabela-hospitais", "data"),
    Input("filtro-municipio", "value"),
    Input("filtro-esfera", "value"),
    Input("filtro-potencial", "value"),
)
def atualizar(municipios, esferas, potenciais):
    dff = aplicar_filtros(hospitais_df, municipios, esferas, potenciais)
    total = len(dff)
    equipamentos = int(dff["EQUIPAMENTOS_TOTAL"].sum())
    ociosos = int(dff["OCIOSOS"].sum())
    manutencao = int(dff["MANUTENCAO"].sum())
    pendentes = int((dff["POTENCIAL_REAPROVEITAMENTO"] == "Inventario pendente").sum())
    taxa_reuso = 0 if equipamentos == 0 else round(((ociosos + manutencao) / equipamentos) * 100, 1)

    cards = [
        card("Hospitais mapeados", f"{total}", "unidades com coordenadas validas", "#2563eb"),
        card("Equipamentos cadastrados", f"{equipamentos}", "inventario total informado", "#0f766e"),
        card("Potencial de reuso", f"{taxa_reuso}%", "ociosos + manutencao sobre total", "#f59e0b"),
        card("Inventario pendente", f"{pendentes}", "unidades a qualificar no piloto", "#7c3aed"),
    ]

    fig_mapa = montar_mapa(dff, municipios_gdf)
    esfera = dff.groupby("ESFERA", as_index=False).agg(HOSPITAIS=("ID_HOSPITAL", "count"), EQUIPAMENTOS=("EQUIPAMENTOS_TOTAL", "sum"))
    potencial = dff.groupby("POTENCIAL_REAPROVEITAMENTO", as_index=False).agg(HOSPITAIS=("ID_HOSPITAL", "count"))

    fig_esfera = px.bar(esfera, x="ESFERA", y="HOSPITAIS", text="HOSPITAIS", color="ESFERA", title="Hospitais por esfera") if not esfera.empty else fig_vazia("Sem dados")
    fig_potencial = px.bar(potencial, x="POTENCIAL_REAPROVEITAMENTO", y="HOSPITAIS", text="HOSPITAIS", color="POTENCIAL_REAPROVEITAMENTO", title="Hospitais por potencial") if not potencial.empty else fig_vazia("Sem dados")
    for fig in [fig_esfera, fig_potencial]:
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

    tabela_df = dff[
        [
            "NOME_HOSPITAL",
            "ESFERA",
            "PORTE",
            "ENDERECO",
            "MUNICIPIO",
            "REGIAO",
            "LEITOS",
            "LEITOS_REFERENCIA",
            "TELEFONE_REFERENCIA",
            "EQUIPAMENTOS_TOTAL",
            "OCIOSOS",
            "MANUTENCAO",
            "DESCARTE",
            "POTENCIAL_REAPROVEITAMENTO",
            "SCORE_REAPROVEITAMENTO",
        ]
    ].sort_values(["MUNICIPIO", "NOME_HOSPITAL"])
    return cards, fig_mapa, fig_esfera, fig_potencial, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")


@app.callback(
    Output("filtro-hospital-detalhe", "options"),
    Output("filtro-hospital-detalhe", "value"),
    Input("filtro-regiao-hospital", "value"),
    Input("hospital-clicado-mapa", "data"),
)
def atualizar_opcoes_hospitais(regiao, hospital_clicado):
    dff = hospitais_df.copy()
    if regiao:
        dff = dff[dff["REGIAO"] == regiao]
    dff = dff.sort_values(["MUNICIPIO", "NOME_HOSPITAL"])
    opcoes = [
        {"label": f"{row.NOME_HOSPITAL} - {row.MUNICIPIO}", "value": row.ID_HOSPITAL}
        for row in dff.itertuples()
    ]
    valores_validos = {op["value"] for op in opcoes}
    if hospital_clicado and hospital_clicado in valores_validos:
        valor = hospital_clicado
    else:
        valor = opcoes[0]["value"] if opcoes else None
    return opcoes, valor


@app.callback(
    Output("hospital-clicado-mapa", "data"),
    Input("mapa-hospital-detalhe", "clickData"),
)
def selecionar_hospital_pelo_mapa(click_data):
    if not click_data or not click_data.get("points"):
        return None
    ponto = click_data["points"][0]
    custom = ponto.get("customdata") or []
    if custom:
        return chave_cnes(custom[0])
    return None


@app.callback(
    Output("cards-hospital", "children"),
    Output("mapa-hospital-detalhe", "figure"),
    Output("grafico-status-hospital", "figure"),
    Output("grafico-tipo-equipamento-hospital", "figure"),
    Output("tabela-equipamentos-hospital", "columns"),
    Output("tabela-equipamentos-hospital", "data"),
    Input("filtro-hospital-detalhe", "value"),
    Input("filtro-regiao-hospital", "value"),
)
def atualizar_hospital(cnes, regiao):
    if not cnes:
        vazio = fig_vazia("Selecione um hospital")
        return [], vazio, vazio, vazio, [], []

    cnes = chave_cnes(cnes)
    registro = hospitais_df[hospitais_df["ID_HOSPITAL"] == cnes]
    if registro.empty:
        vazio = fig_vazia("Hospital nao encontrado")
        return [], vazio, vazio, vazio, [], []

    row = registro.iloc[0].to_dict()
    inv = inventario_df[inventario_df["CO_CNES"] == cnes].copy()
    equipamentos = int(row.get("EQUIPAMENTOS_TOTAL", 0) or 0)
    em_uso = int(row.get("OPERACIONAIS", 0) or 0)
    ociosos = int(row.get("OCIOSOS", 0) or 0)

    leitos_ref = 0 if pd.isna(row.get("LEITOS_REFERENCIA")) else int(row.get("LEITOS_REFERENCIA") or 0)
    telefone_ref = texto_ou_nao_informado(row.get("TELEFONE_REFERENCIA"))
    cards = [
        card("CNES", cnes, row["NOME_HOSPITAL"], "#2563eb"),
        card("Porte", row["PORTE"], f"{int(row.get('LEITOS', 0))} leitos CNES; {row['CRITERIO_PORTE']}", "#64748b"),
        card("Media de acessos", "Nao documentada", "preencher somente com fonte de producao/atendimento", "#475569"),
        card("Equipamentos", f"{equipamentos}", f"{em_uso} em uso; {ociosos} ociosos estimados", "#0f766e"),
        card("Referencia local", f"{leitos_ref} leitos", telefone_ref, "#7c3aed"),
    ]

    hospitais_mapa = hospitais_df.copy()
    if regiao:
        hospitais_mapa = hospitais_mapa[hospitais_mapa["REGIAO"] == regiao]
    if hospitais_mapa.empty:
        hospitais_mapa = registro.copy()
    fig_mapa = montar_mapa_hospital(hospitais_mapa, cnes)

    status = pd.DataFrame(
        [
            {"STATUS": "Em uso", "QUANTIDADE": em_uso},
            {"STATUS": "Ocioso estimado", "QUANTIDADE": ociosos},
            {"STATUS": "Manutencao", "QUANTIDADE": int(row.get("MANUTENCAO", 0) or 0)},
            {"STATUS": "Descarte", "QUANTIDADE": int(row.get("DESCARTE", 0) or 0)},
            {"STATUS": "Para instalacao", "QUANTIDADE": 0},
        ]
    )
    fig_status = px.bar(status, x="STATUS", y="QUANTIDADE", text="QUANTIDADE", color="STATUS", title="Equipamentos por status") if not status.empty else fig_vazia("Sem status")
    fig_status.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

    if inv.empty:
        fig_tipo = fig_vazia("Sem inventario detalhado")
        tabela_df = pd.DataFrame(columns=["Tipo", "Equipamento", "Existente", "Em uso", "Ocioso", "Manutencao", "Descarte", "Para instalacao", "SUS"])
    else:
        tipo = inv.groupby("DS_TIPO_EQUIPAMENTO", as_index=False).agg(QUANTIDADE=("QT_EXISTENTE", "sum")).sort_values("QUANTIDADE", ascending=False)
        fig_tipo = px.bar(tipo, x="QUANTIDADE", y="DS_TIPO_EQUIPAMENTO", orientation="h", text="QUANTIDADE", title="Equipamentos por tipo")
        fig_tipo.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10), yaxis_title="", xaxis_title="Quantidade")

        tabela_df = inv.rename(
            columns={
                "DS_TIPO_EQUIPAMENTO": "Tipo",
                "DS_EQUIPAMENTO": "Equipamento",
                "QT_EXISTENTE": "Existente",
                "QT_USO": "Em uso",
                "QT_OCIOSO_ESTIMADO": "Ocioso",
                "QT_SUS": "SUS",
                "MANUTENCAO": "Manutencao",
                "DESCARTE": "Descarte",
                "PARA_INSTALACAO": "Para instalacao",
            }
        )[
            ["Tipo", "Equipamento", "Existente", "Em uso", "Ocioso", "Manutencao", "Descarte", "Para instalacao", "SUS"]
        ].sort_values(["Tipo", "Equipamento"])

    return cards, fig_mapa, fig_status, fig_tipo, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")


def filtrar_unidades_saude(tipos, municipios):
    dff = unidades_saude_df.copy()
    if tipos:
        dff = dff[dff["CATEGORIA_UNIDADE"].isin(tipos)]
    if municipios:
        dff = dff[dff["NO_MUNICIPIO"].isin(municipios)]
    return dff


def montar_mapa_unidades_saude(df):
    if df.empty:
        return fig_vazia("Sem unidades com coordenadas", altura=620)
    centro = {"lat": float(df["LAT"].mean()), "lon": float(df["LON"].mean())}
    zoom = 7 if df["NO_MUNICIPIO"].nunique() > 1 else 11
    fig = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="CATEGORIA_UNIDADE",
        custom_data=["CO_CNES"],
        hover_name="NO_FANTASIA",
        hover_data={
            "CO_CNES": True,
            "NO_MUNICIPIO": True,
            "ENDERECO": True,
            "NU_TELEFONE": True,
            "NO_EMAIL": True,
            "LAT": False,
            "LON": False,
        },
        height=620,
        center=centro,
        zoom=zoom,
        color_discrete_map={
            "UBS / Atencao basica": "#16a34a",
            "Clinica da familia": "#0891b2",
            "Posto de saude": "#f59e0b",
            "UPA / Pronto atendimento": "#dc2626",
        },
    )
    fig.update_traces(marker={"size": 9})
    fig.update_layout(
        title="UBS, postos de saude e UPAs municipais",
        map={"style": "carto-positron", "center": centro, "zoom": zoom},
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text="Tipo",
    )
    return fig


def detalhe_unidade(cnes, df):
    if not cnes or df.empty:
        return html.Div("Clique em uma unidade no mapa para ver os detalhes.", style={"color": "#64748b"})
    row = df[df["CO_CNES"] == chave_cnes(cnes)]
    if row.empty:
        return html.Div("Unidade nao encontrada no filtro atual.", style={"color": "#64748b"})
    r = row.iloc[0]
    itens = [
        ("CNES", r.get("CO_CNES")),
        ("Nome", r.get("NO_FANTASIA")),
        ("Tipo", r.get("CATEGORIA_UNIDADE")),
        ("Municipio", r.get("NO_MUNICIPIO")),
        ("Endereco", r.get("ENDERECO")),
        ("Telefone", r.get("NU_TELEFONE")),
        ("E-mail", r.get("NO_EMAIL")),
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.Div(label, style={"fontSize": "12px", "color": "#64748b", "fontWeight": "700"}),
                    html.Div(texto_ou_nao_informado(valor), style={"fontSize": "14px", "marginBottom": "10px"}),
                ]
            )
            for label, valor in itens
        ]
    )


@app.callback(
    Output("unidade-clicada-mapa", "data"),
    Input("mapa-unidades-saude", "clickData"),
)
def selecionar_unidade_pelo_mapa(click_data):
    if not click_data or not click_data.get("points"):
        return None
    custom = click_data["points"][0].get("customdata") or []
    return chave_cnes(custom[0]) if custom else None


@app.callback(
    Output("cards-unidades-saude", "children"),
    Output("mapa-unidades-saude", "figure"),
    Output("detalhe-unidade-saude", "children"),
    Output("grafico-unidades-categoria", "figure"),
    Output("tabela-unidades-saude", "columns"),
    Output("tabela-unidades-saude", "data"),
    Input("filtro-tipo-unidade", "value"),
    Input("filtro-municipio-unidade", "value"),
    Input("unidade-clicada-mapa", "data"),
)
def atualizar_unidades_saude(tipos, municipios, cnes_clicado):
    dff = filtrar_unidades_saude(tipos, municipios)
    total = len(dff)
    municipios_total = dff["NO_MUNICIPIO"].nunique() if not dff.empty else 0
    por_tipo = dff["CATEGORIA_UNIDADE"].value_counts()

    cards = [
        card("Unidades mapeadas", f"{total}", "UBS, postos e UPAs com coordenadas", "#2563eb"),
        card("Municipios", f"{municipios_total}", "municipios no filtro atual", "#0f766e"),
        card("Atencao basica", f"{int(por_tipo.get('UBS / Atencao basica', 0))}", "UBS, USF e unidades basicas", "#16a34a"),
        card("Clinicas da familia", f"{int(por_tipo.get('Clinica da familia', 0))}", "categoria destacada no CNES/nome", "#0891b2"),
        card("UPA / PA", f"{int(por_tipo.get('UPA / Pronto atendimento', 0))}", "pronto atendimento e UPAs", "#dc2626"),
        card("Postos", f"{int(por_tipo.get('Posto de saude', 0))}", "postos de saude identificados", "#f59e0b"),
    ]

    fig_mapa = montar_mapa_unidades_saude(dff)
    detalhe = detalhe_unidade(cnes_clicado, dff)

    resumo = dff.groupby("CATEGORIA_UNIDADE", as_index=False).agg(UNIDADES=("CO_CNES", "count")).sort_values("UNIDADES", ascending=False)
    fig_categoria = px.bar(resumo, x="CATEGORIA_UNIDADE", y="UNIDADES", color="CATEGORIA_UNIDADE", text="UNIDADES", title="Unidades por tipo") if not resumo.empty else fig_vazia("Sem dados")
    fig_categoria.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

    tabela_df = dff[
        [
            "CO_CNES",
            "NO_FANTASIA",
            "CATEGORIA_UNIDADE",
            "DS_TIPO_ESTABELECIMENTO",
            "NO_MUNICIPIO",
            "ENDERECO",
            "NU_TELEFONE",
            "NO_EMAIL",
        ]
    ].rename(
        columns={
            "CO_CNES": "CNES",
            "NO_FANTASIA": "Unidade",
            "CATEGORIA_UNIDADE": "Categoria",
            "DS_TIPO_ESTABELECIMENTO": "Tipo CNES",
            "NO_MUNICIPIO": "Municipio",
            "ENDERECO": "Endereco",
            "NU_TELEFONE": "Telefone",
            "NO_EMAIL": "E-mail",
        }
    ).sort_values(["Categoria", "Municipio", "Unidade"])

    return cards, fig_mapa, detalhe, fig_categoria, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")


if __name__ == "__main__":
    app.run(debug=True, port=8053)
