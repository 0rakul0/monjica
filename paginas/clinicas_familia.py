import pandas as pd
import plotly.express as px
from dash import Input, Output, dcc, html

from .shared import CARD_CONTAINER, PANEL, card, chave_cnes, clinicas_familia_df, fig_vazia, secao_intro, tabela, texto_ou_nao_informado

opcoes_regioes = [{"label": r, "value": r} for r in sorted(clinicas_familia_df["REGIAO"].dropna().unique())]
opcoes_municipios = [{"label": m, "value": m} for m in sorted(clinicas_familia_df["NO_MUNICIPIO"].dropna().unique())]


def montar_mapa(df_clinicas, cnes_selecionado=None):
    if df_clinicas is None or df_clinicas.empty:
        return fig_vazia("Sem Clínicas da Família com coordenadas", altura=420)
    df = df_clinicas.dropna(subset=["LAT", "LON"]).copy()
    if df.empty:
        return fig_vazia("Clínicas sem coordenadas válidas", altura=420)

    df["SELECIONADA"] = df["CO_CNES"].eq(chave_cnes(cnes_selecionado))
    centro = df[df["SELECIONADA"]].iloc[0] if df["SELECIONADA"].any() else df.iloc[0]
    fig = px.scatter_map(
        df,
        lat="LAT",
        lon="LON",
        color="SELECIONADA",
        color_discrete_map={True: "#dc2626", False: "#0891b2"},
        custom_data=["CO_CNES"],
        hover_name="NO_FANTASIA",
        hover_data={"REGIAO": True, "NO_MUNICIPIO": True, "ENDERECO": True, "NU_TELEFONE": True, "NO_EMAIL": True, "SELECIONADA": False, "LAT": False, "LON": False},
        zoom=9 if len(df) > 1 else 13,
        center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
        height=420,
    )
    fig.update_traces(marker={"size": 11})
    fig.update_layout(title="Clínicas da Família da região selecionada", map={"style": "carto-positron", "center": {"lat": float(centro['LAT']), "lon": float(centro['LON'])}, "zoom": 9 if len(df) > 1 else 13}, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    return fig


def inventario_placeholder():
    return pd.DataFrame([{"Tipo": "Inventário clínico", "Equipamento": "Base CNES atual", "Existente": 0, "Em uso": 0, "Ocioso": 0, "Manutenção": 0, "Descarte": 0, "Para instalação": 0, "Observação": "Sem inventário de equipamentos identificado para esta Clínica da Família na extração atual."}])


def layout():
    valor_padrao = clinicas_familia_df.iloc[0]["CO_CNES"] if not clinicas_familia_df.empty else None
    return html.Div(
        [
            secao_intro("Clínicas da Família", "Esta etapa usa a mesma lógica de navegação dos hospitais, mas aplicada à atenção primária. Aqui você identifica a clínica, verifica sua localização e enxerga claramente o que já está documentado no CNES e o que ainda precisa ser integrado para formar um inventário operacional completo."),
            dcc.Store(id="clinica-clicada-mapa"),
            html.Div(
                [
                    html.Div([html.Label("Região", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-regiao-clinica", options=opcoes_regioes, placeholder="Todas as regiões")], style={"minWidth": "260px", "flex": "1"}),
                    html.Div([html.Label("Município", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-municipio-clinica", options=opcoes_municipios, placeholder="Todos os municípios")], style={"minWidth": "260px", "flex": "1"}),
                    html.Div([html.Label("Clínica da Família", style={"fontWeight": "600"}), dcc.Dropdown(id="filtro-clinica-detalhe", options=[], value=valor_padrao, placeholder="Selecione uma clínica")], style={"minWidth": "360px", "flex": "2"}),
                ],
                style={**PANEL, "display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "14px"},
            ),
            html.Div(id="cards-clinica", style=CARD_CONTAINER),
            html.Div([html.Div(dcc.Graph(id="mapa-clinica-detalhe"), style={"flex": "1", "minWidth": "360px"}), html.Div(dcc.Graph(id="grafico-status-clinica"), style={"flex": "1", "minWidth": "360px"})], style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"}),
            html.Div(dcc.Graph(id="grafico-necessidades-clinica"), style={**PANEL, "padding": "8px", "marginBottom": "14px"}),
            html.Div([html.H3("Inventário e necessidades", style={"marginTop": "0"}), html.Div("Nesta aba você encontra os dados cadastrais existentes e uma leitura clara das lacunas. A base CNES usada no projeto não traz inventário de equipamentos para Clínicas da Família, então as necessidades listadas abaixo servem como roteiro para integração futura com patrimônio, engenharia clínica ou visita técnica.", style={"color": "#64748b", "fontSize": "13px", "marginBottom": "10px"}), tabela("tabela-clinica-inventario", page_size=10)], style=PANEL),
        ]
    )


def register_callbacks(app):
    @app.callback(
        Output("filtro-clinica-detalhe", "options"),
        Output("filtro-clinica-detalhe", "value"),
        Input("filtro-regiao-clinica", "value"),
        Input("filtro-municipio-clinica", "value"),
        Input("clinica-clicada-mapa", "data"),
    )
    def atualizar_opcoes(regiao, municipio, clinica_clicada):
        dff = clinicas_familia_df.copy()
        if regiao:
            dff = dff[dff["REGIAO"] == regiao]
        if municipio:
            dff = dff[dff["NO_MUNICIPIO"] == municipio]
        dff = dff.sort_values(["NO_MUNICIPIO", "NO_FANTASIA"])
        opcoes = [{"label": f"{row.NO_FANTASIA} - {row.NO_MUNICIPIO}", "value": row.CO_CNES} for row in dff.itertuples()]
        valores_validos = {op["value"] for op in opcoes}
        valor = clinica_clicada if clinica_clicada in valores_validos else (opcoes[0]["value"] if opcoes else None)
        return opcoes, valor

    @app.callback(Output("clinica-clicada-mapa", "data"), Input("mapa-clinica-detalhe", "clickData"))
    def selecionar_pelo_mapa(click_data):
        if not click_data or not click_data.get("points"):
            return None
        custom = click_data["points"][0].get("customdata") or []
        return chave_cnes(custom[0]) if custom else None

    @app.callback(
        Output("cards-clinica", "children"),
        Output("mapa-clinica-detalhe", "figure"),
        Output("grafico-status-clinica", "figure"),
        Output("grafico-necessidades-clinica", "figure"),
        Output("tabela-clinica-inventario", "columns"),
        Output("tabela-clinica-inventario", "data"),
        Input("filtro-clinica-detalhe", "value"),
        Input("filtro-regiao-clinica", "value"),
        Input("filtro-municipio-clinica", "value"),
    )
    def atualizar_clinica(cnes, regiao, municipio):
        if not cnes:
            vazio = fig_vazia("Selecione uma Clínica da Família")
            return [], vazio, vazio, vazio, [], []
        cnes = chave_cnes(cnes)
        registro = clinicas_familia_df[clinicas_familia_df["CO_CNES"] == cnes]
        if registro.empty:
            vazio = fig_vazia("Clínica não encontrada")
            return [], vazio, vazio, vazio, [], []

        row = registro.iloc[0].to_dict()
        dff_mapa = clinicas_familia_df.copy()
        if regiao:
            dff_mapa = dff_mapa[dff_mapa["REGIAO"] == regiao]
        if municipio:
            dff_mapa = dff_mapa[dff_mapa["NO_MUNICIPIO"] == municipio]
        if dff_mapa.empty:
            dff_mapa = registro.copy()

        tem_telefone = int(bool(str(row.get("NU_TELEFONE") or "").strip()))
        tem_email = int(bool(str(row.get("NO_EMAIL") or "").strip()))
        cards = [
            card("CNES", cnes, row["NO_FANTASIA"], "#0891b2"),
            card("Região", row["REGIAO"], row["NO_MUNICIPIO"], "#2563eb"),
            card("Telefone", texto_ou_nao_informado(row.get("NU_TELEFONE")), "contato cadastrado no CNES", "#0f766e"),
            card("Inventário CNES", "Não identificado", "sem linhas de equipamentos na extração atual", "#64748b"),
            card("Necessidades", "Mapeamento pendente", "vincular patrimônio, manutenção e instalação", "#7c3aed"),
        ]

        fig_mapa = montar_mapa(dff_mapa, cnes)
        status = pd.DataFrame([{"STATUS": "Telefone informado", "QUANTIDADE": tem_telefone}, {"STATUS": "E-mail informado", "QUANTIDADE": tem_email}, {"STATUS": "Inventário disponível", "QUANTIDADE": 0}, {"STATUS": "Inventário pendente", "QUANTIDADE": 1}])
        fig_status = px.bar(status, x="STATUS", y="QUANTIDADE", text="QUANTIDADE", color="STATUS", title="Situação cadastral da clínica")
        fig_status.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

        necessidades = pd.DataFrame([{"ETAPA": "Inventário biomédico", "STATUS": "Pendente", "VALOR": 1}, {"ETAPA": "Status operacional", "STATUS": "Pendente", "VALOR": 1}, {"ETAPA": "Manutenção", "STATUS": "Pendente", "VALOR": 1}, {"ETAPA": "Descarte", "STATUS": "Pendente", "VALOR": 1}, {"ETAPA": "Para instalação", "STATUS": "Pendente", "VALOR": 1}])
        fig_necessidades = px.bar(necessidades, x="VALOR", y="ETAPA", color="STATUS", orientation="h", text="STATUS", title="Necessidades de integração para detalhamento da clínica", color_discrete_map={"Pendente": "#f59e0b"})
        fig_necessidades.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), xaxis_title="", yaxis_title="", showlegend=False)
        fig_necessidades.update_xaxes(visible=False)

        tabela_df = inventario_placeholder()
        return cards, fig_mapa, fig_status, fig_necessidades, [{"name": c, "id": c} for c in tabela_df.columns], tabela_df.to_dict("records")
