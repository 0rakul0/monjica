from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_ENTRADA = BASE_DIR / "data" / "entrada" / "hospitais_inventario.csv"
INVENTARIO_EQUIPAMENTOS = BASE_DIR / "data" / "entrada" / "inventario_equipamentos_municipais_rj_cnes_202603.csv"
REFERENCIA_LOCAL_HOSPITAIS = BASE_DIR / "data" / "entrada" / "referencia_local_hospitais.csv"
UNIDADES_SAUDE = BASE_DIR / "data" / "entrada" / "unidades_saude_municipais_rj_cnes_202603.csv"
REFERENCIA_XLSX = BASE_DIR / "data" / "entrada" / "endereço_caps.xlsx"
MUNICIPIOS_SHP = BASE_DIR / "data" / "entrada" / "RJ_Municipios_2024.shp"
