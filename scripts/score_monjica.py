from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "banco" / "monjica.db"


def uid() -> str:
    return str(uuid.uuid4())


def normalizar(valor: Any, minimo: float, maximo: float) -> float:
    try:
        if valor is None:
            return 0.0
        valor = float(valor)
    except Exception:
        return 0.0
    if maximo == minimo:
        return 0.0
    return max(0.0, min(1.0, (valor - minimo) / (maximo - minimo)))


def calcular_idade_meses(data_aquisicao: Any) -> int:
    if not data_aquisicao:
        return 0
    try:
        data = datetime.strptime(str(data_aquisicao)[:10], "%Y-%m-%d")
    except Exception:
        return 0
    hoje = datetime.now()
    return (hoje.year - data.year) * 12 + (hoje.month - data.month)


def recomendacao(score_reuso: float, score_criticidade: float, score_prioridade: float, estado: str) -> str:
    if estado in {"descarte", "inoperante"} and score_reuso < 0.35:
        return "descarte"
    if estado in {"manutencao", "inoperante"} and score_reuso >= 0.35:
        return "recondicionar"
    if estado == "ocioso" and score_prioridade >= 0.55:
        return "redistribuir"
    if score_reuso >= 0.60:
        return "reuso"
    return "recondicionar"


def executar() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("DELETE FROM score_decisao")

    equipamentos = cur.execute("""
        SELECT
            e.id,
            e.id_estabelecimento,
            e.cnes_atual,
            e.tipo_equipamento,
            e.equipamento,
            e.estado_atual,
            e.data_aquisicao,
            e.vida_util_estimada,
            es.nome_fantasia,
            es.municipio,
            hp.equipamentos_ociosos_estimados,
            hp.equipamentos_total,
            hp.score_reaproveitamento
        FROM equipamentos e
        LEFT JOIN estabelecimentos_saude es ON es.id = e.id_estabelecimento
        LEFT JOIN hospitais_perfil hp ON hp.id_estabelecimento = e.id_estabelecimento
    """).fetchall()

    for eq in equipamentos:
        hist = cur.execute("""
            SELECT COUNT(*) AS qtd_falhas,
                   COALESCE(SUM(custo_manutencao), 0) AS custo_total,
                   COALESCE(SUM(tempo_parado), 0) AS tempo_parado_total
            FROM historico_tecnico
            WHERE id_equipamento = ?
        """, (eq["id"],)).fetchone()

        destino = cur.execute("""
            SELECT municipio, quantidade_necessaria, nivel_vulnerabilidade
            FROM demanda_regional
            WHERE tipo_equipamento = ?
              AND COALESCE(municipio, '') <> COALESCE(?, '')
            ORDER BY nivel_vulnerabilidade DESC, quantidade_necessaria DESC
            LIMIT 1
        """, (eq["tipo_equipamento"], eq["municipio"])).fetchone()

        vida_util = int(eq["vida_util_estimada"] or 120)
        idade_meses = calcular_idade_meses(eq["data_aquisicao"])
        estado = eq["estado_atual"] or "ativo"
        qtd_falhas = hist["qtd_falhas"] or 0
        custo_total = hist["custo_total"] or 0
        tempo_parado = hist["tempo_parado_total"] or 0
        demanda = destino["quantidade_necessaria"] if destino else 0
        vulnerabilidade = destino["nivel_vulnerabilidade"] if destino else 1
        municipio_destino = destino["municipio"] if destino else None

        idade_rel = normalizar(idade_meses, 0, vida_util)
        falhas_norm = normalizar(qtd_falhas, 0, 10)
        custo_norm = normalizar(custo_total, 0, 30000)
        parada_norm = normalizar(tempo_parado, 0, 180)
        demanda_norm = normalizar(demanda, 0, 50)
        vuln_norm = normalizar(vulnerabilidade, 1, 5)

        bonus_ocioso = 0.15 if estado == "ocioso" else 0.0
        penalidade_inoperante = 0.25 if estado in {"inoperante", "descarte"} else 0.0

        score_reuso = (
            0.30 * (1 - idade_rel)
            + 0.20 * (1 - falhas_norm)
            + 0.15 * (1 - custo_norm)
            + 0.15 * (1 - parada_norm)
            + bonus_ocioso
            - penalidade_inoperante
        )
        score_reuso = max(0, min(1, score_reuso))

        score_criticidade = (
            0.25 * idade_rel
            + 0.25 * falhas_norm
            + 0.20 * custo_norm
            + 0.15 * parada_norm
            + (0.15 if estado in {"ocioso", "manutencao", "inoperante"} else 0)
        )
        score_criticidade = max(0, min(1, score_criticidade))

        score_prioridade = (
            0.35 * score_reuso
            + 0.30 * demanda_norm
            + 0.25 * vuln_norm
            + 0.10 * (1 - score_criticidade)
        )
        score_prioridade = max(0, min(1, score_prioridade))

        rec = recomendacao(score_reuso, score_criticidade, score_prioridade, estado)
        explicacao = (
            f"Recomendação: {rec}. Equipamento '{eq['equipamento']}' do tipo '{eq['tipo_equipamento']}', "
            f"atualmente em {eq['nome_fantasia']} ({eq['municipio']}), estado='{estado}'. "
            f"O score considera idade estimada ({idade_meses} meses), falhas registradas ({qtd_falhas}), "
            f"custo técnico acumulado R$ {float(custo_total):.2f}, tempo parado {tempo_parado} dias, "
            f"demanda territorial por tipo ({demanda}) e vulnerabilidade ({vulnerabilidade}). "
            f"Destino territorial sugerido: {municipio_destino or 'não definido'}."
        )

        cur.execute("""
            INSERT INTO score_decisao (
                id, id_equipamento, id_origem_estabelecimento, tipo_equipamento,
                score_reuso, score_criticidade, score_prioridade,
                recomendacao, destino_municipio, explicacao_modelo, modelo_versao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid(), eq["id"], eq["id_estabelecimento"], eq["tipo_equipamento"],
            round(score_reuso, 2), round(score_criticidade, 2), round(score_prioridade, 2),
            rec, municipio_destino, explicacao, "monjica_v3_fk"
        ))

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM score_decisao").fetchone()[0]
    conn.close()
    print(f"✅ Scores MONJICA v3 FK calculados: {total}")


if __name__ == "__main__":
    executar()
