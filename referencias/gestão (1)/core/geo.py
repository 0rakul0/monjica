import json

import numpy as np
import pandas as pd
from shapely.geometry import shape


def corrigir_coord(valor):
    if pd.isna(valor) or valor is None:
        return np.nan

    if isinstance(valor, (int, float)):
        v = float(valor)
        if -180 <= v <= 180:
            return v

    txt = str(valor).strip()
    if txt == "":
        return np.nan

    txt = txt.replace(",", ".")

    try:
        v = float(txt)
        if -180 <= v <= 180:
            return v
    except Exception:
        pass

    txt = "".join(ch for ch in txt if ch.isdigit() or ch in "-.")
    if txt in {"", ".", "-", "-."}:
        return np.nan

    negativo = txt.startswith("-")
    txt = txt.replace("-", "").replace(".", "")
    if len(txt) < 3:
        return np.nan

    txt = txt[:2] + "." + txt[2:]
    if negativo:
        txt = "-" + txt

    try:
        return float(txt)
    except Exception:
        return np.nan


def geometry_from_json(geometry_json):
    if pd.isna(geometry_json) or geometry_json is None:
        return None
    return shape(json.loads(geometry_json))
