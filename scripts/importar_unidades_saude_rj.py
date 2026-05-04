from pathlib import Path
import re
import unicodedata
import zipfile

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ZIP_PATH = BASE_DIR / "data" / "processado" / "BASE_DE_DADOS_CNES_202603.ZIP"
SAIDA = BASE_DIR / "data" / "entrada" / "unidades_saude_municipais_rj_cnes_202603.csv"
CORRECOES_COORDENADAS = BASE_DIR / "data" / "entrada" / "correcoes_coordenadas_unidades.csv"
COMPETENCIA = "202603"


def normalizar(txt):
    txt = "" if pd.isna(txt) else str(txt)
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^A-Za-z0-9]+", " ", txt).upper()
    return re.sub(r"\s+", " ", txt).strip()


def normalizar_coord(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip().replace(",", ".")
    try:
        num = float(texto)
    except ValueError:
        return None
    while abs(num) > 180:
        num = num / 10
    return num


def montar_endereco(row):
    partes = [row.get("NO_LOGRADOURO"), row.get("NU_ENDERECO"), row.get("NO_COMPLEMENTO"), row.get("NO_BAIRRO")]
    endereco = ", ".join([str(p).strip() for p in partes if pd.notna(p) and str(p).strip()])
    cep = row.get("CO_CEP")
    if pd.notna(cep) and str(cep).strip():
        endereco = f"{endereco} - CEP {str(cep).strip()}"
    return endereco


def classificar_unidade(row):
    nome = normalizar(f"{row.get('NO_FANTASIA', '')} {row.get('NO_RAZAO_SOCIAL', '')}")
    tipo_estab = str(row.get("CO_TIPO_ESTABELECIMENTO") or "").zfill(3)

    if tipo_estab == "008" or " UPA " in f" {nome} " or "UNIDADE DE PRONTO ATENDIMENTO" in nome:
        return "UPA / Pronto atendimento"

    if "CLINICA DA FAMILIA" in nome:
        return "Clinica da familia"

    padroes_basicos = [
        "UBS",
        "USF",
        "UNIDADE DE SAUDE DA FAMILIA",
        "CLINICA DA FAMILIA",
        "POSTO DE SAUDE",
        "CENTRO DE SAUDE",
        "CENTRO MUNICIPAL DE SAUDE",
    ]
    if tipo_estab == "001" or any(p in nome for p in padroes_basicos):
        if "POSTO DE SAUDE" in nome:
            return "Posto de saude"
        if "UPA" in nome:
            return "UPA / Pronto atendimento"
        return "UBS / Atencao basica"

    return None


def main():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Base CNES nao encontrada: {ZIP_PATH}")

    usecols = [
        "CO_UNIDADE",
        "CO_CNES",
        "NO_RAZAO_SOCIAL",
        "NO_FANTASIA",
        "NO_LOGRADOURO",
        "NU_ENDERECO",
        "NO_COMPLEMENTO",
        "NO_BAIRRO",
        "CO_CEP",
        "NU_TELEFONE",
        "NO_EMAIL",
        "CO_MUNICIPIO_GESTOR",
        "NU_LATITUDE",
        "NU_LONGITUDE",
        "CO_NATUREZA_JUR",
        "TP_GESTAO",
        "CO_TIPO_ESTABELECIMENTO",
        "CO_MOTIVO_DESAB",
        "TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')",
    ]

    partes = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        with zf.open(f"tbEstabelecimento{COMPETENCIA}.csv") as f:
            for chunk in pd.read_csv(
                f,
                sep=";",
                encoding="latin1",
                dtype=str,
                usecols=lambda c: c in usecols,
                chunksize=200_000,
            ):
                rj = chunk[
                    chunk["CO_UNIDADE"].astype(str).str.startswith("33", na=False)
                    & chunk["TP_GESTAO"].eq("M")
                    & chunk["CO_MOTIVO_DESAB"].isna()
                ].copy()
                if not rj.empty:
                    partes.append(rj)

        municipios = pd.read_csv(
            zf.open(f"tbMunicipio{COMPETENCIA}.csv"),
            sep=";",
            encoding="latin1",
            dtype=str,
            usecols=["CO_MUNICIPIO", "NO_MUNICIPIO", "CO_SIGLA_ESTADO"],
        )

        tipo_estabelecimento = pd.read_csv(
            zf.open(f"tbTipoEstabelecimento{COMPETENCIA}.csv"),
            sep=";",
            encoding="latin1",
            dtype=str,
            usecols=["CO_TIPO_ESTABELECIMENTO", "DS_TIPO_ESTABELECIMENTO"],
        )

    est = pd.concat(partes, ignore_index=True)
    est["CATEGORIA_UNIDADE"] = est.apply(classificar_unidade, axis=1)
    est = est[est["CATEGORIA_UNIDADE"].notna()].copy()

    est = est.merge(municipios, left_on="CO_MUNICIPIO_GESTOR", right_on="CO_MUNICIPIO", how="left")
    est = est.merge(tipo_estabelecimento, on="CO_TIPO_ESTABELECIMENTO", how="left")
    est["ENDERECO"] = est.apply(montar_endereco, axis=1)
    est["LAT"] = est["NU_LATITUDE"].apply(normalizar_coord)
    est["LON"] = est["NU_LONGITUDE"].apply(normalizar_coord)

    saida = est[
        [
            "CO_UNIDADE",
            "CO_CNES",
            "NO_FANTASIA",
            "NO_RAZAO_SOCIAL",
            "CATEGORIA_UNIDADE",
            "DS_TIPO_ESTABELECIMENTO",
            "ENDERECO",
            "NO_BAIRRO",
            "CO_CEP",
            "NO_MUNICIPIO",
            "CO_MUNICIPIO_GESTOR",
            "NU_TELEFONE",
            "NO_EMAIL",
            "LAT",
            "LON",
            "CO_NATUREZA_JUR",
            "TP_GESTAO",
            "CO_TIPO_ESTABELECIMENTO",
            "TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')",
        ]
    ].sort_values(["CATEGORIA_UNIDADE", "NO_MUNICIPIO", "NO_FANTASIA"])

    if CORRECOES_COORDENADAS.exists():
        correcoes = pd.read_csv(CORRECOES_COORDENADAS, dtype={"CO_CNES": str})
        correcoes["CO_CNES"] = correcoes["CO_CNES"].astype(str).str.zfill(7)
        for _, correcao in correcoes.iterrows():
            mask = saida["CO_CNES"].astype(str).str.zfill(7).eq(correcao["CO_CNES"])
            if mask.any():
                saida.loc[mask, "LAT"] = float(correcao["LAT_CORRIGIDA"])
                saida.loc[mask, "LON"] = float(correcao["LON_CORRIGIDA"])

    saida.to_csv(SAIDA, index=False, encoding="utf-8-sig")

    print(f"Unidades extraidas: {len(saida)}")
    print(saida["CATEGORIA_UNIDADE"].value_counts().to_string())
    print(f"Arquivo gerado: {SAIDA}")


if __name__ == "__main__":
    main()
