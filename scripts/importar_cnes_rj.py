from pathlib import Path
import zipfile

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ZIP_PATH = BASE_DIR / "data" / "processado" / "BASE_DE_DADOS_CNES_202603.ZIP"
SAIDA_HOSPITAIS = BASE_DIR / "data" / "entrada" / "hospitais_municipais_rj_cnes_202603.csv"
SAIDA_INVENTARIO = BASE_DIR / "data" / "entrada" / "inventario_equipamentos_municipais_rj_cnes_202603.csv"
SAIDA_APP = BASE_DIR / "data" / "entrada" / "hospitais_inventario.csv"

COMPETENCIA = "202603"


def ler_csv_zip(zf, nome, **kwargs):
    with zf.open(nome) as f:
        return pd.read_csv(f, sep=";", encoding="latin1", dtype=str, **kwargs)


def numero(valor):
    return pd.to_numeric(valor, errors="coerce").fillna(0).astype(int)


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


def sim_nao_ativo(valor):
    return pd.isna(valor) or str(valor).strip() == ""


def carregar_estabelecimentos(zf):
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
        "CO_TIPO_UNIDADE",
        "CO_TIPO_ESTABELECIMENTO",
        "CO_ATIVIDADE_PRINCIPAL",
        "CO_MOTIVO_DESAB",
        "TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')",
    ]
    partes = []
    with zf.open(f"tbEstabelecimento{COMPETENCIA}.csv") as f:
        for chunk in pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            dtype=str,
            usecols=lambda c: c in usecols,
            chunksize=200_000,
        ):
            chunk["CO_UNIDADE"] = chunk["CO_UNIDADE"].astype(str)
            rj = chunk[chunk["CO_UNIDADE"].str.startswith("33", na=False)].copy()
            if not rj.empty:
                partes.append(rj)
    return pd.concat(partes, ignore_index=True)


def montar_endereco(row):
    partes = [
        row.get("NO_LOGRADOURO"),
        row.get("NU_ENDERECO"),
        row.get("NO_COMPLEMENTO"),
        row.get("NO_BAIRRO"),
    ]
    texto = ", ".join([str(p).strip() for p in partes if pd.notna(p) and str(p).strip()])
    cep = row.get("CO_CEP")
    if pd.notna(cep) and str(cep).strip():
        texto = f"{texto} - CEP {str(cep).strip()}"
    return texto


def selecionar_hospitais_municipais(est):
    texto_nome = (
        est["NO_FANTASIA"].fillna("").str.upper()
        + " "
        + est["NO_RAZAO_SOCIAL"].fillna("").str.upper()
    )
    nome_hospital_municipal = texto_nome.str.contains("HOSPITAL MUNICIPAL", regex=False)
    hospital_natureza_municipio = (
        est["CO_TIPO_ESTABELECIMENTO"].eq("006")
        & est["CO_NATUREZA_JUR"].eq("1244")
    )
    ativo = est["CO_MOTIVO_DESAB"].apply(sim_nao_ativo)
    gestao_municipal = est["TP_GESTAO"].eq("M")

    selecionados = est[ativo & gestao_municipal & (nome_hospital_municipal | hospital_natureza_municipio)].copy()
    selecionados["CRITERIO_SELECAO"] = "nome Hospital Municipal"
    selecionados.loc[hospital_natureza_municipio.loc[selecionados.index], "CRITERIO_SELECAO"] = "tipo hospital + natureza Municipio"
    selecionados.loc[
        nome_hospital_municipal.loc[selecionados.index] & hospital_natureza_municipio.loc[selecionados.index],
        "CRITERIO_SELECAO",
    ] = "nome Hospital Municipal + tipo hospital/natureza Municipio"
    return selecionados


def carregar_municipios(zf):
    municipios = ler_csv_zip(zf, f"tbMunicipio{COMPETENCIA}.csv")
    return municipios[["CO_MUNICIPIO", "NO_MUNICIPIO", "CO_SIGLA_ESTADO"]]


def carregar_inventario(zf, unidades):
    unidades = set(unidades)
    partes = []
    usecols = ["CO_UNIDADE", "CO_EQUIPAMENTO", "CO_TIPO_EQUIPAMENTO", "QT_EXISTENTE", "QT_USO", "QT_SUS"]
    with zf.open(f"rlEstabEquipamento{COMPETENCIA}.csv") as f:
        for chunk in pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            dtype=str,
            usecols=lambda c: c in usecols,
            chunksize=300_000,
        ):
            dff = chunk[chunk["CO_UNIDADE"].isin(unidades)].copy()
            if not dff.empty:
                partes.append(dff)
    if not partes:
        return pd.DataFrame(columns=usecols)
    inventario = pd.concat(partes, ignore_index=True)
    inventario["QT_EXISTENTE"] = numero(inventario["QT_EXISTENTE"])
    inventario["QT_USO"] = numero(inventario["QT_USO"])
    inventario["QT_SUS"] = numero(inventario["QT_SUS"])

    equipamentos = ler_csv_zip(zf, f"tbEquipamento{COMPETENCIA}.csv")
    tipos = ler_csv_zip(zf, f"tbTipoEquipamento{COMPETENCIA}.csv")
    for df in [inventario, equipamentos, tipos]:
        for col in ["CO_EQUIPAMENTO", "CO_TIPO_EQUIPAMENTO"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

    inventario = inventario.merge(
        equipamentos[["CO_EQUIPAMENTO", "CO_TIPO_EQUIPAMENTO", "DS_EQUIPAMENTO"]],
        on=["CO_EQUIPAMENTO", "CO_TIPO_EQUIPAMENTO"],
        how="left",
    )
    inventario = inventario.merge(
        tipos[["CO_TIPO_EQUIPAMENTO", "DS_TIPO_EQUIPAMENTO"]],
        on="CO_TIPO_EQUIPAMENTO",
        how="left",
    )
    inventario["QT_OCIOSO_ESTIMADO"] = (inventario["QT_EXISTENTE"] - inventario["QT_USO"]).clip(lower=0)
    return inventario


def carregar_leitos(zf, unidades):
    unidades = set(unidades)
    partes = []
    usecols = ["CO_UNIDADE", "CO_LEITO", "CO_TIPO_LEITO", "QT_EXIST", "QT_CONTR", "QT_SUS"]
    with zf.open(f"rlEstabComplementar{COMPETENCIA}.csv") as f:
        for chunk in pd.read_csv(
            f,
            sep=";",
            encoding="latin1",
            dtype=str,
            usecols=lambda c: c in usecols,
            chunksize=200_000,
        ):
            dff = chunk[chunk["CO_UNIDADE"].isin(unidades)].copy()
            if not dff.empty:
                partes.append(dff)
    if not partes:
        return pd.DataFrame(columns=["CO_UNIDADE", "LEITOS"])
    leitos = pd.concat(partes, ignore_index=True)
    leitos["QT_EXIST"] = numero(leitos["QT_EXIST"])
    return leitos.groupby("CO_UNIDADE", as_index=False).agg(LEITOS=("QT_EXIST", "sum"))


def main():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Base CNES nao encontrada: {ZIP_PATH}")

    with zipfile.ZipFile(ZIP_PATH) as zf:
        est = carregar_estabelecimentos(zf)
        municipios = carregar_municipios(zf)
        hospitais = selecionar_hospitais_municipais(est)
        hospitais = hospitais.merge(
            municipios,
            left_on="CO_MUNICIPIO_GESTOR",
            right_on="CO_MUNICIPIO",
            how="left",
        )
        hospitais["ENDERECO"] = hospitais.apply(montar_endereco, axis=1)
        hospitais["LAT"] = hospitais["NU_LATITUDE"].apply(normalizar_coord)
        hospitais["LON"] = hospitais["NU_LONGITUDE"].apply(normalizar_coord)

        inventario = carregar_inventario(zf, hospitais["CO_UNIDADE"])
        leitos = carregar_leitos(zf, hospitais["CO_UNIDADE"])
        resumo = (
            inventario.groupby("CO_UNIDADE", as_index=False)
            .agg(
                EQUIPAMENTOS_TOTAL=("QT_EXISTENTE", "sum"),
                OPERACIONAIS=("QT_USO", "sum"),
                OCIOSOS=("QT_OCIOSO_ESTIMADO", "sum"),
            )
        )

    hospitais_saida = hospitais[
        [
            "CO_UNIDADE",
            "CO_CNES",
            "NO_FANTASIA",
            "NO_RAZAO_SOCIAL",
            "CRITERIO_SELECAO",
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
            "CO_ATIVIDADE_PRINCIPAL",
            "TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')",
        ]
    ].sort_values(["NO_MUNICIPIO", "NO_FANTASIA"])
    hospitais_saida.to_csv(SAIDA_HOSPITAIS, index=False, encoding="utf-8-sig")

    inventario_saida = inventario.merge(
        hospitais[["CO_UNIDADE", "CO_CNES", "NO_FANTASIA", "NO_MUNICIPIO"]],
        on="CO_UNIDADE",
        how="left",
    )
    inventario_saida = inventario_saida[
        [
            "CO_UNIDADE",
            "CO_CNES",
            "NO_FANTASIA",
            "NO_MUNICIPIO",
            "CO_TIPO_EQUIPAMENTO",
            "DS_TIPO_EQUIPAMENTO",
            "CO_EQUIPAMENTO",
            "DS_EQUIPAMENTO",
            "QT_EXISTENTE",
            "QT_USO",
            "QT_SUS",
            "QT_OCIOSO_ESTIMADO",
        ]
    ].sort_values(["NO_MUNICIPIO", "NO_FANTASIA", "DS_TIPO_EQUIPAMENTO", "DS_EQUIPAMENTO"])
    inventario_saida.to_csv(SAIDA_INVENTARIO, index=False, encoding="utf-8-sig")

    app_df = hospitais.merge(resumo, on="CO_UNIDADE", how="left")
    app_df = app_df.merge(leitos, on="CO_UNIDADE", how="left")
    for col in ["EQUIPAMENTOS_TOTAL", "OPERACIONAIS", "OCIOSOS"]:
        app_df[col] = pd.to_numeric(app_df[col], errors="coerce").fillna(0).astype(int)
    app_df["MANUTENCAO"] = 0
    app_df["DESCARTE"] = 0
    app_df["ID_HOSPITAL"] = app_df["CO_CNES"]
    app_df["NOME_HOSPITAL"] = app_df["NO_FANTASIA"]
    app_df["ESFERA"] = "Municipal"
    app_df["MUNICIPIO"] = app_df["NO_MUNICIPIO"]
    app_df["REGIAO"] = "A classificar"
    app_df["LEITOS"] = pd.to_numeric(app_df["LEITOS"], errors="coerce").fillna(0).astype(int)
    app_df[
        [
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
        ]
    ].sort_values(["MUNICIPIO", "NOME_HOSPITAL"]).to_csv(SAIDA_APP, index=False, encoding="utf-8-sig")

    print(f"Hospitais municipais/candidatos RJ: {len(hospitais_saida)}")
    print(f"Linhas de inventario de equipamentos: {len(inventario_saida)}")
    print(f"Arquivos gerados:\\n- {SAIDA_HOSPITAIS}\\n- {SAIDA_INVENTARIO}\\n- {SAIDA_APP}")


if __name__ == "__main__":
    main()
