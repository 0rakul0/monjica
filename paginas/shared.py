from pathlib import Path
import sqlite3
import unicodedata

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, html

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

    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])

    return texto

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
                if coluna in {
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
            pd.to_numeric(df["LEITOS_REFERENCIA"], errors="coerce")
            .fillna(0)
            .astype(int)
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
    df["CATEGORIA_UNIDADE"] = df["CATEGORIA_UNIDADE"].fillna("Não classificada")

    return df.dropna(subset=["LAT", "LON"]).copy()


def carregar_municipios():
    if not MUNICIPIOS_SHP.exists():
        return None

    gdf = gpd.read_file(MUNICIPIOS_SHP)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")

    return gdf.to_crs("EPSG:4326")


def carregar_coordenadas_municipios():
    if not COORD_HOSPITAIS_PATH.exists():
        return pd.DataFrame(columns=["destino_norm", "lat_destino", "lon_destino"])

    df = pd.read_csv(COORD_HOSPITAIS_PATH)

    print("Colunas do CSV:", df.columns.tolist())

    # =========================
    # ESCOLHA CORRETA DAS COLUNAS
    # =========================

    # 🔥 força nome correto
    if "NO_MUNICIPIO" in df.columns:
        col_municipio = "NO_MUNICIPIO"
    else:
        col_municipio = None
        for col in df.columns:
            if "MUNIC" in col.upper():
                col_municipio = col

    # lat/lon continuam automáticos
    col_lat = None
    col_lon = None

    for col in df.columns:
        c = col.upper()

        if "LAT" in c:
            col_lat = col

        if "LON" in c or "LOG" in c:
            col_lon = col

    print("Detectado:", col_municipio, col_lat, col_lon)

    if not col_municipio or not col_lat or not col_lon:
        print("❌ Não encontrou colunas necessárias")
        return pd.DataFrame(columns=["destino_norm", "lat_destino", "lon_destino"])

    # =========================
    # NORMALIZAÇÃO
    # =========================

    df["LAT"] = df[col_lat].apply(normalizar_coord)
    df["LON"] = df[col_lon].apply(normalizar_coord)

    # 🔥 agora correto
    df["destino_norm"] = df[col_municipio].apply(normalizar_texto)

    df = df.dropna(subset=["LAT", "LON"])

    df_mun = (
        df.groupby("destino_norm", as_index=False)
        .agg(
            lat_destino=("LAT", "mean"),
            lon_destino=("LON", "mean")
        )
    )

    print("✅ Municípios com coordenadas:", len(df_mun))

    return df_mun


def carregar_monjica():
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        e.id,
        e.tipo_equipamento,
        e.estado_atual,
        l.municipio AS origem,
        l.lat AS lat_origem,
        l.lon AS lon_origem,
        s.score_reuso,
        s.score_criticidade,
        s.score_prioridade,
        s.recomendacao,
        s.explicacao_modelo
    FROM score_decisao s
    JOIN equipamentos e ON e.id = s.id_equipamento
    LEFT JOIN localizacao l ON e.id = l.id_equipamento
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
        l.municipio AS origem,
        l.lat AS lat_origem,
        l.lon AS lon_origem,
        s.score_prioridade,
        s.recomendacao,
        d.municipio AS destino,
        d.nivel_vulnerabilidade,
        d.quantidade_necessaria
    FROM score_decisao s
    JOIN equipamentos e ON e.id = s.id_equipamento
    LEFT JOIN localizacao l ON e.id = l.id_equipamento
    LEFT JOIN demanda_regional d
        ON e.tipo_equipamento = d.tipo_equipamento
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df["destino_norm"] = df["destino"].apply(normalizar_texto)

    df = df.sort_values(
        ["id", "nivel_vulnerabilidade", "quantidade_necessaria", "score_prioridade"],
        ascending=[True, False, False, False],
    ).drop_duplicates("id")

    coords = carregar_coordenadas_municipios()

    print(df["destino"].unique()[:10])
    print(coords["destino_norm"].unique()[:10])

    df = df.merge(
        coords[["destino_norm", "lat_destino", "lon_destino"]],
        on="destino_norm",
        how="left"
    )

    df["lat_origem"] = pd.to_numeric(df["lat_origem"], errors="coerce")
    df["lon_origem"] = pd.to_numeric(df["lon_origem"], errors="coerce")
    df["lat_destino"] = pd.to_numeric(df["lat_destino"], errors="coerce")
    df["lon_destino"] = pd.to_numeric(df["lon_destino"], errors="coerce")

    return df


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


# Dados compartilhados carregados uma vez
hospitais_df = carregar_hospitais()
inventario_df = carregar_inventario_equipamentos()
referencia_local_df = carregar_referencia_local()

if not referencia_local_df.empty:
    hospitais_df = hospitais_df.merge(referencia_local_df, on="ID_HOSPITAL", how="left")
    hospitais_df["REGIAO"] = hospitais_df.get("REGIAO_REFERENCIA", hospitais_df["REGIAO"]).fillna(hospitais_df["REGIAO"])
else:
    hospitais_df["LEITOS_REFERENCIA"] = 0
    hospitais_df["TELEFONE_REFERENCIA"] = "Não informado"
    hospitais_df["REGIAO_REFERENCIA"] = "Não informada"

municipios_gdf = carregar_municipios()
unidades_saude_df = carregar_unidades_saude()
