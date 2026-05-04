from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
SAIDA = BASE_DIR / "data" / "entrada" / "referencia_local_hospitais.csv"


def achar_planilha():
    candidatos = list((BASE_DIR / "referencias").rglob("*.xlsx"))
    for caminho in candidatos:
        if "caps" in caminho.name.lower() and not caminho.name.startswith("~$"):
            return caminho
    raise FileNotFoundError("Planilha de referencia nao encontrada em referencias/**/*.xlsx")


def cnes(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto.zfill(7)


def main():
    planilha = achar_planilha()
    leitos = pd.read_excel(planilha, sheet_name="leitos", dtype={"CNES": str})
    regioes = pd.read_excel(planilha, sheet_name="regiao")

    regioes = regioes.drop_duplicates(subset=["id_regiao"]).copy()
    leitos = leitos.merge(regioes, on="id_regiao", how="left")
    leitos["CNES"] = leitos["CNES"].apply(cnes)

    col_municipio = next(c for c in leitos.columns if c.startswith("Mun"))
    saida = leitos.rename(
        columns={
            "CNES": "ID_HOSPITAL",
            "Hospital": "HOSPITAL_REFERENCIA",
            col_municipio: "MUNICIPIO_REFERENCIA",
            "Endereço": "ENDERECO_REFERENCIA",
            "Leitos": "LEITOS_REFERENCIA",
            "TEL": "TELEFONE_REFERENCIA",
            "email": "EMAIL_REFERENCIA",
            "Região": "REGIAO_REFERENCIA",
        }
    )[
        [
            "ID_HOSPITAL",
            "HOSPITAL_REFERENCIA",
            "MUNICIPIO_REFERENCIA",
            "REGIAO_REFERENCIA",
            "ENDERECO_REFERENCIA",
            "LEITOS_REFERENCIA",
            "LAT",
            "LOG",
            "TELEFONE_REFERENCIA",
            "EMAIL_REFERENCIA",
        ]
    ].copy()

    saida.to_csv(SAIDA, index=False, encoding="utf-8-sig")
    print(f"Referencia local: {len(saida)} hospitais")
    print(f"Com telefone: {saida['TELEFONE_REFERENCIA'].notna().sum()}")
    print(f"Com e-mail: {saida['EMAIL_REFERENCIA'].notna().sum()}")
    print(f"Arquivo gerado: {SAIDA}")


if __name__ == "__main__":
    main()
