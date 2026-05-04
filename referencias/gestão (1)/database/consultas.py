import json
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import DB_PATH, PACIENTES_XLSX, MUNICIPIOS_SHP
from core.geo import corrigir_coord
from core.normalizacao import normalizar_txt


def conectar_db():
    return sqlite3.connect(Path(DB_PATH))


def aplicar_filtro_lista(df, coluna, valores):
    if not valores or coluna not in df.columns:
        return df
    return df[df[coluna].isin(valores)].copy()


def carregar_caps_db():
    conn = conectar_db()
    try:
        query = """
        SELECT
            c.id_caps,
            c.nome_caps AS NOME_CAPS,
            c.tipo_caps AS TIPO_CAPS,
            c.end_caps AS END_CAPS,
            c.lat AS LAT,
            c.log AS LON,
            m.id_municipio AS ID_MUNICIPIO,
            m.nome_municipio AS MUNICIPIO_CAPS,
            r.nome_regiao AS REGIAO_CAPS
        FROM caps c
        LEFT JOIN caps_municipio cm ON cm.id_caps = c.id_caps
        LEFT JOIN municipios m ON m.id_municipio = cm.id_municipio
        LEFT JOIN regiao_municipio rm ON rm.id_municipio = m.id_municipio
        LEFT JOIN regioes r ON r.id_regiao = rm.id_regiao
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=["id_caps", "NOME_CAPS", "TIPO_CAPS", "END_CAPS", "LAT", "LON", "ID_MUNICIPIO", "MUNICIPIO_CAPS", "REGIAO_CAPS"])

    df["LAT"] = df["LAT"].apply(corrigir_coord)
    df["LON"] = df["LON"].apply(corrigir_coord)
    df["MUNICIPIO_CAPS"] = df["MUNICIPIO_CAPS"].fillna("Não informado")
    df["REGIAO_CAPS"] = df["REGIAO_CAPS"].fillna("Não informada")
    df["TIPO_CAPS"] = df["TIPO_CAPS"].fillna("OUTRO")
    return df.drop_duplicates(subset=["id_caps"]).copy()


def carregar_leitos_db():
    conn = conectar_db()
    try:
        query = """
        SELECT
            l.id_hospital,
            l.nome_hospital AS NOME_UNIDADE,
            l.end_hosp AS END_UNIDADE,
            l.qte_leitos AS QTD_LEITOS,
            l.lat AS LAT,
            l.log AS LON,
            f.financiamento AS TIPO_UNIDADE,
            m.nome_municipio AS MUNICIPIO_UNIDADE,
            r.nome_regiao AS REGIAO_UNIDADE
        FROM leitos l
        LEFT JOIN municipios m ON m.id_municipio = l.id_municipio
        LEFT JOIN regiao_municipio rm ON rm.id_municipio = l.id_municipio
        LEFT JOIN regioes r ON r.id_regiao = rm.id_regiao
        LEFT JOIN financiamento f ON f.id_financiamento = l.id_financiamento
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=["id_hospital", "NOME_UNIDADE", "END_UNIDADE", "QTD_LEITOS", "LAT", "LON", "TIPO_UNIDADE", "MUNICIPIO_UNIDADE", "REGIAO_UNIDADE"])

    df["LAT"] = df["LAT"].apply(corrigir_coord)
    df["LON"] = df["LON"].apply(corrigir_coord)
    df["QTD_LEITOS"] = pd.to_numeric(df["QTD_LEITOS"], errors="coerce").fillna(0)
    df["TIPO_UNIDADE"] = df["TIPO_UNIDADE"].fillna("LEITO")
    df["MUNICIPIO_UNIDADE"] = df["MUNICIPIO_UNIDADE"].fillna("Não informado")
    df["REGIAO_UNIDADE"] = df["REGIAO_UNIDADE"].fillna("Não informada")
    return df.drop_duplicates(subset=["id_hospital"]).copy()

def carregar_srts_db():
    conn = conectar_db()
    try:
        query = """
        SELECT
            s.id_caps,
            s.rt,
            s.uai,
            s.uaa,
            c.nome_caps AS NOME_UNIDADE,
            c.end_caps AS END_UNIDADE,
            c.tipo_caps AS TIPO_CAPS,
            c.lat AS LAT,
            c.log AS LON,
            m.nome_municipio AS MUNICIPIO_UNIDADE,
            r.nome_regiao AS REGIAO_UNIDADE
        FROM srts s
        LEFT JOIN caps c ON c.id_caps = s.id_caps
        LEFT JOIN caps_municipio cm ON cm.id_caps = s.id_caps
        LEFT JOIN municipios m ON m.id_municipio = cm.id_municipio
        LEFT JOIN regiao_municipio rm ON rm.id_municipio = m.id_municipio
        LEFT JOIN regioes r ON r.id_regiao = rm.id_regiao
        """
        base = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if base.empty:
        return pd.DataFrame(columns=[
            "ID_CAPS", "TIPO_UNIDADE", "QTD_REFERENCIAS", "TIPO_CAPS",
            "NOME_UNIDADE", "END_UNIDADE", "LAT", "LON",
            "MUNICIPIO_UNIDADE", "REGIAO_UNIDADE"
        ])

    base["LAT"] = base["LAT"].apply(corrigir_coord)
    base["LON"] = base["LON"].apply(corrigir_coord)
    base["MUNICIPIO_UNIDADE"] = base["MUNICIPIO_UNIDADE"].fillna("Não informado")
    base["REGIAO_UNIDADE"] = base["REGIAO_UNIDADE"].fillna("Não informada")
    base["TIPO_CAPS"] = base["TIPO_CAPS"].fillna("OUTRO")

    registros = []
    for _, row in base.iterrows():
        for coluna, rotulo in [("rt", "RTs"), ("uai", "UAI"), ("uaa", "UAA")]:
            valor = row.get(coluna)
            try:
                valor_num = int(float(valor)) if pd.notna(valor) else 0
            except Exception:
                valor_num = 0

            if valor_num > 0:
                registros.append({
                    "ID_CAPS": row["id_caps"],
                    "TIPO_UNIDADE": rotulo,
                    "QTD_REFERENCIAS": valor_num,
                    "TIPO_CAPS": row["TIPO_CAPS"],
                    "NOME_UNIDADE": row["NOME_UNIDADE"],
                    "END_UNIDADE": row["END_UNIDADE"],
                    "LAT": row["LAT"],
                    "LON": row["LON"],
                    "MUNICIPIO_UNIDADE": row["MUNICIPIO_UNIDADE"],
                    "REGIAO_UNIDADE": row["REGIAO_UNIDADE"],
                })

    return pd.DataFrame(registros)

def carregar_geo_municipios_db():
    caminho = Path(MUNICIPIOS_SHP)

    if not caminho.exists():
        return gpd.GeoDataFrame(
            columns=["id_municipio", "id_ibge", "MUNICIPIO_CAPS", "REGIAO_CAPS", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = gpd.read_file(caminho)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")

    gdf = gdf.to_crs("EPSG:4326")

    gdf["MUNICIPIO_CAPS"] = gdf["NM_MUN"].apply(normalizar_txt)
    gdf["id_ibge"] = gdf["CD_MUN"].astype(str)

    conn = conectar_db()
    try:
        municipios = pd.read_sql_query(
            """
            SELECT
                m.id_municipio,
                m.nome_municipio,
                r.nome_regiao AS REGIAO_CAPS
            FROM municipios m
            LEFT JOIN regiao_municipio rm
                ON rm.id_municipio = m.id_municipio
            LEFT JOIN regioes r
                ON r.id_regiao = rm.id_regiao
            """,
            conn,
        )
    finally:
        conn.close()

    municipios["nome_municipio"] = municipios["nome_municipio"].apply(normalizar_txt)

    gdf = gdf.merge(
        municipios,
        left_on="MUNICIPIO_CAPS",
        right_on="nome_municipio",
        how="left",
    )

    gdf["REGIAO_CAPS"] = gdf["REGIAO_CAPS"].fillna("Não informada")

    return gpd.GeoDataFrame(
        gdf[["id_municipio", "id_ibge", "MUNICIPIO_CAPS", "REGIAO_CAPS", "geometry"]],
        geometry="geometry",
        crs="EPSG:4326",
    )


def carregar_dados_pacientes():
    caminho = Path(PACIENTES_XLSX)
    if not caminho.exists():
        return pd.DataFrame(columns=["MUNICIPIO_FILTRO", "CAPS_FILTRO", "TIPO_MATCH", "CPF", "RG"])
    try:
        df = pd.read_excel(caminho)
    except Exception:
        return pd.DataFrame(columns=["MUNICIPIO_FILTRO", "CAPS_FILTRO", "TIPO_MATCH", "CPF", "RG"])

    col_caps = next((c for c in df.columns if str(c).upper() in {"CAPS_REF", "CAPS DE REFERÊNCIA", "CAPS DE REFERENCIA", "CAPS_FILTRO"}), None)
    col_municipio = next((c for c in df.columns if str(c).upper() in {"MUNICÍPIO", "MUNICIPIO", "MUNICIPIO_FILTRO"}), None)
    col_tipo_match = next((c for c in df.columns if str(c).upper() == "TIPO_MATCH"), None)
    col_cpf = next((c for c in df.columns if str(c).upper() == "CPF"), None)
    col_rg = next((c for c in df.columns if str(c).upper() == "RG"), None)

    saida = pd.DataFrame()
    saida["CAPS_FILTRO"] = df[col_caps] if col_caps else None
    saida["MUNICIPIO_FILTRO"] = df[col_municipio] if col_municipio else None
    saida["TIPO_MATCH"] = df[col_tipo_match] if col_tipo_match else None
    saida["CPF"] = df[col_cpf] if col_cpf else None
    saida["RG"] = df[col_rg] if col_rg else None
    return saida


