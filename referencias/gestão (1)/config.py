from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "banco" / "caps.sqlite"
PACIENTES_XLSX = BASE_DIR / "dados" / "brutos" / "output_com_endereco_caps_fuzzy.xlsx"
MUNICIPIOS_SHP = BASE_DIR / "dados" / "territoriais" / "RJ_Municipios_2024.shp"
PLANILHA_REDE_PATH = BASE_DIR / "dados" / "brutos" / "endereço_caps.xlsx"

PORT = 8052
APP_TITLE = "Painel CAPS"
