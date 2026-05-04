SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS regioes (
    id_regiao INTEGER PRIMARY KEY NOT NULL,
    nome_regiao TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS municipios (
    id_municipio INTEGER PRIMARY KEY,
    nome_municipio TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS caps (
    id_caps INTEGER PRIMARY KEY NOT NULL,
    nome_caps TEXT,
    tipo_caps TEXT,
    end_caps TEXT,
    lat REAL,
    log REAL
);

CREATE TABLE IF NOT EXISTS regiao_municipio (
    id_municipio INTEGER PRIMARY KEY,
    id_regiao INTEGER NOT NULL,
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio),
    FOREIGN KEY (id_regiao) REFERENCES regioes(id_regiao)
);

CREATE TABLE IF NOT EXISTS caps_municipio (
    id_municipio INTEGER NOT NULL,
    id_caps INTEGER NOT NULL,
    PRIMARY KEY (id_municipio, id_caps),
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio),
    FOREIGN KEY (id_caps) REFERENCES caps(id_caps)
);

CREATE TABLE IF NOT EXISTS financiamento (
    id_financiamento INTEGER PRIMARY KEY AUTOINCREMENT,
    financiamento TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS leitos (
    id_municipio INTEGER NOT NULL,
    id_hospital INTEGER NOT NULL,
    nome_hospital TEXT,
    end_hosp TEXT,
    qte_leitos INTEGER,
    lat REAL,
    log REAL,
    id_financiamento INTEGER,
    PRIMARY KEY (id_hospital),
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio),
    FOREIGN KEY (id_financiamento) REFERENCES financiamento(id_financiamento)
);

CREATE TABLE IF NOT EXISTS srts (
    id_caps INTEGER PRIMARY KEY,
    rt INTEGER,
    uai INTEGER,
    uaa INTEGER,
    FOREIGN KEY (id_caps) REFERENCES caps(id_caps)
);

CREATE TABLE IF NOT EXISTS municipios_geo (
    id_municipio INTEGER PRIMARY KEY,
    id_ibge TEXT,
    nome_municipio TEXT,
    geometry_json TEXT,
    FOREIGN KEY (id_municipio) REFERENCES municipios(id_municipio)
);
"""
