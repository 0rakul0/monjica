import plotly.express as px

from database.consultas import aplicar_filtro_lista
from ui.components import card, fig_vazia
from ui.mapas import montar_mapa_unidades_generico
from ui.styles import AZUL, ROXO, VERDE


def preparar_saida_caps(caps_df, geo_municipios, municipios=None, regioes=None, tipos=None):
    dff = caps_df.copy()
    dff = aplicar_filtro_lista(dff, "MUNICIPIO_CAPS", municipios)
    dff = aplicar_filtro_lista(dff, "REGIAO_CAPS", regioes)
    dff = aplicar_filtro_lista(dff, "TIPO_CAPS", tipos)

    cards = [
        card("Total de unidades CAPS", f"{int(dff['NOME_CAPS'].nunique()):,}".replace(",", "."), ROXO),
        card("Municípios com CAPS", f"{int(dff['MUNICIPIO_CAPS'].nunique()):,}".replace(",", "."), VERDE),
        card("Regiões com CAPS", f"{int(dff['REGIAO_CAPS'].nunique()):,}".replace(",", "."), AZUL),
    ]

    dff_mapa = dff.rename(columns={"NOME_CAPS": "NOME_UNIDADE", "END_CAPS": "END_UNIDADE", "MUNICIPIO_CAPS": "MUNICIPIO_UNIDADE", "REGIAO_CAPS": "REGIAO_UNIDADE", "TIPO_CAPS": "TIPO_UNIDADE"})
    fig_mapa = montar_mapa_unidades_generico(dff_mapa, geo_municipios, titulo="Rede CAPS do estado", titulo_legenda="Tipo de CAPS")

    resumo_tipo = dff.groupby("TIPO_CAPS", as_index=False).agg(QTD_CAPS=("id_caps", "nunique")).sort_values("QTD_CAPS", ascending=False)
    resumo_regiao = dff.groupby("REGIAO_CAPS", as_index=False).agg(QTD_CAPS=("id_caps", "nunique")).sort_values("QTD_CAPS", ascending=False)
    unidades = dff[["NOME_CAPS", "TIPO_CAPS", "MUNICIPIO_CAPS", "REGIAO_CAPS", "END_CAPS"]].sort_values(["REGIAO_CAPS", "MUNICIPIO_CAPS", "NOME_CAPS"])

    fig_tipo = px.bar(resumo_tipo, x="TIPO_CAPS", y="QTD_CAPS", text="QTD_CAPS", title="Quantitativo por tipo de CAPS") if not resumo_tipo.empty else fig_vazia()
    fig_regiao = px.bar(resumo_regiao, x="REGIAO_CAPS", y="QTD_CAPS", text="QTD_CAPS", title="CAPS por região") if not resumo_regiao.empty else fig_vazia()
    for fig in [fig_tipo, fig_regiao]:
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=480)

    return {
        "cards": cards,
        "fig_mapa": fig_mapa,
        "fig_tipo": fig_tipo,
        "fig_regiao": fig_regiao,
        "resumo_tipo": resumo_tipo,
        "resumo_regiao": resumo_regiao,
        "unidades": unidades,
    }
