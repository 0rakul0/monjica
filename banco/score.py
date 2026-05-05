import sqlite3
from datetime import datetime
import uuid

DB_PATH = "monjica.db"


def normalizar(valor, minimo, maximo):
    if valor is None:
        return 0
    if maximo == minimo:
        return 0
    return max(0, min(1, (valor - minimo) / (maximo - minimo)))


def calcular_idade_meses(data_aquisicao):
    if not data_aquisicao:
        return 0

    data = datetime.strptime(str(data_aquisicao), "%Y-%m-%d")
    hoje = datetime.now()

    return (hoje.year - data.year) * 12 + (hoje.month - data.month)


def definir_recomendacao(score_reuso, score_criticidade, score_prioridade, estado_atual):
    if estado_atual == "inoperante" and score_reuso < 0.35:
        return "descarte"

    if estado_atual == "inoperante" and score_reuso >= 0.35:
        return "recondicionar"

    if score_prioridade >= 0.70:
        return "redistribuir"

    if score_reuso >= 0.60:
        return "reuso"

    return "recondicionar"


def gerar_explicacao(
    idade_meses,
    vida_util,
    qtd_falhas,
    custo_total,
    tempo_parado_total,
    demanda,
    vulnerabilidade,
    destino,
    recomendacao
):
    return (
        f"Recomendação: {recomendacao}. "
        f"Equipamento com {idade_meses} meses de uso frente a uma vida útil estimada de {vida_util} meses. "
        f"Histórico técnico registra {qtd_falhas} manutenção(ões), "
        f"custo acumulado de R$ {custo_total:.2f} e {tempo_parado_total} dias parado. "
        f"A região de destino sugerida é {destino}, com demanda de {demanda} unidade(s) "
        f"e vulnerabilidade territorial nível {vulnerabilidade}. "
        f"A decisão considera reuso, criticidade técnica, demanda regional e impacto social."
    )


def executar_monjica_v1():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Limpa scores antigos
    cur.execute("DELETE FROM score_decisao")

    equipamentos = cur.execute("""
        SELECT
            e.id,
            e.tipo_equipamento,
            e.data_aquisicao,
            e.vida_util_estimada,
            e.estado_atual,
            l.municipio AS municipio_origem
        FROM equipamentos e
        LEFT JOIN localizacao l
            ON e.id = l.id_equipamento
    """).fetchall()

    for eq in equipamentos:
        id_equipamento = eq["id"]
        tipo = eq["tipo_equipamento"]
        estado_atual = eq["estado_atual"]
        vida_util = eq["vida_util_estimada"] or 120

        idade_meses = calcular_idade_meses(eq["data_aquisicao"])

        historico = cur.execute("""
            SELECT
                COUNT(*) AS qtd_falhas,
                COALESCE(SUM(custo_manutencao), 0) AS custo_total,
                COALESCE(SUM(tempo_parado), 0) AS tempo_parado_total
            FROM historico_tecnico
            WHERE id_equipamento = ?
        """, (id_equipamento,)).fetchone()

        qtd_falhas = historico["qtd_falhas"]
        custo_total = historico["custo_total"]
        tempo_parado_total = historico["tempo_parado_total"]

        destino = cur.execute("""
            SELECT
                municipio,
                quantidade_necessaria,
                nivel_vulnerabilidade
            FROM demanda_regional
            WHERE tipo_equipamento = ?
            ORDER BY
                nivel_vulnerabilidade DESC,
                quantidade_necessaria DESC
            LIMIT 1
        """, (tipo,)).fetchone()

        if destino:
            municipio_destino = destino["municipio"]
            demanda = destino["quantidade_necessaria"] or 0
            vulnerabilidade = destino["nivel_vulnerabilidade"] or 1
        else:
            municipio_destino = "não definido"
            demanda = 0
            vulnerabilidade = 1

        # =========================
        # SCORES NORMALIZADOS
        # =========================

        idade_relativa = normalizar(idade_meses, 0, vida_util)
        falhas_norm = normalizar(qtd_falhas, 0, 10)
        custo_norm = normalizar(custo_total, 0, 30000)
        parada_norm = normalizar(tempo_parado_total, 0, 180)

        demanda_norm = normalizar(demanda, 0, 50)
        vulnerabilidade_norm = normalizar(vulnerabilidade, 1, 5)

        # =========================
        # SCORE DE REUSO
        # Quanto maior, mais viável reaproveitar.
        # =========================

        score_reuso = (
            0.35 * (1 - idade_relativa) +
            0.25 * (1 - falhas_norm) +
            0.20 * (1 - custo_norm) +
            0.20 * (1 - parada_norm)
        )

        # =========================
        # SCORE DE CRITICIDADE
        # Quanto maior, mais urgente agir.
        # =========================

        score_criticidade = (
            0.30 * idade_relativa +
            0.25 * falhas_norm +
            0.25 * custo_norm +
            0.20 * parada_norm
        )

        # =========================
        # SCORE DE PRIORIDADE
        # Quanto maior, maior prioridade de redistribuição.
        # =========================

        score_prioridade = (
            0.35 * score_reuso +
            0.30 * demanda_norm +
            0.25 * vulnerabilidade_norm +
            0.10 * (1 - score_criticidade)
        )

        score_reuso = round(score_reuso, 2)
        score_criticidade = round(score_criticidade, 2)
        score_prioridade = round(score_prioridade, 2)

        recomendacao = definir_recomendacao(
            score_reuso,
            score_criticidade,
            score_prioridade,
            estado_atual
        )

        explicacao = gerar_explicacao(
            idade_meses,
            vida_util,
            qtd_falhas,
            custo_total,
            tempo_parado_total,
            demanda,
            vulnerabilidade,
            municipio_destino,
            recomendacao
        )

        cur.execute("""
            INSERT INTO score_decisao (
                id,
                id_equipamento,
                score_reuso,
                score_criticidade,
                score_prioridade,
                recomendacao,
                explicacao_modelo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            id_equipamento,
            score_reuso,
            score_criticidade,
            score_prioridade,
            recomendacao,
            explicacao
        ))

    conn.commit()
    conn.close()

    print("✅ MONJICA v1 executado com sucesso!")
    print("✅ Scores recalculados com base em idade, falhas, custo, demanda e vulnerabilidade.")


if __name__ == "__main__":
    executar_monjica_v1()