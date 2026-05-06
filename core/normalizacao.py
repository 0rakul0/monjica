import re
import unicodedata

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


def normalizar_municipio(nome):
    nome = normalizar_txt(nome)
    if not nome:
        return None

    ajustes = {
        "ARMACAO DE BUZIOS": "ARMACAO DOS BUZIOS",
        "CASSIMIRO DE ABREU": "CASIMIRO DE ABREU",
        "SUMIDORO": "SUMIDOURO",
        "PATY DOS ALFERES": "PATY DO ALFERES",
        "PARATI": "PARATY",
    }
    return ajustes.get(nome, nome)


def normalizar_regiao_nome(nome):
    nome = normalizar_txt(nome)
    if nome is None:
        return None

    mapa = {
        "REGIAO BAIXADA LITORANEA": "REGIÃO BAIXADA LITORÂNEA",
        "BAIXADA LITORANEA": "REGIÃO BAIXADA LITORÂNEA",
        "REGIAO MEDIO PARAIBA": "REGIÃO MÉDIO PARAÍBA",
        "MEDIO PARAIBA": "REGIÃO MÉDIO PARAÍBA",
        "REGIAO BAIA DA ILHA GRANDE": "REGIÃO BAÍA DA ILHA GRANDE",
        "BAIA DA ILHA GRANDE": "REGIÃO BAÍA DA ILHA GRANDE",
        "REGIAO CENTRO-SUL": "REGIÃO CENTRO-SUL",
        "CENTRO-SUL": "REGIÃO CENTRO-SUL",
        "REGIAO METROPOLITANA I": "REGIÃO METROPOLITANA I",
        "METROPOLITANA I": "REGIÃO METROPOLITANA I",
        "REGIAO METROPOLITANA II": "REGIÃO METROPOLITANA II",
        "METROPOLITANA II": "REGIÃO METROPOLITANA II",
        "REGIAO NORTE": "REGIÃO NORTE",
        "NORTE": "REGIÃO NORTE",
        "REGIAO NOROESTE": "REGIÃO NOROESTE",
        "NOROESTE": "REGIÃO NOROESTE",
        "REGIAO SERRANA": "REGIÃO SERRANA",
        "SERRANA": "REGIÃO SERRANA",
    }
    return mapa.get(nome, nome.title())

