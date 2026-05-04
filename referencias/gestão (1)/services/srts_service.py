import plotly.express as px

from database.consultas import aplicar_filtro_lista
from ui.components import card, fig_vazia
from ui.mapas import montar_mapa_recurso_por_tipo
from ui.styles import *


def preparar_saida_srts(srt_df, geo_municipios, municipios=None, regioes=None, tipos=None, tipos_caps=None):
    dff = srt_df.copy()
    dff = aplicar_filtro_lista(dff, "MUNICIPIO_UNIDADE", municipios)
    dff = aplicar_filtro_lista(dff, "REGIAO_UNIDADE", regioes)
    dff = aplicar_filtro_lista(dff, "TIPO_CAPS", tipos_caps)

    # tipos continua valendo para cards/tabelas/gráficos, se o usuário quiser filtrar
    dff_visao = aplicar_filtro_lista(dff, "TIPO_UNIDADE", tipos)

    fig_mapa_rts = montar_mapa_recurso_por_tipo(
        dff,
        geo_municipios,
        tipo_recurso="RTs",
        titulo="RTs",
        coluna_municipio_df="MUNICIPIO_UNIDADE",
        altura=460,
    )
    fig_mapa_uai = montar_mapa_recurso_por_tipo(
        dff,
        geo_municipios,
        tipo_recurso="UAI",
        titulo="UAI",
        coluna_municipio_df="MUNICIPIO_UNIDADE",
        altura=460,
    )
    fig_mapa_uaa = montar_mapa_recurso_por_tipo(
        dff,
        geo_municipios,
        tipo_recurso="UAA",
        titulo="UAA",
        coluna_municipio_df="MUNICIPIO_UNIDADE",
        altura=460,
    )

    resumo_tipo = dff_visao.groupby("TIPO_UNIDADE", as_index=False).agg(
        QTD_REFERENCIAS=("QTD_REFERENCIAS", "sum")
    ).sort_values("QTD_REFERENCIAS", ascending=False) if not dff_visao.empty else dff_visao

    resumo_regiao = dff_visao.groupby("REGIAO_UNIDADE", as_index=False).agg(
        QTD_REFERENCIAS=("QTD_REFERENCIAS", "sum")
    ).sort_values("QTD_REFERENCIAS", ascending=False) if not dff_visao.empty else dff_visao

    unidades = dff_visao[
        [
            "TIPO_CAPS",
            "TIPO_UNIDADE",
            "QTD_REFERENCIAS",
            "NOME_UNIDADE",
            "MUNICIPIO_UNIDADE",
            "REGIAO_UNIDADE",
            "END_UNIDADE",
        ]
    ].sort_values(
        ["REGIAO_UNIDADE", "MUNICIPIO_UNIDADE", "TIPO_CAPS", "TIPO_UNIDADE", "NOME_UNIDADE"]
    ) if not dff_visao.empty else dff_visao

    cards = [
        card("Pontos RT/UAI/UAA", f"{int(dff_visao.shape[0]):,}".replace(",", "."), AZUL),
        card("CAPS vinculados", f"{int(dff_visao['ID_CAPS'].nunique()):,}".replace(",", "."), VERDE),
        card("Referências totais", f"{int(dff_visao['QTD_REFERENCIAS'].fillna(0).sum()):,}".replace(",", "."), ROXO),
    ]

    fig_tipo = px.bar(
        resumo_tipo,
        x="TIPO_UNIDADE",
        y="QTD_REFERENCIAS",
        text="QTD_REFERENCIAS",
        title="RTs / UAI / UAA por tipo"
    ) if not resumo_tipo.empty else fig_vazia()

    fig_regiao = px.bar(
        resumo_regiao,
        x="REGIAO_UNIDADE",
        y="QTD_REFERENCIAS",
        text="QTD_REFERENCIAS",
        title="RTs / UAI / UAA por região"
    ) if not resumo_regiao.empty else fig_vazia()

    for fig in [fig_tipo, fig_regiao]:
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=480)

    return {
        "cards": cards,
        "fig_mapa_rts": fig_mapa_rts,
        "fig_mapa_uai": fig_mapa_uai,
        "fig_mapa_uaa": fig_mapa_uaa,
        "fig_tipo": fig_tipo,
        "fig_regiao": fig_regiao,
        "resumo_tipo": resumo_tipo,
        "unidades": unidades,
    }