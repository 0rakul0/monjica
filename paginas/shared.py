from pathlib import Path
import sqlite3
import unicodedata

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import requests
from dash import dash_table, html

from core import REGIAO_POR_MUNICIPIO, normalizar_municipio, normalizar_regiao_nome
from config import *

DB_PATH = Path("./banco/monjica.db")
COORD_HOSPITAIS_PATH = Path("./data/entrada/hospitais_municipais_rj_cnes_202603.csv")

CARD_CONTAINER = {
    "display": "flex",
    "gap": "12px",
    "flexWrap": "wrap",
    "marginBottom": "14px",
}

PANEL = {
    "backgroundColor": "#ffffff",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "14px",
}

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


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def normalizar_chave_municipio(valor):
    base = normalizar_municipio(valor) or normalizar_texto(valor)
    return (base or "").replace("-", " ")


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


REGIAO_POR_MUNICIPIO = {
    normalizar_chave_municipio(municipio): normalizar_regiao_nome(regiao)
    for municipio, regiao in REGIAO_POR_MUNICIPIO.items()
}


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
        return "Inventário pendente"

    taxa = (ociosos + manutencao) / total

    if descarte / total >= 0.5:
        return "Baixo"
    if taxa >= 0.3:
        return "Alto"
    if taxa >= 0.1:
        return "Médio"
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
            return "Médio porte", "classificado por leitos CNES"
        return "Grande porte", "classificado por leitos CNES"

    if equipamentos <= 50:
        return "Pequeno porte", "estimativa preliminar por inventário"
    if equipamentos <= 200:
        return "Médio porte", "estimativa preliminar por inventário"

    return "Grande porte", "estimativa preliminar por inventário"


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
                "POTENCIAL_REAPROVEITAMENTO": "Inventário pendente",
                "SCORE_REAPROVEITAMENTO": 0,
            }
        )
    else:
        df = pd.DataFrame(columns=COLUNAS_BASE)

    for coluna in COLUNAS_BASE:
        if coluna not in df.columns:
            df[coluna] = (
                0
                if coluna
                in {
                    "LEITOS",
                    "EQUIPAMENTOS_TOTAL",
                    "OPERACIONAIS",
                    "OCIOSOS",
                    "MANUTENCAO",
                    "DESCARTE",
                    "SCORE_REAPROVEITAMENTO",
                }
                else "Não informado"
            )

    df["ID_HOSPITAL"] = df["ID_HOSPITAL"].apply(chave_cnes)
    df["LAT"] = df["LAT"].apply(normalizar_coord)
    df["LON"] = df["LON"].apply(normalizar_coord)

    for coluna in [
        "LEITOS",
        "EQUIPAMENTOS_TOTAL",
        "OPERACIONAIS",
        "OCIOSOS",
        "MANUTENCAO",
        "DESCARTE",
    ]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)

    df["ESFERA"] = df["ESFERA"].fillna("A classificar").replace("", "A classificar")
    df["POTENCIAL_REAPROVEITAMENTO"] = df.apply(inferir_potencial, axis=1)
    df["SCORE_REAPROVEITAMENTO"] = df.apply(calcular_score, axis=1)
    df["MUNICIPIO"] = df["MUNICIPIO"].fillna("Não informado")
    df["REGIAO"] = df["REGIAO"].fillna("Não informada")
    df["ENDERECO"] = df["ENDERECO"].fillna("Não informado")
    df["NOME_HOSPITAL"] = df["NOME_HOSPITAL"].fillna("Não informado")
    df["MUNICIPIO_NORM"] = df["MUNICIPIO"].apply(normalizar_chave_municipio)
    df["REGIAO"] = df["REGIAO"].replace(
        {"A classificar": pd.NA, "Não informada": pd.NA, "": pd.NA}
    )
    df["REGIAO"] = df["REGIAO"].fillna(df["MUNICIPIO_NORM"].map(REGIAO_POR_MUNICIPIO))
    df["REGIAO"] = df["REGIAO"].fillna("A classificar").apply(normalizar_regiao_nome)

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
            df[coluna] = 0 if coluna.startswith("QT_") else "Não informado"

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
        df["LEITOS_REFERENCIA"] = (
            pd.to_numeric(df["LEITOS_REFERENCIA"], errors="coerce").fillna(0).astype(int)
        )

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
            df[coluna] = "Não informado"

    df["CO_CNES"] = df["CO_CNES"].apply(chave_cnes)
    df["LAT"] = df["LAT"].apply(normalizar_coord)
    df["LON"] = df["LON"].apply(normalizar_coord)
    df["NO_MUNICIPIO"] = df["NO_MUNICIPIO"].fillna("Não informado")
    df["MUNICIPIO_NORM"] = df["NO_MUNICIPIO"].apply(normalizar_chave_municipio)
    df["REGIAO"] = df["MUNICIPIO_NORM"].map(REGIAO_POR_MUNICIPIO).fillna("A classificar")
    df["CATEGORIA_UNIDADE"] = df["CATEGORIA_UNIDADE"].fillna("Não classificada")

    return df.dropna(subset=["LAT", "LON"]).copy()


def carregar_municipios():
    if not MUNICIPIOS_SHP.exists():
        return None

    gdf = gpd.read_file(MUNICIPIOS_SHP)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")

    gdf = gdf.to_crs("EPSG:4326")
    gdf["MUNICIPIO_NORM"] = gdf["NM_MUN"].apply(normalizar_chave_municipio)
    gdf["REGIAO_SAUDE"] = (
        gdf["MUNICIPIO_NORM"].map(REGIAO_POR_MUNICIPIO).fillna("A classificar").apply(normalizar_regiao_nome)
    )
    return gdf


_COORD_CACHE = None


def carregar_coordenadas_municipios():
    global _COORD_CACHE

    if _COORD_CACHE is not None:
        return _COORD_CACHE

    if not COORD_HOSPITAIS_PATH.exists():
        return pd.DataFrame(columns=["destino_norm", "lat_destino", "lon_destino"])

    df = pd.read_csv(COORD_HOSPITAIS_PATH)
    df["LAT"] = df["LAT"].apply(normalizar_coord)
    df["LON"] = df["LON"].apply(normalizar_coord)
    df["destino_norm"] = df["NO_MUNICIPIO"].apply(normalizar_texto)
    df = df.dropna(subset=["LAT", "LON"])

    df_mun = (
        df.groupby("destino_norm", as_index=False)
        .agg(lat_destino=("LAT", "mean"), lon_destino=("LON", "mean"))
    )
    _COORD_CACHE = df_mun
    return df_mun


def obter_rota_osrm(lat1, lon1, lat2, lon2):
    url = (
        "http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )

    try:
        resposta = requests.get(url, timeout=5)
        data = resposta.json()
        coords = data["routes"][0]["geometry"]["coordinates"]

        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        distancia_km = data["routes"][0]["distance"] / 1000
        tempo_min = data["routes"][0]["duration"] / 60
        return lats, lons, distancia_km, tempo_min
    except Exception:
        return None, None, None, None


def carregar_monjica():
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT
        e.id,
        e.tipo_equipamento,
        e.estado_atual,
        es.nome_fantasia AS estabelecimento_origem,
        es.municipio AS origem,
        es.latitude AS lat_origem,
        es.longitude AS lon_origem,
        s.score_reuso,
        s.score_criticidade,
        s.score_prioridade,
        s.recomendacao,
        s.explicacao_modelo
    FROM score_decisao s
    JOIN equipamentos e
        ON e.id = s.id_equipamento
    LEFT JOIN estabelecimentos_saude es
        ON e.id_estabelecimento = es.id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def carregar_fluxo_monjica():
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT
        e.id,
        e.tipo_equipamento,
        es.municipio AS origem,
        es.latitude AS lat_origem,
        es.longitude AS lon_origem,
        s.score_prioridade,
        s.recomendacao,
        d.municipio AS destino,
        d.nivel_vulnerabilidade,
        d.quantidade_necessaria
    FROM score_decisao s
    JOIN equipamentos e
        ON e.id = s.id_equipamento
    LEFT JOIN estabelecimentos_saude es
        ON e.id_estabelecimento = es.id
    LEFT JOIN demanda_regional d
        ON e.tipo_equipamento = d.tipo_equipamento
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df["destino_norm"] = df["destino"].apply(normalizar_texto)
    df["origem_norm"] = df["origem"].apply(normalizar_chave_municipio)
    df["destino_norm_mun"] = df["destino"].apply(normalizar_chave_municipio)
    df["REGIAO_ORIGEM"] = df["origem_norm"].map(REGIAO_POR_MUNICIPIO).fillna("A classificar")
    df["REGIAO_DESTINO"] = df["destino_norm_mun"].map(REGIAO_POR_MUNICIPIO).fillna("A classificar")
    coords = carregar_coordenadas_municipios()
    return df.merge(coords, on="destino_norm", how="left")


def fig_vazia(titulo, altura=480):
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
            }
        ],
        height=altura,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def card(titulo, valor, detalhe, cor):
    return html.Div(
        [
            html.Div(
                titulo,
                style={"fontSize": "12px", "color": "#475569", "marginBottom": "6px"},
            ),
            html.Div(
                valor,
                style={"fontSize": "25px", "fontWeight": "700", "color": cor},
            ),
            html.Div(
                detalhe,
                style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"},
            ),
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


def secao_intro(titulo, descricao):
    return html.Div(
        [
            html.H3(titulo, style={"margin": "0 0 6px 0"}),
            html.Div(
                descricao,
                style={"color": "#475569", "fontSize": "14px", "lineHeight": "1.5"},
            ),
        ],
        style={**PANEL, "marginBottom": "14px"},
    )


def tabela(id_tabela, page_size=12):
    return dash_table.DataTable(
        id=id_tabela,
        page_size=page_size,
        sort_action="native",
        filter_action="native",
        export_format="xlsx",
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "8px",
            "fontFamily": "Arial",
            "fontSize": "13px",
            "whiteSpace": "normal",
            "maxWidth": "360px",
        },
        style_header={"fontWeight": "700", "backgroundColor": "#f1f5f9"},
    )


def texto_ou_nao_informado(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return "Não informado"
    return str(valor).strip()


hospitais_df = carregar_hospitais()
inventario_df = carregar_inventario_equipamentos()
referencia_local_df = carregar_referencia_local()

if not referencia_local_df.empty:
    hospitais_df = hospitais_df.merge(referencia_local_df, on="ID_HOSPITAL", how="left")
    hospitais_df["REGIAO"] = hospitais_df.get(
        "REGIAO_REFERENCIA", hospitais_df["REGIAO"]
    ).fillna(hospitais_df["REGIAO"]).apply(normalizar_regiao_nome)
else:
    hospitais_df["LEITOS_REFERENCIA"] = 0
    hospitais_df["TELEFONE_REFERENCIA"] = "Não informado"
    hospitais_df["REGIAO_REFERENCIA"] = "Não informada"

municipios_gdf = carregar_municipios()
unidades_saude_df = carregar_unidades_saude()
clinicas_familia_df = (
    unidades_saude_df[unidades_saude_df["CATEGORIA_UNIDADE"] == "Clinica da familia"]
    .copy()
    .sort_values(["NO_MUNICIPIO", "NO_FANTASIA"])
)
