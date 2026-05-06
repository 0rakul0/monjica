import plotly.express as px
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, chave_cnes, fig_vazia, secao_intro, tabela, texto_ou_nao_informado, unidades_saude_df

opcoes_tipos_unidades = [{"label": t, "value": t} for t in sorted(unidades_saude_df["CATEGORIA_UNIDADE"].dropna().unique())]
opcoes_municipios_unidades = [{"label": m, "value": m} for m in sorted(unidades_saude_df["NO_MUNICIPIO"].dropna().unique())]
opcoes_regioes_unidades = [{"label": r, "value": r} for r in sorted(unidades_saude_df["REGIAO"].dropna().unique())]


def filtrar_unidades_saude(regioes, tipos, municipios):
    dff = unidades_saude_df.copy()
    if regioes:
        dff = dff[dff["REGIAO"].isin(regioes)]
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
        hover_data={"REGIAO": True, "CO_CNES": True, "NO_MUNICIPIO": True, "ENDERECO": True, "NU_TELEFONE": True, "NO_EMAIL": True, "LAT": False, "LON": False},
        height=620,
        center=centro,
        zoom=zoom,
        color_discrete_map={"UBS / Atencao basica": "#16a34a", "Clinica da familia": "#0891b2", "Posto de saude": "#f59e0b", "UPA / Pronto atendimento": "#dc2626"},
    )
    fig.update_traces(marker={"size": 8})
    fig.update_layout(title="UBS, Clínicas da Família, postos de saúde e UPAs municipais", map={"style": "carto-positron", "center": centro, "zoom": zoom}, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="Tipo")
    return fig


def detalhe_unidade(cnes, df):
    if not cnes or df.empty:
        return html.Div("Clique em uma unidade no mapa para ver os detalhes.", style={"color": "#64748b"})
    row = df[df["CO_CNES"] == chave_cnes(cnes)]
    if row.empty:
        return html.Div("Unidade não encontrada no filtro atual.", style={"color": "#64748b"})
    r = row.iloc[0]
    itens = [("CNES", r.get("CO_CNES")), ("Nome", r.get("NO_FANTASIA")), ("Tipo", r.get("CATEGORIA_UNIDADE")), ("Região", r.get("REGIAO")), ("Município", r.get("NO_MUNICIPIO")), ("Endereço", r.get("ENDERECO")), ("Telefone", r.get("NU_TELEFONE")), ("E-mail", r.get("NO_EMAIL"))]
    return html.Div([html.Div([html.Div(label, style={"fontSize": "12px", "color": "#64748b", "fontWeight": "700"}), html.Div(texto_ou_nao_informado(valor), style={"fontSize": "14px", "marginBottom": "10px"})]) for label, valor in itens])


def layout():
    return html.Div(
        [
            secao_intro(
                "Unidades de Saúde",
                "Esta etapa amplia a leitura territorial além dos hospitais. Aqui você encontra UBS, Clínicas da Família, postos de saúde e UPAs para entender presença territorial, cadastro das unidades e cobertura básica do ecossistema de saúde municipal no estado.",
                objetivo="apresentar a infraestrutura territorial ampliada do piloto, mostrando a rede pública que compõe o contexto de origem e destino das estratégias de redistribuição.",
                encontra="filtros por região, tipo e município, mapa clicável, detalhamento cadastral e microdados exportáveis das unidades.",
            ),
            dcc.Store(id="unidade-clicada-mapa"),
            html.Div(
                [
                    html.Div([html.Label("Região", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-regiao-unidade", options=opcoes_regioes_unidades, multi=True, placeholder="Todas")], style={"minWidth": "260px", "flex": "1"}),
                    html.Div([html.Label("Tipo de unidade", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-tipo-unidade", options=opcoes_tipos_unidades, multi=True, placeholder="Todos")], style={"minWidth": "260px", "flex": "1"}),
                    html.Div([html.Label("Município", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-municipio-unidade", options=opcoes_municipios_unidades, multi=True, placeholder="Todos")], style={"minWidth": "260px", "flex": "1"}),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-unidades-saude", style=CARD_CONTAINER),
            html.Div([html.Div(dcc.Graph(id="mapa-unidades-saude"), style={"flex": "2", "minWidth": "460px"}), html.Div([html.H3("Unidade selecionada", style={"marginTop": "0"}), html.Div(id="detalhe-unidade-saude")], style={**PANEL, "flex": "1", "minWidth": "320px"})], style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"}),
            html.Div(dcc.Graph(id="grafico-unidades-categoria"), style={**PANEL, "padding": "8px", "marginBottom": "14px"}),
            html.Div([html.H3("Microdados das unidades", style={"marginTop": "0"}), html.Div("A tabela abaixo lista os microdados cadastrais das unidades no filtro atual, com CNES, região, categoria, endereço e contatos informados no CNES.", style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"}), tabela("tabela-unidades-saude", page_size=15)], style=PANEL),
        ]
    )


def register_callbacks(app):
    @app.callback(Output("unidade-clicada-mapa", "data"), Input("mapa-unidades-saude", "clickData"))
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
        Input("filtro-regiao-unidade", "value"),
        Input("filtro-tipo-unidade", "value"),
        Input("filtro-municipio-unidade", "value"),
        Input("unidade-clicada-mapa", "data"),
    )
    def atualizar_unidades_saude(regioes, tipos, municipios, cnes_clicado):
        dff = filtrar_unidades_saude(regioes, tipos, municipios)
        total = len(dff)
        municipios_total = dff["NO_MUNICIPIO"].nunique() if not dff.empty else 0
        regioes_total = dff["REGIAO"].nunique() if not dff.empty else 0
        por_tipo = dff["CATEGORIA_UNIDADE"].value_counts()

        cards = [
            card("Unidades mapeadas", f"{total}", "UBS, postos e UPAs com coordenadas", "#2563eb"),
            card("Regiões", f"{regioes_total}", "regiões de saúde no filtro atual", "#7c3aed"),
            card("Municípios", f"{municipios_total}", "municípios no filtro atual", "#0f766e"),
            card("Atenção básica", f"{int(por_tipo.get('UBS / Atencao basica', 0))}", "UBS, USF e unidades básicas", "#16a34a"),
            card("Clínicas da Família", f"{int(por_tipo.get('Clinica da familia', 0))}", "categoria destacada no CNES e no nome", "#0891b2"),
            card("UPA / PA", f"{int(por_tipo.get('UPA / Pronto atendimento', 0))}", "pronto atendimento e UPAs", "#dc2626"),
        ]

        fig_mapa = montar_mapa_unidades_saude(dff)
        detalhe = detalhe_unidade(cnes_clicado, dff)
        resumo = dff.groupby("CATEGORIA_UNIDADE", as_index=False).agg(UNIDADES=("CO_CNES", "count")).sort_values("UNIDADES", ascending=False)
        fig_categoria = px.bar(resumo, x="CATEGORIA_UNIDADE", y="UNIDADES", color="CATEGORIA_UNIDADE", text="UNIDADES", title="Unidades por tipo") if not resumo.empty else fig_vazia("Sem dados")
        fig_categoria.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

        tabela_df = dff[["CO_CNES", "NO_FANTASIA", "REGIAO", "CATEGORIA_UNIDADE", "DS_TIPO_ESTABELECIMENTO", "NO_MUNICIPIO", "ENDERECO", "NU_TELEFONE", "NO_EMAIL"]].rename(columns={"CO_CNES": "CNES", "NO_FANTASIA": "Unidade", "REGIAO": "Região", "CATEGORIA_UNIDADE": "Categoria", "DS_TIPO_ESTABELECIMENTO": "Tipo CNES", "NO_MUNICIPIO": "Município", "ENDERECO": "Endereço", "NU_TELEFONE": "Telefone", "NO_EMAIL": "E-mail"}).sort_values(["Região", "Categoria", "Município", "Unidade"])

        return cards, fig_mapa, detalhe, fig_categoria, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
