import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
import uuid

fake = Faker("pt_BR")

# =========================
# CONEXÃO
# =========================
conn = sqlite3.connect("monjica.db")
cur = conn.cursor()

# =========================
# CREATE TABLES
# =========================

cur.executescript("""
DROP TABLE IF EXISTS equipamentos;
DROP TABLE IF EXISTS historico_tecnico;
DROP TABLE IF EXISTS localizacao;
DROP TABLE IF EXISTS demanda_regional;
DROP TABLE IF EXISTS movimentacao;
DROP TABLE IF EXISTS score_decisao;
DROP TABLE IF EXISTS uso_equipamento;

CREATE TABLE equipamentos (
    id TEXT PRIMARY KEY,
    tipo_equipamento TEXT,
    modelo TEXT,
    fabricante TEXT,
    data_aquisicao TEXT,
    vida_util_estimada INTEGER,
    estado_atual TEXT CHECK (estado_atual IN ('ativo','ocioso','inoperante')),
    status_triagem TEXT CHECK (status_triagem IN ('pendente','aprovado_reuso','recondicionar','descarte'))
);

CREATE TABLE historico_tecnico (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT,
    data_manutencao TEXT,
    tipo_manutencao TEXT,
    falha_detectada TEXT,
    tempo_parado INTEGER,
    custo_manutencao REAL
);

CREATE TABLE localizacao (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT,
    instituicao_origem TEXT,
    municipio TEXT,
    regiao TEXT,
    lat REAL,
    lon REAL
);

CREATE TABLE demanda_regional (
    id TEXT PRIMARY KEY,
    municipio TEXT,
    tipo_equipamento TEXT,
    quantidade_necessaria INTEGER,
    nivel_vulnerabilidade INTEGER,
    populacao_atendida INTEGER
);

CREATE TABLE movimentacao (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT,
    origem TEXT,
    destino TEXT,
    data_envio TEXT,
    data_recebimento TEXT,
    status_logistico TEXT,
    custo_transporte REAL
);

CREATE TABLE score_decisao (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT,
    score_reuso REAL,
    score_criticidade REAL,
    score_prioridade REAL,
    recomendacao TEXT,
    explicacao_modelo TEXT
);

CREATE TABLE uso_equipamento (
    id TEXT PRIMARY KEY,
    id_equipamento TEXT,
    data TEXT,
    quantidade_uso INTEGER,
    tipo_atendimento TEXT
);
""")

# =========================
# DADOS BASE
# =========================

TIPOS = ["Raio-X", "Ultrassom", "Tomógrafo", "Ventilador"]
ESTADOS = ["ativo", "ocioso", "inoperante"]
TRIAGEM = ["pendente", "aprovado_reuso", "recondicionar", "descarte"]
RECOMENDACOES = ["reuso", "recondicionar", "descarte", "redistribuir"]

MUNICIPIOS = [
    ("Rio de Janeiro", "Metropolitana"),
    ("Duque de Caxias", "Metropolitana"),
    ("Nova Iguaçu", "Metropolitana"),
    ("Campos dos Goytacazes", "Norte"),
    ("Volta Redonda", "Sul Fluminense"),
    ("Petrópolis", "Serrana")
]

# =========================
# 1. EQUIPAMENTOS
# =========================

equip_ids = []

for _ in range(100):
    eid = str(uuid.uuid4())
    equip_ids.append(eid)

    cur.execute("""
    INSERT INTO equipamentos VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        eid,
        random.choice(TIPOS),
        fake.word(),
        fake.company(),
        fake.date_between(start_date='-10y', end_date='today'),
        random.randint(60, 180),
        random.choice(ESTADOS),
        random.choice(TRIAGEM)
    ))

# =========================
# 2. HISTÓRICO TÉCNICO
# =========================

for eid in equip_ids:
    for _ in range(random.randint(1, 5)):
        cur.execute("""
        INSERT INTO historico_tecnico VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            eid,
            fake.date_between(start_date='-3y', end_date='today'),
            random.choice(["preventiva", "corretiva"]),
            fake.sentence(),
            random.randint(0, 30),
            round(random.uniform(100, 5000), 2)
        ))

# =========================
# 3. LOCALIZAÇÃO
# =========================

for eid in equip_ids:
    municipio, regiao = random.choice(MUNICIPIOS)

    cur.execute("""
    INSERT INTO localizacao VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        eid,
        fake.company(),
        municipio,
        regiao,
        round(random.uniform(-23, -21), 6),
        round(random.uniform(-45, -41), 6)
    ))

# =========================
# 4. DEMANDA REGIONAL
# =========================

for municipio, regiao in MUNICIPIOS:
    for tipo in TIPOS:
        cur.execute("""
        INSERT INTO demanda_regional VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            municipio,
            tipo,
            random.randint(5, 50),
            random.randint(1, 5),
            random.randint(50000, 1000000)
        ))

# =========================
# 5. SCORE (IA SIMULADA)
# =========================

for eid in equip_ids:
    score = random.uniform(0, 1)

    cur.execute("""
    INSERT INTO score_decisao VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        eid,
        round(random.uniform(0, 1), 2),
        round(random.uniform(0, 1), 2),
        round(score, 2),
        random.choice(RECOMENDACOES),
        "Decisão baseada em criticidade e demanda regional"
    ))

# =========================
# 6. MOVIMENTAÇÃO
# =========================

for eid in random.sample(equip_ids, 50):
    origem = random.choice(MUNICIPIOS)[0]
    destino = random.choice(MUNICIPIOS)[0]

    data_envio = datetime.now() - timedelta(days=random.randint(1, 30))

    cur.execute("""
    INSERT INTO movimentacao VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        eid,
        origem,
        destino,
        data_envio.date(),
        (data_envio + timedelta(days=random.randint(1,10))).date(),
        random.choice(["pendente", "em_transporte", "entregue"]),
        round(random.uniform(500, 5000), 2)
    ))

# =========================
# 7. USO (IMPACTO)
# =========================

for eid in equip_ids:
    for _ in range(random.randint(5, 20)):
        cur.execute("""
        INSERT INTO uso_equipamento VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            eid,
            fake.date_between(start_date='-1y', end_date='today'),
            random.randint(1, 20),
            random.choice(["exame", "emergência", "rotina"])
        ))

conn.commit()
conn.close()

print("✅ Banco SQLite populado com sucesso!")