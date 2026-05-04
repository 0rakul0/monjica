import plotly.express as px

from database.consultas import aplicar_filtro_lista
from ui.components import card
from ui.mapas import montar_mapa_cobertura
from ui.styles import AZUL, VERDE, VERMELHO


def montar_base_cobertura(geo_municipios, caps_df):
    gdf = geo_municipios.copy()
    municipios_com_caps = set(
        caps_df["ID_MUNICIPIO"].dropna().astype(int).unique()
    ) if not caps_df.empty and "ID_MUNICIPIO" in caps_df.columns else set()

    gdf["STATUS_CAPS"] = gdf["id_municipio"].apply(
        lambda x: "Com CAPS" if int(x) in municipios_com_caps else "Sem CAPS"
    )
    return gdf


def preparar_saida_cobertura(geo_municipios, caps_df, status_caps=None, municipios_sel=None):
    # Base completa para o mapa: nunca remover municípios daqui
    cobertura_base = montar_base_cobertura(geo_municipios, caps_df)

    # Base filtrada apenas para cards, tabelas e gráfico
    cobertura_filtrada = cobertura_base.copy()
    cobertura_filtrada = aplicar_filtro_lista(cobertura_filtrada, "STATUS_CAPS", status_caps)
    cobertura_filtrada = aplicar_filtro_lista(cobertura_filtrada, "MUNICIPIO_CAPS", municipios_sel)

    # Mapa sempre com a base completa para evitar "buracos"
    fig_mapa = montar_mapa_cobertura(cobertura_base, titulo="Cobertura territorial de CAPS")

    com_caps = (
        cobertura_filtrada[cobertura_filtrada["STATUS_CAPS"] == "Com CAPS"][
            ["MUNICIPIO_CAPS", "REGIAO_CAPS"]
        ]
        .drop_duplicates()
        .sort_values(["REGIAO_CAPS", "MUNICIPIO_CAPS"])
    )

    sem_caps = (
        cobertura_filtrada[cobertura_filtrada["STATUS_CAPS"] == "Sem CAPS"][
            ["MUNICIPIO_CAPS", "REGIAO_CAPS"]
        ]
        .drop_duplicates()
        .sort_values(["REGIAO_CAPS", "MUNICIPIO_CAPS"])
    )

    resumo_regiao = (
        cobertura_filtrada.groupby(["REGIAO_CAPS", "STATUS_CAPS"])
        .size()
        .reset_index(name="QTD")
    )

    fig_regiao = px.bar(
        resumo_regiao,
        x="REGIAO_CAPS",
        y="QTD",
        color="STATUS_CAPS",
        barmode="group",
        text="QTD",
        title="Cobertura por região",
    )
    fig_regiao.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=480)

    # cards está aqui por conta dos dados dos caps
    cards = [
        card("Municípios", str(len(cobertura_filtrada)), AZUL),
        card("Com CAPS", str(len(com_caps)), VERDE),
        card("Sem CAPS", str(len(sem_caps)), VERMELHO),
    ]

    return {
        "cards": cards,
        "fig_mapa": fig_mapa,
        "fig_regiao": fig_regiao,
        "com_caps": com_caps,
        "sem_caps": sem_caps,
    }