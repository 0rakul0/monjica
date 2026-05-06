import pandas as pd
import plotly.express as px
from dash import Input, Output, dcc, html

from .shared import (
    CARD_CONTAINER,
    PANEL,
    card,
    chave_cnes,
    fig_vazia,
    hospitais_df,
    inventario_df,
    secao_intro,
    tabela,
    texto_ou_nao_informado,
)

opcoes_regioes_hospitais = [
    {"label": r, "value": r}
    for r in sorted(hospitais_df["REGIAO"].dropna().unique())
]

opcoes_hospitais = [
    {"label": f"{row.NOME_HOSPITAL} - {row.MUNICIPIO}", "value": row.ID_HOSPITAL}
    for row in hospitais_df.sort_values(["REGIAO", "MUNICIPIO", "NOME_HOSPITAL"]).itertuples()
]


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
        hover_data={
            "REGIAO": True,
            "ENDERECO": True,
            "MUNICIPIO": True,
            "PORTE": True,
            "EQUIPAMENTOS_TOTAL": True,
            "SELECIONADO": False,
            "LAT": False,
            "LON": False,
        },
        zoom=8 if len(df) > 1 else 13,
        center={"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
        height=420,
    )

    fig.update_traces(marker={"size": 11})
    fig.update_layout(
        title="Hospitais da região selecionada",
        map={
            "style": "carto-positron",
            "center": {"lat": float(centro["LAT"]), "lon": float(centro["LON"])},
            "zoom": 8 if len(df) > 1 else 13,
        },
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
    )
    return fig


def layout():
    valor_padrao = opcoes_hospitais[0]["value"] if opcoes_hospitais else None

    return html.Div(
        [
            secao_intro(
                "Hospitais",
                "Esta etapa detalha cada hospital individualmente. Aqui você pode navegar por região de saúde, "
                "selecionar uma unidade no mapa ou na lista e consultar seus microdados operacionais: porte, "
                "leitos, referência local e inventário por tipo de equipamento para apoiar triagem e validação técnica.",
            ),
            dcc.Store(id="hospital-clicado-mapa"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Região", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-regiao-hospital",
                                options=opcoes_regioes_hospitais,
                                placeholder="Todas as regiões",
                            ),
                        ],
                        style={"minWidth": "260px", "flex": "1"},
                    ),
                    html.Div(
                        [
                            html.Label("Hospital", style={"fontWeight": "600"}),
                            dcc.Dropdown(
                                id="filtro-hospital-detalhe",
                                options=opcoes_hospitais,
                                value=valor_padrao,
                                placeholder="Selecione um hospital",
                            ),
                        ],
                        style={"minWidth": "360px", "flex": "2"},
                    ),
                ],
                style={
                    **PANEL,
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),
            html.Div(id="cards-hospital", style=CARD_CONTAINER),
            html.Div(
                [
                    html.Div(
                        dcc.Graph(id="mapa-hospital-detalhe"),
                        style={"flex": "1", "minWidth": "360px"},
                    ),
                    html.Div(
                        dcc.Graph(id="grafico-status-hospital"),
                        style={"flex": "1", "minWidth": "360px"},
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "14px",
                    "flexWrap": "wrap",
                    "marginBottom": "14px",
                },
            ),
            html.Div(
                dcc.Graph(id="grafico-tipo-equipamento-hospital"),
                style={**PANEL, "padding": "8px", "marginBottom": "14px"},
            ),
            html.Div(
                [
                    html.H3("Quantitativo por equipamento", style={"marginTop": "0"}),
                    html.Div(
                        "Nesta aba você encontra o detalhamento do inventário do hospital selecionado. "
                        "Os campos de manutenção, descarte e para instalação ainda dependem de integração "
                        "com engenharia clínica ou patrimônio e, por isso, permanecem zerados quando a base CNES não os informa.",
                        style={
                            "color": "#64748b",
                            "fontSize": "13px",
                            "marginBottom": "10px",
                        },
                    ),
                    tabela("tabela-equipamentos-hospital", page_size=14),
                ],
                style=PANEL,
            ),
        ]
    )


def register_callbacks(app):
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
        custom = click_data["points"][0].get("customdata") or []
        return chave_cnes(custom[0]) if custom else None

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
            vazio = fig_vazia("Hospital não encontrado")
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
            card("Média de acessos", "Não documentada", "preencher com produção ou atendimento", "#475569"),
            card("Equipamentos", f"{equipamentos}", f"{em_uso} em uso; {ociosos} ociosos estimados", "#0f766e"),
            card("Referência local", f"{leitos_ref} leitos", telefone_ref, "#7c3aed"),
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
                {"STATUS": "Manutenção", "QUANTIDADE": int(row.get("MANUTENCAO", 0) or 0)},
                {"STATUS": "Descarte", "QUANTIDADE": int(row.get("DESCARTE", 0) or 0)},
                {"STATUS": "Para instalação", "QUANTIDADE": 0},
            ]
        )
        fig_status = (
            px.bar(
                status,
                x="STATUS",
                y="QUANTIDADE",
                text="QUANTIDADE",
                color="STATUS",
                title="Equipamentos por status",
            )
            if not status.empty
            else fig_vazia("Sem status")
        )
        fig_status.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)

        if inv.empty:
            fig_tipo = fig_vazia("Sem inventário detalhado")
            tabela_df = pd.DataFrame(
                columns=[
                    "Tipo",
                    "Equipamento",
                    "Existente",
                    "Em uso",
                    "Ocioso",
                    "Manutenção",
                    "Descarte",
                    "Para instalação",
                    "SUS",
                ]
            )
        else:
            tipo = (
                inv.groupby("DS_TIPO_EQUIPAMENTO", as_index=False)
                .agg(QUANTIDADE=("QT_EXISTENTE", "sum"))
                .sort_values("QUANTIDADE", ascending=False)
            )
            fig_tipo = px.bar(
                tipo,
                x="QUANTIDADE",
                y="DS_TIPO_EQUIPAMENTO",
                orientation="h",
                text="QUANTIDADE",
                title="Equipamentos por tipo",
            )
            fig_tipo.update_layout(height=520, margin=dict(l=10, r=10, t=50, b=10), yaxis_title="", xaxis_title="Quantidade")

            tabela_df = inv.rename(
                columns={
                    "DS_TIPO_EQUIPAMENTO": "Tipo",
                    "DS_EQUIPAMENTO": "Equipamento",
                    "QT_EXISTENTE": "Existente",
                    "QT_USO": "Em uso",
                    "QT_OCIOSO_ESTIMADO": "Ocioso",
                    "QT_SUS": "SUS",
                    "MANUTENCAO": "Manutenção",
                    "DESCARTE": "Descarte",
                    "PARA_INSTALACAO": "Para instalação",
                }
            )[
                [
                    "Tipo",
                    "Equipamento",
                    "Existente",
                    "Em uso",
                    "Ocioso",
                    "Manutenção",
                    "Descarte",
                    "Para instalação",
                    "SUS",
                ]
            ].sort_values(["Tipo", "Equipamento"])

        return (
            cards,
            fig_mapa,
            fig_status,
            fig_tipo,
            [{"name": c, "id": c} for c in tabela_df.columns],
            tabela_df.to_dict("records"),
        )
