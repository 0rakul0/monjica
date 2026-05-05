PRAGMA foreign_keys = OFF;

DROP VIEW IF EXISTS vw_fluxo_redistribuicao;
DROP VIEW IF EXISTS vw_prioridade_equipamentos;
DROP VIEW IF EXISTS vw_hospitais_resumo;
DROP VIEW IF EXISTS vw_impacto_equipamentos;

DROP TABLE IF EXISTS score_decisao;
DROP TABLE IF EXISTS movimentacao;
DROP TABLE IF EXISTS uso_equipamento;
DROP TABLE IF EXISTS historico_tecnico;
DROP TABLE IF EXISTS equipamentos;
DROP TABLE IF EXISTS inventario_equipamentos_cnes;
DROP TABLE IF EXISTS demanda_regional;
DROP TABLE IF EXISTS hospitais_perfil;
DROP TABLE IF EXISTS estabelecimentos_saude;
DROP TABLE IF EXISTS municipios;
DROP TABLE IF EXISTS etl_log;

PRAGMA foreign_keys = ON;

CREATE TABLE municipios (
    id_municipio TEXT PRIMARY KEY,
    nome_municipio TEXT NOT NULL,
    nome_municipio_norm TEXT NOT NULL UNIQUE,
    regiao TEXT DEFAULT 'A classificar',
    lat_media REAL,
    lon_media REAL
);

CREATE TABLE estabelecimentos_saude (
    id TEXT PRIMARY KEY,
    cnes TEXT NOT NULL UNIQUE,
    co_unidade TEXT,
    nome_fantasia TEXT NOT NULL,
    razao_social TEXT,
    categoria_unidade TEXT,
    tipo_estabelecimento TEXT,
    criterio_selecao TEXT,
    endereco TEXT,
    bairro TEXT,
    cep TEXT,
    id_municipio TEXT,
    municipio TEXT,
    telefone TEXT,
    email TEXT,
    latitude REAL,
    longitude REAL,
    natureza_juridica TEXT,
    tipo_gestao TEXT,
    co_tipo_estabelecimento TEXT,
    co_atividade_principal TEXT,
    data_atualizacao TEXT,
    fonte TEXT NOT NULL,
    ativo INTEGER DEFAULT 1,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio)
);

CREATE TABLE hospitais_perfil (
    id TEXT PRIMARY KEY,
    id_estabelecimento TEXT NOT NULL UNIQUE,
    cnes TEXT NOT NULL UNIQUE,
    esfera TEXT DEFAULT 'A classificar',
    porte TEXT DEFAULT 'Não classificado',
    criterio_porte TEXT,
    regiao TEXT DEFAULT 'A classificar',
    leitos_cnes INTEGER DEFAULT 0,
    leitos_referencia INTEGER DEFAULT 0,
    telefone_referencia TEXT,
    email_referencia TEXT,
    endereco_referencia TEXT,
    lat_referencia REAL,
    lon_referencia REAL,
    equipamentos_total INTEGER DEFAULT 0,
    equipamentos_em_uso INTEGER DEFAULT 0,
    equipamentos_sus INTEGER DEFAULT 0,
    equipamentos_ociosos_estimados INTEGER DEFAULT 0,
    manutencao INTEGER DEFAULT 0,
    descarte INTEGER DEFAULT 0,
    potencial_reaproveitamento TEXT DEFAULT 'Inventário pendente',
    score_reaproveitamento REAL DEFAULT 0,
    FOREIGN KEY (id_estabelecimento) REFERENCES estabelecimentos_saude(id) ON DELETE CASCADE,
    FOREIGN KEY (cnes) REFERENCES estabelecimentos_saude(cnes) ON DELETE CASCADE
);

CREATE TABLE inventario_equipamentos_cnes (
    id TEXT PRIMARY KEY,
    id_estabelecimento TEXT NOT NULL,
    cnes TEXT NOT NULL,
    co_tipo_equipamento TEXT,
    tipo_equipamento TEXT NOT NULL,
    co_equipamento TEXT,
    equipamento TEXT NOT NULL,
    qt_existente INTEGER DEFAULT 0,
    qt_uso INTEGER DEFAULT 0,
    qt_sus INTEGER DEFAULT 0,
    qt_ocioso_estimado INTEGER DEFAULT 0,
    manutencao INTEGER DEFAULT 0,
    descarte INTEGER DEFAULT 0,
    para_instalacao INTEGER DEFAULT 0,
    fonte TEXT DEFAULT 'CNES',
    FOREIGN KEY (id_estabelecimento) REFERENCES estabelecimentos_saude(id) ON DELETE CASCADE,
    FOREIGN KEY (cnes) REFERENCES estabelecimentos_saude(cnes) ON DELETE CASCADE
);

CREATE TABLE equipamentos (
    id TEXT PRIMARY KEY,
    id_inventario TEXT,
    id_estabelecimento TEXT NOT NULL,
    cnes_atual TEXT NOT NULL,
    tipo_equipamento TEXT NOT NULL,
    equipamento TEXT NOT NULL,
    modelo TEXT,
    fabricante TEXT,
    numero_patrimonio TEXT,
    data_aquisicao TEXT,
    vida_util_estimada INTEGER DEFAULT 120,
    estado_atual TEXT CHECK (estado_atual IN ('ativo','ocioso','inoperante','manutencao','descarte')) DEFAULT 'ativo',
    status_triagem TEXT CHECK (status_triagem IN ('pendente','aprovado_reuso','recondicionar','descarte','redistribuir')) DEFAULT 'pendente',
    origem_dado TEXT DEFAULT 'CNES_expandido',
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_inventario) REFERENCES inventario_equipamentos_cnes(id) ON DELETE CASCADE,
    FOREIGN KEY (id_estabelecimento) REFERENCES estabelecimentos_saude(id),
    FOREIGN KEY (cnes_atual) REFERENCES estabelecimentos_saude(cnes)
);

CREATE TABLE historico_tecnico (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT NOT NULL,
    data_manutencao TEXT NOT NULL,
    tipo_manutencao TEXT,
    falha_detectada TEXT,
    tempo_parado INTEGER DEFAULT 0,
    custo_manutencao REAL DEFAULT 0,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id) ON DELETE CASCADE
);

CREATE TABLE demanda_regional (
    id TEXT PRIMARY KEY,
    id_municipio TEXT,
    municipio TEXT NOT NULL,
    tipo_equipamento TEXT NOT NULL,
    quantidade_necessaria INTEGER DEFAULT 0,
    nivel_vulnerabilidade INTEGER CHECK (nivel_vulnerabilidade BETWEEN 1 AND 5) DEFAULT 1,
    populacao_atendida INTEGER DEFAULT 0,
    fonte TEXT DEFAULT 'estimativa_inicial',
    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio)
);

CREATE TABLE movimentacao (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT NOT NULL,
    id_origem_estabelecimento TEXT,
    id_destino_estabelecimento TEXT,
    municipio_destino TEXT,
    data_envio TEXT,
    data_recebimento TEXT,
    status_logistico TEXT CHECK (status_logistico IN ('pendente','em_transporte','entregue','cancelado')) DEFAULT 'pendente',
    custo_transporte REAL DEFAULT 0,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id),
    FOREIGN KEY (id_origem_estabelecimento) REFERENCES estabelecimentos_saude(id),
    FOREIGN KEY (id_destino_estabelecimento) REFERENCES estabelecimentos_saude(id)
);

CREATE TABLE score_decisao (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT NOT NULL,
    id_origem_estabelecimento TEXT,
    tipo_equipamento TEXT,
    score_reuso REAL,
    score_criticidade REAL,
    score_prioridade REAL,
    recomendacao TEXT CHECK (recomendacao IN ('reuso','recondicionar','descarte','redistribuir')),
    destino_municipio TEXT,
    explicacao_modelo TEXT,
    modelo_versao TEXT DEFAULT 'monjica_v3_fk',
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id) ON DELETE CASCADE,
    FOREIGN KEY (id_origem_estabelecimento) REFERENCES estabelecimentos_saude(id)
);

CREATE TABLE uso_equipamento (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT NOT NULL,
    id_estabelecimento TEXT,
    data TEXT,
    quantidade_uso INTEGER DEFAULT 0,
    tipo_atendimento TEXT,
    fonte TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_equipamento) REFERENCES equipamentos(id),
    FOREIGN KEY (id_estabelecimento) REFERENCES estabelecimentos_saude(id)
);

CREATE TABLE etl_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    etapa TEXT,
    linhas INTEGER,
    observacao TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_estabelecimentos_cnes ON estabelecimentos_saude(cnes);
CREATE INDEX idx_estabelecimentos_municipio ON estabelecimentos_saude(municipio);
CREATE INDEX idx_estabelecimentos_categoria ON estabelecimentos_saude(categoria_unidade);
CREATE INDEX idx_hospitais_estabelecimento ON hospitais_perfil(id_estabelecimento);
CREATE INDEX idx_inventario_estabelecimento ON inventario_equipamentos_cnes(id_estabelecimento);
CREATE INDEX idx_inventario_cnes ON inventario_equipamentos_cnes(cnes);
CREATE INDEX idx_equipamentos_estabelecimento ON equipamentos(id_estabelecimento);
CREATE INDEX idx_equipamentos_cnes ON equipamentos(cnes_atual);
CREATE INDEX idx_equipamentos_tipo ON equipamentos(tipo_equipamento);
CREATE INDEX idx_score_origem ON score_decisao(id_origem_estabelecimento);
CREATE INDEX idx_score_prioridade ON score_decisao(score_prioridade);
CREATE INDEX idx_demanda_tipo_municipio ON demanda_regional(tipo_equipamento, municipio);

CREATE VIEW vw_hospitais_resumo AS
SELECT
    es.id AS id_estabelecimento,
    es.cnes,
    es.nome_fantasia,
    es.razao_social,
    es.municipio,
    COALESCE(h.regiao, m.regiao) AS regiao,
    h.esfera,
    h.porte,
    es.endereco,
    es.telefone,
    es.email,
    es.latitude,
    es.longitude,
    h.leitos_cnes,
    h.leitos_referencia,
    h.equipamentos_total,
    h.equipamentos_em_uso,
    h.equipamentos_ociosos_estimados,
    h.potencial_reaproveitamento,
    h.score_reaproveitamento
FROM hospitais_perfil h
JOIN estabelecimentos_saude es ON es.id = h.id_estabelecimento
LEFT JOIN municipios m ON m.id_municipio = es.id_municipio;

CREATE VIEW vw_prioridade_equipamentos AS
SELECT
    eq.id,
    eq.id_estabelecimento,
    eq.cnes_atual,
    es.nome_fantasia AS origem_estabelecimento,
    es.municipio AS origem_municipio,
    es.latitude AS lat_origem,
    es.longitude AS lon_origem,
    eq.tipo_equipamento,
    eq.equipamento,
    eq.estado_atual,
    s.score_reuso,
    s.score_criticidade,
    s.score_prioridade,
    s.recomendacao,
    s.destino_municipio,
    s.explicacao_modelo
FROM equipamentos eq
LEFT JOIN estabelecimentos_saude es ON es.id = eq.id_estabelecimento
LEFT JOIN score_decisao s ON s.id_equipamento = eq.id;

CREATE VIEW vw_fluxo_redistribuicao AS
SELECT
    s.id_equipamento,
    s.tipo_equipamento,
    s.score_prioridade,
    s.recomendacao,
    o.id AS id_origem_estabelecimento,
    o.cnes AS cnes_origem,
    o.nome_fantasia AS origem,
    o.municipio AS municipio_origem,
    o.latitude AS lat_origem,
    o.longitude AS lon_origem,
    s.destino_municipio AS destino,
    m.lat_media AS lat_destino,
    m.lon_media AS lon_destino,
    d.nivel_vulnerabilidade,
    d.quantidade_necessaria
FROM score_decisao s
LEFT JOIN estabelecimentos_saude o ON o.id = s.id_origem_estabelecimento
LEFT JOIN municipios m ON m.nome_municipio_norm = s.destino_municipio
LEFT JOIN demanda_regional d
    ON d.tipo_equipamento = s.tipo_equipamento
   AND d.municipio = s.destino_municipio;

CREATE VIEW vw_impacto_equipamentos AS
SELECT
    id_equipamento,
    id_estabelecimento,
    SUM(quantidade_uso) AS total_atendimentos
FROM uso_equipamento
GROUP BY id_equipamento, id_estabelecimento;
