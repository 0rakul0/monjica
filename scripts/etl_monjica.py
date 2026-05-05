from __future__ import annotations

import argparse
import sqlite3
import unicodedata
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "entrada"
DB_PATH = ROOT / "banco" / "monjica.db"
SCHEMA_PATH = ROOT / "sql" / "schema_monjica.sqlite.sql"

ARQ_UNIDADES = DATA_DIR / "unidades_saude_municipais_rj_cnes_202603.csv"
ARQ_HOSPITAIS = DATA_DIR / "hospitais_municipais_rj_cnes_202603.csv"
ARQ_INVENTARIO = DATA_DIR / "inventario_equipamentos_municipais_rj_cnes_202603.csv"
ARQ_HOSPITAIS_RESUMO = DATA_DIR / "hospitais_inventario.csv"
ARQ_REFERENCIA_LOCAL = DATA_DIR / "referencia_local_hospitais.csv"


def uid() -> str:
    return str(uuid.uuid4())


def chave_cnes(valor: Any) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    texto = "".join(ch for ch in texto if ch.isdigit())
    return texto.zfill(7) if texto else ""


def normalizar_texto(valor: Any) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def normalizar_coord(valor: Any) -> float | None:
    if pd.isna(valor):
        return None
    texto = str(valor).strip().replace(",", ".")
    if texto in {"", "nan", "None"}:
        return None
    try:
        numero = float(texto)
    except ValueError:
        return None
    while abs(numero) > 180:
        numero = numero / 10
    return numero


def limpar_str(valor: Any) -> str | None:
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto if texto else None


def to_int(valor: Any, default: int = 0) -> int:
    try:
        if pd.isna(valor):
            return default
        return int(float(valor))
    except Exception:
        return default


def inferir_esfera(nome: Any, natureza: Any = None) -> str:
    texto = normalizar_texto(nome)
    natureza_txt = normalizar_texto(natureza)
    if "ESTADUAL" in texto or "INSTITUTO ESTADUAL" in texto:
        return "Estadual"
    if "MUNICIPAL" in texto or "SMS" in texto or "SECRETARIA MUNICIPAL" in natureza_txt:
        return "Municipal"
    return "A classificar"


def inferir_porte(leitos: int, equipamentos: int) -> tuple[str, str]:
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


def potencial(total: int, ociosos: int, manutencao: int, descarte: int) -> tuple[str, float]:
    if total <= 0:
        return "Inventário pendente", 0.0
    score = max(0, min(100, round(((ociosos * 1.0) + (manutencao * 0.6) - (descarte * 0.4)) / total * 100, 1)))
    taxa = (ociosos + manutencao) / total
    if descarte / total >= 0.5:
        return "Baixo", score
    if taxa >= 0.30:
        return "Alto", score
    if taxa >= 0.10:
        return "Médio", score
    return "Baixo", score


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        print(f"⚠️ Arquivo não encontrado: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, **kwargs)


def criar_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def log(conn: sqlite3.Connection, etapa: str, linhas: int, obs: str = "") -> None:
    conn.execute("INSERT INTO etl_log(etapa, linhas, observacao) VALUES (?, ?, ?)", (etapa, linhas, obs))


def mapa_estabelecimentos(conn: sqlite3.Connection) -> dict[str, str]:
    df = pd.read_sql_query("SELECT id, cnes FROM estabelecimentos_saude", conn)
    return dict(zip(df["cnes"], df["id"]))


def montar_estabelecimentos() -> pd.DataFrame:
    unidades = read_csv(ARQ_UNIDADES, dtype={"CO_CNES": str, "CO_UNIDADE": str})
    hospitais = read_csv(ARQ_HOSPITAIS, dtype={"CO_CNES": str, "CO_UNIDADE": str})
    registros: list[pd.DataFrame] = []

    if not unidades.empty:
        u = unidades.copy()
        u["fonte"] = "unidades_saude_municipais_rj_cnes_202603"
        u["criterio_selecao"] = None
        u["co_atividade_principal"] = None
        registros.append(u)

    if not hospitais.empty:
        h = hospitais.copy()
        h["fonte"] = "hospitais_municipais_rj_cnes_202603"
        if "CATEGORIA_UNIDADE" not in h.columns:
            h["CATEGORIA_UNIDADE"] = "Hospital"
        if "DS_TIPO_ESTABELECIMENTO" not in h.columns:
            h["DS_TIPO_ESTABELECIMENTO"] = "HOSPITAL"
        registros.append(h)

    if not registros:
        return pd.DataFrame()

    df = pd.concat(registros, ignore_index=True, sort=False)
    df["cnes"] = df.get("CO_CNES", "").apply(chave_cnes)
    df = df[df["cnes"] != ""].copy()
    df["latitude"] = df.get("LAT").apply(normalizar_coord)
    df["longitude"] = df.get("LON").apply(normalizar_coord)
    df["municipio"] = df.get("NO_MUNICIPIO").apply(limpar_str)
    df["id_municipio"] = df.get("CO_MUNICIPIO_GESTOR").apply(lambda x: str(int(float(x))).zfill(6) if pd.notna(x) and str(x).strip() else None)
    df["nome_fantasia"] = df.get("NO_FANTASIA").apply(limpar_str)
    df["razao_social"] = df.get("NO_RAZAO_SOCIAL").apply(limpar_str)

    data_col = "TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')"
    if data_col not in df.columns:
        df[data_col] = None

    out = pd.DataFrame({
        "id": [uid() for _ in range(len(df))],
        "cnes": df["cnes"],
        "co_unidade": df.get("CO_UNIDADE"),
        "nome_fantasia": df["nome_fantasia"].fillna("Não informado"),
        "razao_social": df["razao_social"],
        "categoria_unidade": df.get("CATEGORIA_UNIDADE"),
        "tipo_estabelecimento": df.get("DS_TIPO_ESTABELECIMENTO"),
        "criterio_selecao": df.get("CRITERIO_SELECAO"),
        "endereco": df.get("ENDERECO"),
        "bairro": df.get("NO_BAIRRO"),
        "cep": df.get("CO_CEP"),
        "id_municipio": df["id_municipio"],
        "municipio": df["municipio"],
        "telefone": df.get("NU_TELEFONE"),
        "email": df.get("NO_EMAIL"),
        "latitude": df["latitude"],
        "longitude": df["longitude"],
        "natureza_juridica": df.get("CO_NATUREZA_JUR"),
        "tipo_gestao": df.get("TP_GESTAO"),
        "co_tipo_estabelecimento": df.get("CO_TIPO_ESTABELECIMENTO"),
        "co_atividade_principal": df.get("CO_ATIVIDADE_PRINCIPAL"),
        "data_atualizacao": df[data_col],
        "fonte": df["fonte"],
    })
    out["rank"] = out["fonte"].str.contains("hospitais", case=False, na=False).astype(int)
    out = out.sort_values(["cnes", "rank"]).drop_duplicates("cnes", keep="last").drop(columns="rank")
    return out


def popular_municipios(conn: sqlite3.Connection, estabelecimentos: pd.DataFrame) -> None:
    if estabelecimentos.empty:
        return
    mun = estabelecimentos.dropna(subset=["id_municipio", "municipio"]).copy()
    mun["nome_municipio_norm"] = mun["municipio"].apply(normalizar_texto)
    coords = mun.dropna(subset=["latitude", "longitude"]).groupby("id_municipio", as_index=False).agg(
        lat_media=("latitude", "mean"), lon_media=("longitude", "mean")
    )
    mun = mun.groupby(["id_municipio", "municipio", "nome_municipio_norm"], as_index=False).size().drop(columns="size")
    mun = mun.merge(coords, on="id_municipio", how="left")
    mun["regiao"] = "A classificar"
    mun = mun.rename(columns={"municipio": "nome_municipio"})[["id_municipio", "nome_municipio", "nome_municipio_norm", "regiao", "lat_media", "lon_media"]]
    mun.to_sql("municipios", conn, if_exists="append", index=False)
    log(conn, "municipios", len(mun))


def popular_estabelecimentos(conn: sqlite3.Connection, estabelecimentos: pd.DataFrame) -> None:
    if estabelecimentos.empty:
        return
    estabelecimentos.to_sql("estabelecimentos_saude", conn, if_exists="append", index=False)
    log(conn, "estabelecimentos_saude", len(estabelecimentos))


def popular_inventario(conn: sqlite3.Connection) -> pd.DataFrame:
    inv = read_csv(ARQ_INVENTARIO, dtype={"CO_CNES": str})
    if inv.empty:
        return inv
    mapa = mapa_estabelecimentos(conn)
    for c in ["QT_EXISTENTE", "QT_USO", "QT_SUS", "QT_OCIOSO_ESTIMADO"]:
        inv[c] = pd.to_numeric(inv.get(c, 0), errors="coerce").fillna(0).astype(int)
    inv["cnes"] = inv["CO_CNES"].apply(chave_cnes)
    inv["id_estabelecimento"] = inv["cnes"].map(mapa)
    inv = inv.dropna(subset=["id_estabelecimento"]).copy()
    inv["id"] = [uid() for _ in range(len(inv))]
    out = pd.DataFrame({
        "id": inv["id"],
        "id_estabelecimento": inv["id_estabelecimento"],
        "cnes": inv["cnes"],
        "co_tipo_equipamento": inv.get("CO_TIPO_EQUIPAMENTO"),
        "tipo_equipamento": inv.get("DS_TIPO_EQUIPAMENTO", "Não informado"),
        "co_equipamento": inv.get("CO_EQUIPAMENTO"),
        "equipamento": inv.get("DS_EQUIPAMENTO", "Não informado"),
        "qt_existente": inv["QT_EXISTENTE"],
        "qt_uso": inv["QT_USO"],
        "qt_sus": inv["QT_SUS"],
        "qt_ocioso_estimado": inv["QT_OCIOSO_ESTIMADO"],
        "manutencao": 0,
        "descarte": 0,
        "para_instalacao": 0,
        "fonte": "CNES_202603",
    })
    out.to_sql("inventario_equipamentos_cnes", conn, if_exists="append", index=False)
    log(conn, "inventario_equipamentos_cnes", len(out))
    return out


def popular_hospitais_perfil(conn: sqlite3.Connection, estabelecimentos: pd.DataFrame, inventario: pd.DataFrame) -> None:
    hospitais = read_csv(ARQ_HOSPITAIS_RESUMO, dtype={"ID_HOSPITAL": str})
    referencia = read_csv(ARQ_REFERENCIA_LOCAL, dtype={"ID_HOSPITAL": str})
    hosp_cnes = set(read_csv(ARQ_HOSPITAIS, dtype={"CO_CNES": str}).get("CO_CNES", pd.Series(dtype=str)).apply(chave_cnes))
    base = estabelecimentos[estabelecimentos["cnes"].isin(hosp_cnes)].copy()

    agg = pd.DataFrame(columns=["cnes", "equipamentos_total", "equipamentos_em_uso", "equipamentos_sus", "equipamentos_ociosos_estimados"])
    if not inventario.empty:
        agg = inventario.groupby("cnes", as_index=False).agg(
            equipamentos_total=("qt_existente", "sum"),
            equipamentos_em_uso=("qt_uso", "sum"),
            equipamentos_sus=("qt_sus", "sum"),
            equipamentos_ociosos_estimados=("qt_ocioso_estimado", "sum"),
        )

    perfil = base[["id", "cnes", "nome_fantasia", "natureza_juridica"]].merge(agg, on="cnes", how="left")
    for c in ["equipamentos_total", "equipamentos_em_uso", "equipamentos_sus", "equipamentos_ociosos_estimados"]:
        perfil[c] = pd.to_numeric(perfil[c], errors="coerce").fillna(0).astype(int)

    if not hospitais.empty:
        hospitais["cnes"] = hospitais["ID_HOSPITAL"].apply(chave_cnes)
        hospitais_small = hospitais[[c for c in ["cnes", "ESFERA", "REGIAO", "LEITOS"] if c in hospitais.columns]].copy()
        perfil = perfil.merge(hospitais_small, on="cnes", how="left")
    else:
        perfil["ESFERA"] = None; perfil["REGIAO"] = None; perfil["LEITOS"] = 0

    if not referencia.empty:
        referencia["cnes"] = referencia["ID_HOSPITAL"].apply(chave_cnes)
        ref_cols = [c for c in ["cnes", "LEITOS_REFERENCIA", "TELEFONE_REFERENCIA", "EMAIL_REFERENCIA", "ENDERECO_REFERENCIA", "LAT", "LOG", "REGIAO_REFERENCIA"] if c in referencia.columns]
        perfil = perfil.merge(referencia[ref_cols], on="cnes", how="left")

    rows = []
    for _, r in perfil.iterrows():
        total = to_int(r.get("equipamentos_total")); uso = to_int(r.get("equipamentos_em_uso")); sus = to_int(r.get("equipamentos_sus"))
        ocioso = to_int(r.get("equipamentos_ociosos_estimados")); leitos = to_int(r.get("LEITOS")); leitos_ref = to_int(r.get("LEITOS_REFERENCIA"))
        porte, criterio = inferir_porte(leitos, total); pot, score = potencial(total, ocioso, 0, 0)
        rows.append({
            "id": uid(),
            "id_estabelecimento": r["id"],
            "cnes": r["cnes"],
            "esfera": r.get("ESFERA") or inferir_esfera(r.get("nome_fantasia"), r.get("natureza_juridica")),
            "porte": porte,
            "criterio_porte": criterio,
            "regiao": r.get("REGIAO_REFERENCIA") or r.get("REGIAO") or "A classificar",
            "leitos_cnes": leitos,
            "leitos_referencia": leitos_ref,
            "telefone_referencia": r.get("TELEFONE_REFERENCIA"),
            "email_referencia": r.get("EMAIL_REFERENCIA"),
            "endereco_referencia": r.get("ENDERECO_REFERENCIA"),
            "lat_referencia": normalizar_coord(r.get("LAT")),
            "lon_referencia": normalizar_coord(r.get("LOG")),
            "equipamentos_total": total,
            "equipamentos_em_uso": uso,
            "equipamentos_sus": sus,
            "equipamentos_ociosos_estimados": ocioso,
            "manutencao": 0,
            "descarte": 0,
            "potencial_reaproveitamento": pot,
            "score_reaproveitamento": score,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_sql("hospitais_perfil", conn, if_exists="append", index=False)
    log(conn, "hospitais_perfil", len(out))


def popular_equipamentos_expandidos(conn: sqlite3.Connection, limite_expandir: int | None = None) -> None:
    inv = pd.read_sql_query("SELECT * FROM inventario_equipamentos_cnes", conn)
    rows = []
    for _, r in inv.iterrows():
        existente = to_int(r["qt_existente"]); uso = to_int(r["qt_uso"]); ocioso = to_int(r["qt_ocioso_estimado"])
        n = existente if limite_expandir is None else min(existente, limite_expandir)
        for i in range(n):
            estado = "ativo" if i < uso else "ocioso"
            if i >= uso + ocioso:
                estado = "ativo"
            rows.append({
                "id": uid(),
                "id_inventario": r["id"],
                "id_estabelecimento": r["id_estabelecimento"],
                "cnes_atual": r["cnes"],
                "tipo_equipamento": r["tipo_equipamento"],
                "equipamento": r["equipamento"],
                "modelo": None,
                "fabricante": None,
                "numero_patrimonio": None,
                "data_aquisicao": None,
                "vida_util_estimada": 120,
                "estado_atual": estado,
                "status_triagem": "pendente",
                "origem_dado": "CNES_expandido_sem_patrimonio",
            })
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_sql("equipamentos", conn, if_exists="append", index=False)
    log(conn, "equipamentos", len(out), "Registros expandidos a partir de QT_EXISTENTE; sem número patrimonial individual no CNES.")


def popular_demanda_inicial(conn: sqlite3.Connection) -> None:
    inv = pd.read_sql_query("""
        SELECT es.id_municipio, es.municipio, i.tipo_equipamento,
               SUM(i.qt_existente) AS existente,
               SUM(i.qt_uso) AS uso
        FROM inventario_equipamentos_cnes i
        JOIN estabelecimentos_saude es ON es.id = i.id_estabelecimento
        GROUP BY es.id_municipio, es.municipio, i.tipo_equipamento
    """, conn)
    if inv.empty:
        return
    rows = []
    for tipo, g in inv.groupby("tipo_equipamento"):
        mediana = g["existente"].median()
        for _, r in g.iterrows():
            deficit = max(0, int(round(mediana - r["existente"])))
            if deficit <= 0:
                continue
            vulnerabilidade = 5 if r["existente"] == 0 else 3
            rows.append({
                "id": uid(),
                "id_municipio": r["id_municipio"],
                "municipio": r["municipio"],
                "tipo_equipamento": tipo,
                "quantidade_necessaria": deficit,
                "nivel_vulnerabilidade": vulnerabilidade,
                "populacao_atendida": 0,
                "fonte": "estimativa_mediana_disponibilidade_cnes",
            })
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_sql("demanda_regional", conn, if_exists="append", index=False)
    log(conn, "demanda_regional", len(out), "Estimativa inicial para testar score; substituir por demanda oficial quando disponível.")


def validar_fk(conn: sqlite3.Connection) -> None:
    checks = {
        "equipamentos_sem_id_estabelecimento": "SELECT COUNT(*) FROM equipamentos WHERE id_estabelecimento IS NULL",
        "inventario_sem_id_estabelecimento": "SELECT COUNT(*) FROM inventario_equipamentos_cnes WHERE id_estabelecimento IS NULL",
        "equipamentos_orfaos": """
            SELECT COUNT(*) FROM equipamentos e
            LEFT JOIN estabelecimentos_saude es ON es.id = e.id_estabelecimento
            WHERE es.id IS NULL
        """,
    }
    for nome, sql in checks.items():
        valor = conn.execute(sql).fetchone()[0]
        log(conn, f"validacao_{nome}", int(valor), "Esperado: 0")


def executar(recriar: bool = True, limite_expandir: int | None = None) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    if recriar:
        criar_schema(conn)

    estabelecimentos = montar_estabelecimentos()
    popular_municipios(conn, estabelecimentos)
    popular_estabelecimentos(conn, estabelecimentos)
    inventario = popular_inventario(conn)
    popular_hospitais_perfil(conn, estabelecimentos, inventario)
    popular_equipamentos_expandidos(conn, limite_expandir=limite_expandir)
    popular_demanda_inicial(conn)
    validar_fk(conn)

    conn.commit()
    resumo = pd.read_sql_query("SELECT etapa, linhas, observacao FROM etl_log ORDER BY id", conn)
    conn.close()
    print(f"✅ Banco criado em: {DB_PATH}")
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL final MONJICA com FK real para SQLite")
    parser.add_argument("--sem-recriar", action="store_true", help="não recria o schema")
    parser.add_argument("--limite-expandir", type=int, default=None, help="limita expansão individual por linha de inventário para testes")
    args = parser.parse_args()
    executar(recriar=not args.sem_recriar, limite_expandir=args.limite_expandir)
