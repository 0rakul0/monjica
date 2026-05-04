#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from core.geo import corrigir_coord
from core.normalizacao import (
    definir_coluna,
    limpar_str,
    limpar_valor,
    normalizar_municipio,
    normalizar_regiao_nome,
    normalizar_texto,
    normalizar_txt,
    para_int,
)
from core.referencias_rj import ID_POR_MUNICIPIO, ID_POR_REGIAO, REGIAO_POR_ID, REGIAO_POR_MUNICIPIO
from database.schema import SCHEMA_SQL


def detectar_coluna_financiamento(df):
    candidatos = [
        "id_financiamento",
        "financiamento",
        "Financiamento",
        "TIPO_FINANCIAMENTO",
        "tipo_financiamento",
    ]
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def extrair_tipo(nome):
    if pd.isna(nome):
        return "OUTRO"
    nome = str(nome).upper()
    padroes = [
        r"CAPS\s?AD\s?III",
        r"CAPS\s?AD\s?II",
        r"CAPS\s?III",
        r"CAPS\s?II",
        r"CAPSI\s?III",
        r"CAPSI",
        r"CAPS\s?I",
        r"CAPS",
    ]
    for padrao in padroes:
        match = re.search(padrao, nome, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(0).upper()).strip()
    return "OUTRO"


def extrair_municipio_de_nome(nome):
    if pd.isna(nome):
        return None
    partes = [p.strip() for p in str(nome).split("-") if p.strip()]
    if not partes:
        return None
    primeira = partes[0]
    if "CAPS" not in primeira.upper():
        return primeira
    ultima = partes[-1]
    if "CAPS" not in ultima.upper():
        return ultima
    return None


def extrair_municipio_caps(nome_caps: str | None, endereco: str | None) -> str:
    if nome_caps and not pd.isna(nome_caps):
        partes = [p.strip() for p in str(nome_caps).split(" - ") if p.strip()]
        if partes:
            return partes[0]
    if endereco and not pd.isna(endereco):
        m = re.search(r"-\s*([^-,]+)\s*-\s*RJ", str(endereco), flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "Não informado"


def padronizar_tipo_caps(txt: str | None) -> str | None:
    if not txt:
        return None
    t = normalizar_txt(txt)
    if not t:
        return None
    substituicoes = {
        "CAPSAD": "CAPS AD",
        "CAPS ADULT": "CAPS AD",
        "CAPS I I I": "CAPS III",
        "CAPS I I": "CAPS II",
        "CAPSIII": "CAPS III",
        "CAPSII": "CAPS II",
        "CAPSI ": "CAPSIJ",
        "CAPSI II ": "CAPSIJ II",
    }
    for a, b in substituicoes.items():
        t = t.replace(a, b)
    t = re.sub(r"CAPSAD", "CAPS AD", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extrair_tipo_caps(txt: str | None) -> str:
    if not txt:
        return "OUTRO"
    t = padronizar_tipo_caps(txt) or ""
    padroes = [
        r"CAPS AD III",
        r"CAPS AD II",
        r"CAPSIJ III",
        r"CAPSIJ II",
        r"CAPSIJ",
        r"CAPS III",
        r"CAPS II",
        r"CAPS I",
        r"CAPS",
    ]
    for padrao in padroes:
        m = re.search(rf"{padrao}", t)
        if m:
            return m.group(0)
    return "OUTRO"


def montar_nome_canonico_unidade(nome_caps: str | None) -> str | None:
    if not nome_caps or pd.isna(nome_caps):
        return None
    bruto = str(nome_caps).strip().replace("–", "-")
    bruto = re.sub(r"\s+", " ", bruto)
    bruto_norm = padronizar_tipo_caps(bruto)
    if not bruto_norm:
        return None
    bruto_norm = re.sub(r"\s*-\s*\d+$", "", bruto_norm).strip()
    partes = [p.strip() for p in bruto_norm.split("-") if p.strip()]
    if not partes:
        return bruto_norm
    if len(partes) == 1:
        return partes[0]
    resto = " - ".join(partes[1:]).strip()
    tipo = extrair_tipo_caps(resto)
    if tipo == "OUTRO":
        tipo = extrair_tipo_caps(bruto_norm)
    if tipo != "OUTRO":
        pos = resto.find(tipo)
        if pos >= 0:
            depois = resto[pos + len(tipo):].strip(" -")
            return f"{tipo} {depois}".strip()
    return resto


class BancoCaps:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def fechar(self):
        self.conn.close()

    def criar_tabelas(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def obter_id_municipio(self, nome_municipio):
        nome_norm = normalizar_municipio(nome_municipio)
        if nome_norm is None:
            return None
        return ID_POR_MUNICIPIO.get(nome_norm)

    def obter_id_financiamento(self, nome_financiamento):
        nome = normalizar_texto(nome_financiamento)
        if nome is None:
            return None
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO financiamento (financiamento) VALUES (?)", (nome,))
        cur.execute("SELECT id_financiamento FROM financiamento WHERE financiamento = ?", (nome,))
        row = cur.fetchone()
        return row[0] if row else None

    def popular_regioes(self):
        for id_regiao, nome_regiao in REGIAO_POR_ID.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO regioes (id_regiao, nome_regiao) VALUES (?, ?)",
                (id_regiao, nome_regiao),
            )
        self.conn.commit()

    def popular_municipios(self):
        for nome_municipio in REGIAO_POR_MUNICIPIO.keys():
            id_municipio = ID_POR_MUNICIPIO[nome_municipio]
            self.conn.execute(
                "INSERT OR IGNORE INTO municipios (id_municipio, nome_municipio) VALUES (?, ?)",
                (id_municipio, nome_municipio),
            )
        self.conn.commit()

    def popular_regiao_municipio(self):
        for nome_municipio, nome_regiao in REGIAO_POR_MUNICIPIO.items():
            id_municipio = ID_POR_MUNICIPIO[nome_municipio]
            id_regiao = ID_POR_REGIAO[nome_regiao]
            self.conn.execute(
                "INSERT INTO regiao_municipio (id_municipio, id_regiao) VALUES (?, ?) ON CONFLICT(id_municipio) DO UPDATE SET id_regiao = excluded.id_regiao",
                (id_municipio, id_regiao),
            )
        self.conn.commit()

    def upsert_caps(self, id_caps, nome_caps, tipo_caps, end_caps, lat, log):
        sql = """
        INSERT INTO caps (id_caps, nome_caps, tipo_caps, end_caps, lat, log)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id_caps) DO UPDATE SET
            nome_caps = COALESCE(caps.nome_caps, excluded.nome_caps),
            tipo_caps = COALESCE(caps.tipo_caps, excluded.tipo_caps),
            end_caps = COALESCE(caps.end_caps, excluded.end_caps),
            lat = COALESCE(caps.lat, excluded.lat),
            log = COALESCE(caps.log, excluded.log)
        """
        self.conn.execute(sql, (id_caps, nome_caps, tipo_caps, end_caps, lat, log))

    def upsert_regiao_municipio(self, id_regiao, id_municipio):
        if id_regiao is None or id_municipio is None:
            return
        self.conn.execute(
            "INSERT INTO regiao_municipio (id_municipio, id_regiao) VALUES (?, ?) ON CONFLICT(id_municipio) DO UPDATE SET id_regiao = excluded.id_regiao",
            (id_municipio, id_regiao),
        )

    def upsert_caps_municipio(self, id_municipio, id_caps):
        if id_municipio is None or id_caps is None:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO caps_municipio (id_municipio, id_caps) VALUES (?, ?)",
            (id_municipio, id_caps),
        )

    def upsert_leito(self, id_municipio, id_hospital, nome_hospital, end_hosp, qte_leitos, lat, log, id_financiamento):
        self.conn.execute(
            """
            INSERT INTO leitos (
                id_municipio, id_hospital, nome_hospital, end_hosp,
                qte_leitos, lat, log, id_financiamento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_hospital) DO UPDATE SET
                id_municipio = COALESCE(leitos.id_municipio, excluded.id_municipio),
                nome_hospital = COALESCE(leitos.nome_hospital, excluded.nome_hospital),
                end_hosp = COALESCE(leitos.end_hosp, excluded.end_hosp),
                qte_leitos = COALESCE(leitos.qte_leitos, excluded.qte_leitos),
                lat = COALESCE(leitos.lat, excluded.lat),
                log = COALESCE(leitos.log, excluded.log),
                id_financiamento = COALESCE(leitos.id_financiamento, excluded.id_financiamento)
            """,
            (id_municipio, id_hospital, nome_hospital, end_hosp, qte_leitos, lat, log, id_financiamento),
        )

    def upsert_srts(self, id_caps, rt, uai, uaa):
        if id_caps is None:
            return
        self.conn.execute(
            """
            INSERT INTO srts (id_caps, rt, uai, uaa)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id_caps) DO UPDATE SET
                rt = COALESCE(srts.rt, excluded.rt),
                uai = COALESCE(srts.uai, excluded.uai),
                uaa = COALESCE(srts.uaa, excluded.uaa)
            """,
            (id_caps, rt, uai, uaa),
        )

    def upsert_municipio_geo(self, id_municipio, id_ibge, nome_municipio, geometry_json):
        if id_municipio is None:
            return
        self.conn.execute(
            """
            INSERT INTO municipios_geo (id_municipio, id_ibge, nome_municipio, geometry_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id_municipio) DO UPDATE SET
                id_ibge = COALESCE(municipios_geo.id_ibge, excluded.id_ibge),
                nome_municipio = COALESCE(municipios_geo.nome_municipio, excluded.nome_municipio),
                geometry_json = COALESCE(municipios_geo.geometry_json, excluded.geometry_json)
            """,
            (id_municipio, id_ibge, nome_municipio, geometry_json),
        )

    def commit(self):
        self.conn.commit()


def importar_caps(banco, xlsx):
    df = pd.read_excel(xlsx, sheet_name="caps")
    df.columns = [str(c).strip() for c in df.columns]
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]

    col_id = definir_coluna(df, ["id_caps", "ID_CAPS"])
    col_id_regiao = definir_coluna(df, ["id_regiao", "ID_REGIAO"])
    col_nome = definir_coluna(df, ["NOME_CAPS", "NOME", "UNIDADE"])
    col_end = definir_coluna(df, ["END_CAPS", "ENDERECO", "ENDEREÇO"])
    col_lat = definir_coluna(df, ["LAT", "LATITUDE"])
    col_lon = definir_coluna(df, ["LOG", "LON", "LONGITUDE", "LNG"])
    col_municipio = definir_coluna(df, ["MUNICIPIO", "MUNICÍPIO"])

    for _, row in df.iterrows():
        id_caps = para_int(row.get(col_id)) if col_id else None
        id_regiao = para_int(row.get(col_id_regiao)) if col_id_regiao else None
        nome_caps = limpar_str(row.get(col_nome), None) if col_nome else None
        end_caps = limpar_str(row.get(col_end), None) if col_end else None
        lat = corrigir_coord(row.get(col_lat)) if col_lat else np.nan
        log = corrigir_coord(row.get(col_lon)) if col_lon else np.nan
        nome_caps_canonico = montar_nome_canonico_unidade(nome_caps) or nome_caps
        tipo_caps = extrair_tipo_caps(nome_caps)
        if tipo_caps == "OUTRO":
            tipo_caps = extrair_tipo(nome_caps)

        municipio = limpar_str(row.get(col_municipio), None) if col_municipio else extrair_municipio_caps(nome_caps, end_caps)
        if municipio in {"Não informado", "", None}:
            municipio = extrair_municipio_de_nome(nome_caps)
        municipio = normalizar_municipio(municipio)
        id_municipio = banco.obter_id_municipio(municipio)

        regiao_nome = REGIAO_POR_MUNICIPIO.get(municipio) if municipio else None
        if regiao_nome is None and id_regiao is not None:
            regiao_nome = REGIAO_POR_ID.get(id_regiao)
        if regiao_nome is not None:
            id_regiao = ID_POR_REGIAO.get(regiao_nome)

        if id_caps is not None:
            banco.upsert_caps(
                id_caps=id_caps,
                nome_caps=nome_caps_canonico,
                tipo_caps=tipo_caps,
                end_caps=end_caps,
                lat=None if pd.isna(lat) else float(lat),
                log=None if pd.isna(log) else float(log),
            )
        banco.upsert_regiao_municipio(id_regiao, id_municipio)
        banco.upsert_caps_municipio(id_municipio, id_caps)

    banco.commit()


def importar_leitos(banco, xlsx):
    df = pd.read_excel(xlsx, sheet_name="leitos")
    df.columns = [str(c).strip() for c in df.columns]
    col_fin = detectar_coluna_financiamento(df)
    col_regiao = definir_coluna(df, ["Região", "REGIAO", "REGIÃO"])
    col_municipio = definir_coluna(df, ["Município", "Municipio", "MUNICÍPIO", "MUNICIPIO"])
    col_id_hospital = definir_coluna(df, ["id_hospital", "ID_HOSPITAL"])
    col_nome = definir_coluna(df, ["Hospital", "HOSPITAL", "NOME_HOSPITAL"])
    col_end = definir_coluna(df, ["Endereço", "ENDERECO", "ENDEREÇO"])
    col_leitos = definir_coluna(df, ["Leitos", "LEITOS", "QTE_LEITOS"])
    col_lat = definir_coluna(df, ["LAT", "LATITUDE"])
    col_lon = definir_coluna(df, ["LOG", "LON", "LONGITUDE", "LNG"])

    regiao_atual = None
    for _, row in df.iterrows():
        regiao_bruta = limpar_str(row.get(col_regiao), None) if col_regiao else None
        if regiao_bruta:
            regiao_atual = normalizar_txt(regiao_bruta)

        municipio = limpar_str(row.get(col_municipio), None) if col_municipio else None
        municipio = normalizar_municipio(municipio)
        id_hospital = para_int(row.get(col_id_hospital)) if col_id_hospital else None
        nome_hospital = limpar_str(row.get(col_nome), None) if col_nome else None
        end_hosp = limpar_str(row.get(col_end), None) if col_end else None
        qte_leitos = para_int(row.get(col_leitos)) if col_leitos else None
        lat = corrigir_coord(row.get(col_lat)) if col_lat else np.nan
        log = corrigir_coord(row.get(col_lon)) if col_lon else np.nan
        id_municipio = banco.obter_id_municipio(municipio)
        regiao_nome = REGIAO_POR_MUNICIPIO.get(municipio) if municipio else None
        if regiao_nome is None:
            regiao_nome = regiao_atual
        id_regiao = ID_POR_REGIAO.get(regiao_nome)

        id_financiamento = None
        if col_fin:
            id_financiamento = para_int(row.get(col_fin)) if col_fin == "id_financiamento" else banco.obter_id_financiamento(row.get(col_fin))

        banco.upsert_regiao_municipio(id_regiao, id_municipio)
        if id_hospital is not None:
            banco.upsert_leito(id_municipio, id_hospital, nome_hospital, end_hosp, qte_leitos, None if pd.isna(lat) else float(lat), None if pd.isna(log) else float(log), id_financiamento)

    banco.commit()


def importar_srts(banco, xlsx):
    df = pd.read_excel(xlsx, sheet_name="srts_UAI_UAA")
    df.columns = [str(c).strip() for c in df.columns]
    col_regiao = definir_coluna(df, ["Regiões", "Região", "REGIÕES", "REGIÃO"])
    col_municipio = definir_coluna(df, ["Município", "Municipio", "MUNICÍPIO", "MUNICIPIO"])
    col_id_caps = definir_coluna(df, ["id_caps", "ID_CAPS"])
    col_rt = definir_coluna(df, ["RTs", "RTS", "rt", "RT"])
    col_uai = definir_coluna(df, ["UAI", "uai"])
    col_uaa = definir_coluna(df, ["UAA", "uaa"])

    regiao_atual = None
    for _, row in df.iterrows():
        regiao_bruta = limpar_str(row.get(col_regiao), None) if col_regiao else None
        if regiao_bruta:
            regiao_atual = normalizar_txt(regiao_bruta)

        municipio = limpar_str(row.get(col_municipio), None) if col_municipio else None
        municipio = normalizar_municipio(municipio)
        id_municipio = banco.obter_id_municipio(municipio)
        regiao_nome = REGIAO_POR_MUNICIPIO.get(municipio) if municipio else None
        if regiao_nome is None:
            regiao_nome = regiao_atual
        id_regiao = ID_POR_REGIAO.get(regiao_nome)
        banco.upsert_regiao_municipio(id_regiao, id_municipio)

        id_caps = para_int(row.get(col_id_caps)) if col_id_caps else None
        rt = para_int(row.get(col_rt)) if col_rt else None
        uai = para_int(row.get(col_uai)) if col_uai else None
        uaa = para_int(row.get(col_uaa)) if col_uaa else None
        if id_caps is not None:
            banco.upsert_srts(id_caps, rt, uai, uaa)

    banco.commit()


import geopandas as gpd


def importar_municipios_geo(banco, shp_path):
    caminho = Path(shp_path)

    if not caminho.exists():
        print("Arquivo shapefile não encontrado:", caminho)
        return

    gdf = gpd.read_file(caminho)

    # garante CRS correto
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")

    gdf = gdf.to_crs("EPSG:4326")

    ignorados = []

    for _, row in gdf.iterrows():
        nome_municipio = row.get("NM_MUN")
        id_ibge = row.get("CD_MUN")
        geometry = row.get("geometry")

        nome_norm = normalizar_municipio(nome_municipio)

        if not nome_norm:
            ignorados.append((id_ibge, nome_municipio, "nome inválido"))
            continue

        id_municipio = banco.obter_id_municipio(nome_norm)

        if id_municipio is None:
            ignorados.append((id_ibge, nome_norm, "fora da base"))
            continue

        geometry_json = json.dumps(geometry.__geo_interface__, ensure_ascii=False)

        banco.upsert_municipio_geo(
            id_municipio=id_municipio,
            id_ibge=str(id_ibge),
            nome_municipio=nome_norm,
            geometry_json=geometry_json,
        )

    banco.commit()

    if ignorados:
        print("\nMunicípios ignorados:")
        for item in ignorados:
            print(item)

def importar_tudo(xlsx_path, db_path, geojson_path=None):
    banco = BancoCaps(db_path)
    try:
        banco.criar_tabelas()
        banco.popular_regioes()
        banco.popular_municipios()
        banco.popular_regiao_municipio()
        importar_caps(banco, xlsx_path)
        importar_leitos(banco, xlsx_path)
        importar_srts(banco, xlsx_path)
        if geojson_path:
            importar_municipios_geo(banco, geojson_path)
        banco.commit()
        print("Importação concluída com sucesso.")
    finally:
        banco.fechar()


def main():
    from config import DB_PATH, MUNICIPIOS_SHP, PLANILHA_REDE_PATH
    importar_tudo(PLANILHA_REDE_PATH, DB_PATH, MUNICIPIOS_SHP)


if __name__ == "__main__":
    main()
