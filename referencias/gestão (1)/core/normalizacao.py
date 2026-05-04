import re
import unicodedata
from typing import Iterable

import pandas as pd


def normalizar_txt(valor):
    if pd.isna(valor) or valor is None:
        return None
    valor = str(valor).strip()
    if valor in {"", "?", "nan", "None", "NULL", "null"}:
        return None
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    valor = re.sub(r"\s+", " ", valor)
    return valor.upper().strip()


def normalizar_texto(valor):
    return normalizar_txt(valor)


def limpar_str(v, padrao=""):
    if pd.isna(v) or v is None:
        return padrao
    s = str(v).strip()
    return s if s else padrao


def limpar_valor(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if valor in {"", "?", "nan", "None", "NULL", "null"}:
            return None
    return valor


def definir_coluna(df, candidatas: Iterable[str]):
    for col in candidatas:
        if col in df.columns:
            return col
    return None


def para_int(valor):
    if valor is None or pd.isna(valor):
        return None
    try:
        return int(float(valor))
    except Exception:
        return None


def para_float(valor):
    if valor is None or pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    s = str(valor).strip()
    if s in {"", "?", "nan", "None", "NULL", "null"}:
        return None

    s = s.replace(" ", "")
    if re.fullmatch(r"-?\d{7,}", s):
        try:
            return int(s) / 10_000_000
        except Exception:
            pass

    s2 = re.sub(r"[^0-9,\.-]", "", s)
    if s2.count(".") > 1 and "," not in s2:
        neg = s2.startswith("-")
        digs = re.sub(r"[^0-9]", "", s2)
        if len(digs) >= 3:
            s2 = ("-" if neg else "") + digs[:2] + "." + digs[2:]

    s2 = s2.replace(",", ".")
    try:
        return float(s2)
    except Exception:
        return None


def normalizar_municipio(nome):
    nome = normalizar_txt(nome)
    if not nome:
        return None
    ajustes = {
        "ARMACAO DE BUZIOS": "ARMACAO DOS BUZIOS",
        "CASSIMIRO DE ABREU": "CASIMIRO DE ABREU",
        "SUMIDORO": "SUMIDOURO",
        "PATY DOS ALFERES": "PATY DO ALFERES",
    }
    return ajustes.get(nome, nome)


def normalizar_regiao_nome(nome):
    nome = normalizar_texto(nome)
    if nome is None:
        return None
    nome = nome.replace("REGIAO ", "").strip()
    return nome
