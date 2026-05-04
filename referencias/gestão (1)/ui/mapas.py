import json

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COR_BASE_MAPA = "#f1f5f9"
COR_RTS = "#93c5fd"
COR_UAI = "#fdba74"
COR_UAA = "#86efac"


def fig_vazia(titulo="Sem dados para exibir", altura=720):
    fig = go.Figure()
    fig.update_layout(
        title=titulo,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": titulo,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16},
            }
        ],
        margin=dict(l=10, r=10, t=50, b=10),
        height=altura,
    )
    return fig


def _choropleth_sem_legenda(gdf, cor, titulo="", altura=520):
    fig = px.choropleth_map(
        gdf,
        geojson=json.loads(gdf.to_json()),
        locations=gdf.index,
        color_discrete_sequence=[cor],
        map_style="light",
        zoom=6.5,
        center={"lat": -22.1, "lon": -42.95},
        opacity=0.50,
        height=altura,
        hover_name="MUNICIPIO_CAPS" if "MUNICIPIO_CAPS" in gdf.columns else None,
        hover_data={"REGIAO_CAPS": "REGIAO_CAPS" in gdf.columns},
    )
    fig.update_traces(
        marker_line_color="#334155",
        marker_line_width=1.2,
        showscale=False,
        showlegend=False,
    )
    fig.update_layout(
        title=titulo,
        margin=dict(l=10, r=10, t=50, b=10),
        height=altura,
        showlegend=False,
    )
    return fig


def montar_mapa_unidades_generico(
    df_base: pd.DataFrame,
    geo_municipios: gpd.GeoDataFrame,
    titulo: str,
    titulo_legenda: str = "Tipo",
    coluna_cor: str = "TIPO_UNIDADE",
    coluna_hover_nome: str = "NOME_UNIDADE",
):
    if geo_municipios is None or geo_municipios.empty:
        return fig_vazia(f"{titulo} - sem base territorial")

    pts = df_base.copy()
    if "LAT" not in pts.columns or "LON" not in pts.columns:
        return fig_vazia(f"{titulo} - sem colunas LAT/LON")

    pts = pts.dropna(subset=["LAT", "LON"]).copy()
    gdf = geo_municipios.copy()

    fig = _choropleth_sem_legenda(gdf, COR_BASE_MAPA, titulo=titulo, altura=820)

    if pts.empty:
        return fig

    hover_data = {
        "MUNICIPIO_UNIDADE": "MUNICIPIO_UNIDADE" in pts.columns,
        "REGIAO_UNIDADE": "REGIAO_UNIDADE" in pts.columns,
        "END_UNIDADE": "END_UNIDADE" in pts.columns,
        "LAT": False,
        "LON": False,
    }
    if "QTD_LEITOS" in pts.columns:
        hover_data["QTD_LEITOS"] = True
    if "QTD_REFERENCIAS" in pts.columns:
        hover_data["QTD_REFERENCIAS"] = True
    if "ID_CAPS" in pts.columns:
        hover_data["ID_CAPS"] = True

    fig_pts = px.scatter_map(
        pts,
        lat="LAT",
        lon="LON",
        color=coluna_cor if coluna_cor in pts.columns else None,
        hover_name=coluna_hover_nome if coluna_hover_nome in pts.columns else None,
        hover_data=hover_data,
        text=coluna_cor if coluna_cor in pts.columns else None,
        zoom=7,
    )

    for trace in fig_pts.data:
        fig.add_trace(trace)

    fig.update_layout(legend_title_text=titulo_legenda)
    return fig


def montar_mapa_cobertura(gdf_cobertura: gpd.GeoDataFrame, titulo: str = "Cobertura territorial de CAPS"):
    if gdf_cobertura is None or gdf_cobertura.empty:
        return fig_vazia(titulo)

    fig = px.choropleth_map(
        gdf_cobertura,
        geojson=json.loads(gdf_cobertura.to_json()),
        locations=gdf_cobertura.index,
        color="STATUS_CAPS",
        color_discrete_map={"Com CAPS": "#86efaf", "Sem CAPS": "#fca5a5"},
        map_style="light",
        zoom=7.3,
        center={"lat": -22.1, "lon": -42.95},
        opacity=0.40,
        height=820,
        hover_name="MUNICIPIO_CAPS" if "MUNICIPIO_CAPS" in gdf_cobertura.columns else None,
        hover_data={"REGIAO_CAPS": "REGIAO_CAPS" in gdf_cobertura.columns},
    )
    fig.update_traces(marker_line_color="#334155", marker_line_width=1.2, showscale=False)
    fig.update_layout(title=titulo, margin=dict(l=10, r=10, t=50, b=10), legend_title_text="Cobertura municipal")
    return fig


def montar_mapa_recurso_por_tipo(
    df_base: pd.DataFrame,
    geo_municipios: gpd.GeoDataFrame,
    tipo_recurso: str,
    titulo: str,
    coluna_municipio_df: str = "MUNICIPIO_UNIDADE",
    altura: int = 520,
):
    cores = {
        "RTs": COR_RTS,
        "UAI": COR_UAI,
        "UAA": COR_UAA,
    }

    if geo_municipios is None or geo_municipios.empty:
        return fig_vazia(f"{titulo} - sem base territorial", altura=altura)

    gdf = geo_municipios.copy()
    fig = _choropleth_sem_legenda(gdf, COR_BASE_MAPA, titulo=titulo, altura=altura)

    if (
        df_base is None
        or df_base.empty
        or "TIPO_UNIDADE" not in df_base.columns
        or coluna_municipio_df not in df_base.columns
        or "MUNICIPIO_CAPS" not in gdf.columns
    ):
        return fig

    dff = df_base[df_base["TIPO_UNIDADE"] == tipo_recurso].copy()
    if dff.empty:
        return fig

    municipios_destacados = (
        dff[coluna_municipio_df]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    if not municipios_destacados:
        return fig

    gdf["MUNICIPIO_CAPS"] = gdf["MUNICIPIO_CAPS"].astype(str).str.strip()
    gdf_dest = gdf[gdf["MUNICIPIO_CAPS"].isin(municipios_destacados)].copy()

    if gdf_dest.empty:
        return fig

    camada = px.choropleth_map(
        gdf_dest,
        geojson=json.loads(gdf_dest.to_json()),
        locations=gdf_dest.index,
        color_discrete_sequence=[cores.get(tipo_recurso, COR_RTS)],
        map_style="light",
        zoom=7.3,
        center={"lat": -22.1, "lon": -42.95},
        opacity=0.65,
        height=altura,
        hover_name="MUNICIPIO_CAPS" if "MUNICIPIO_CAPS" in gdf_dest.columns else None,
        hover_data={"REGIAO_CAPS": "REGIAO_CAPS" in gdf_dest.columns},
    )

    for trace in camada.data:
        trace.marker.line.color = "#334155"
        trace.marker.line.width = 1.2
        trace.showscale = False
        trace.showlegend = False
        fig.add_trace(trace)

    return fig