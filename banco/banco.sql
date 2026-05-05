-- =========================
-- EXTENSÕES (IMPORTANTE)
-- =========================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================
-- TABELA: equipamentos
-- =========================
CREATE TABLE equipamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    tipo_equipamento VARCHAR(100) NOT NULL,
    modelo VARCHAR(100),
    fabricante VARCHAR(100),

    data_aquisicao DATE,
    vida_util_estimada INTEGER, -- em meses

    estado_atual VARCHAR(20) CHECK (
        estado_atual IN ('ativo', 'ocioso', 'inoperante')
    ) NOT NULL,

    status_triagem VARCHAR(30) CHECK (
        status_triagem IN ('pendente', 'aprovado_reuso', 'recondicionar', 'descarte')
    ) DEFAULT 'pendente',

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: historico_tecnico
-- =========================
CREATE TABLE historico_tecnico (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    id_equipamento UUID REFERENCES equipamentos(id) ON DELETE CASCADE,

    data_manutencao DATE NOT NULL,
    tipo_manutencao VARCHAR(100),

    falha_detectada TEXT,
    tempo_parado INTEGER, -- em dias
    custo_manutencao NUMERIC(12,2),

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: localizacao
-- =========================
CREATE TABLE localizacao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    id_equipamento UUID REFERENCES equipamentos(id) ON DELETE CASCADE,

    instituicao_origem VARCHAR(150),
    municipio VARCHAR(100),
    regiao VARCHAR(100),

    lat NUMERIC(9,6),
    lon NUMERIC(9,6),

    ativo BOOLEAN DEFAULT TRUE,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: demanda_regional
-- =========================
CREATE TABLE demanda_regional (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    municipio VARCHAR(100),
    tipo_equipamento VARCHAR(100),

    quantidade_necessaria INTEGER,
    nivel_vulnerabilidade INTEGER CHECK (nivel_vulnerabilidade BETWEEN 1 AND 5),

    populacao_atendida INTEGER,

    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: movimentacao
-- =========================
CREATE TABLE movimentacao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    id_equipamento UUID REFERENCES equipamentos(id),

    origem VARCHAR(150),
    destino VARCHAR(150),

    data_envio DATE,
    data_recebimento DATE,

    status_logistico VARCHAR(30) CHECK (
        status_logistico IN ('pendente', 'em_transporte', 'entregue', 'cancelado')
    ),

    custo_transporte NUMERIC(12,2),

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: score_decisao (CORE IA)
-- =========================
CREATE TABLE score_decisao (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    id_equipamento UUID REFERENCES equipamentos(id) ON DELETE CASCADE,

    score_reuso NUMERIC(5,2),
    score_criticidade NUMERIC(5,2),
    score_prioridade NUMERIC(5,2),

    recomendacao VARCHAR(30) CHECK (
        recomendacao IN ('reuso', 'recondicionar', 'descarte', 'redistribuir')
    ),

    explicacao_modelo TEXT,

    modelo_versao VARCHAR(50),

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- TABELA: uso_equipamento (IMPACTO REAL)
-- =========================
CREATE TABLE uso_equipamento (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    id_equipamento UUID REFERENCES equipamentos(id),

    data DATE,
    quantidade_uso INTEGER,
    tipo_atendimento VARCHAR(100),

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- ÍNDICES (PERFORMANCE)
-- =========================

CREATE INDEX idx_equipamento_tipo ON equipamentos(tipo_equipamento);
CREATE INDEX idx_demanda_municipio ON demanda_regional(municipio);
CREATE INDEX idx_movimentacao_status ON movimentacao(status_logistico);
CREATE INDEX idx_score_prioridade ON score_decisao(score_prioridade);

-- =========================
-- VIEW: prioridade operacional
-- =========================

CREATE VIEW view_prioridade_equipamentos AS
SELECT
    e.id,
    e.tipo_equipamento,
    e.estado_atual,
    s.score_prioridade,
    s.recomendacao,
    l.municipio AS origem,
    d.municipio AS destino_sugerido
FROM equipamentos e
LEFT JOIN score_decisao s ON e.id = s.id_equipamento
LEFT JOIN localizacao l ON e.id = l.id_equipamento
LEFT JOIN demanda_regional d ON e.tipo_equipamento = d.tipo_equipamento
ORDER BY s.score_prioridade DESC;

-- =========================
-- VIEW: impacto
-- =========================

CREATE VIEW view_impacto_equipamentos AS
SELECT
    id_equipamento,
    SUM(quantidade_uso) AS total_atendimentos
FROM uso_equipamento
GROUP BY id_equipamento;