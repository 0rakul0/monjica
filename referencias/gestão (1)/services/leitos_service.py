import pandas as pd
import plotly.express as px

from database.consultas import aplicar_filtro_lista
from ui.components import card, fig_vazia
from ui.mapas import montar_mapa_unidades_generico
from ui.styles import AZUL, LARANJA, VERDE


def preparar_saida_leitos(leitos_df, geo_municipios, municipios=None, regioes=None, tipos=None):
    dff = leitos_df.copy()
    dff = aplicar_filtro_lista(dff, "MUNICIPIO_UNIDADE", municipios)
    dff = aplicar_filtro_lista(dff, "REGIAO_UNIDADE", regioes)
    dff = aplicar_filtro_lista(dff, "TIPO_UNIDADE", tipos)
    dff["QTD_LEITOS"] = pd.to_numeric(dff["QTD_LEITOS"], errors="coerce").fillna(0)

    cards = [
        card("Hospitais/unidades", f"{int(dff['id_hospital'].nunique()):,}".replace(",", "."), AZUL),
        card("Municípios com leitos", f"{int(dff['MUNICIPIO_UNIDADE'].nunique()):,}".replace(",", "."), VERDE),
        card("Leitos totais", f"{int(dff['QTD_LEITOS'].sum()):,}".replace(",", "."), LARANJA),
    ]

    fig_mapa = montar_mapa_unidades_generico(dff, geo_municipios, titulo="Rede de leitos do estado", titulo_legenda="Tipo de leito")
    resumo_tipo = dff.groupby("TIPO_UNIDADE", as_index=False).agg(QTD_LEITOS=("QTD_LEITOS", "sum")).sort_values("QTD_LEITOS", ascending=False)
    resumo_regiao = dff.groupby("REGIAO_UNIDADE", as_index=False).agg(QTD_LEITOS=("QTD_LEITOS", "sum")).sort_values("QTD_LEITOS", ascending=False)
    unidades = dff[["NOME_UNIDADE", "TIPO_UNIDADE", "QTD_LEITOS", "MUNICIPIO_UNIDADE", "REGIAO_UNIDADE", "END_UNIDADE"]].sort_values(["REGIAO_UNIDADE", "MUNICIPIO_UNIDADE", "NOME_UNIDADE"])

    fig_tipo = px.bar(resumo_tipo, x="TIPO_UNIDADE", y="QTD_LEITOS", text="QTD_LEITOS", title="Leitos por tipo") if not resumo_tipo.empty else fig_vazia()
    fig_regiao = px.bar(resumo_regiao, x="REGIAO_UNIDADE", y="QTD_LEITOS", text="QTD_LEITOS", title="Leitos por região") if not resumo_regiao.empty else fig_vazia()
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
