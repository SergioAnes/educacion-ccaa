"""Utilidades compartidas por los scripts extraer_*.py: manifest, territorios, PC-Axis y JSON-stat de Eurostat."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / "datos-originales"
DATOS = RAIZ / "src" / "data"

TERRITORIOS = json.loads((DATOS / "territorios.json").read_text(encoding="utf-8"))
POR_ALIAS = {a: t for t in TERRITORIOS for a in t["alias"]}
POR_NUTS2 = {t["nuts2"]: t for t in TERRITORIOS}


def ultimo_original(fuente: str, nombre: str) -> dict:
    """Entrada del manifest más reciente de ese fichero, comprobando que el fichero local no ha cambiado."""
    manifest = json.loads((ORIGINALES / "manifest.json").read_text(encoding="utf-8"))
    cands = [m for m in manifest if m["fuente"] == fuente and Path(m["fichero"]).name == nombre]
    if not cands:
        raise SystemExit(f"No hay {fuente}/{nombre} en el manifest: ejecuta antes python scripts/descargar.py {fuente}")
    m = max(cands, key=lambda m: m["fecha_captura"])
    ruta = ORIGINALES / m["fichero"]
    if hashlib.sha256(ruta.read_bytes()).hexdigest() != m["sha256"]:
        raise SystemExit(f"{ruta}: el sha256 no coincide con el manifest (los originales no se editan)")
    return {**m, "ruta": ruta}


def territorio(etiqueta: str) -> dict:
    """Territorio a partir del nombre que usa la fuente, sin las llamadas a notas: «Cantabria (3)» -> Cantabria."""
    limpio = re.sub(r"\s*\(\d+\)\s*$", "", etiqueta).strip()
    if limpio not in POR_ALIAS:
        raise SystemExit(f"Territorio desconocido en la fuente: {etiqueta!r} (añadir su alias a src/data/territorios.json)")
    return POR_ALIAS[limpio]


# ---------- PC-Axis (.px) ----------

def leer_px(ruta: Path) -> dict:
    """Lee un fichero PC-Axis: claves (TITLE, NOTE, STUB, HEADING, VALUES(...), DATA...) y la matriz de datos."""
    texto = ruta.read_bytes().decode("iso-8859-15")
    claves: dict[str, object] = {}
    # Cada sentencia termina en «;» fuera de comillas
    sentencias, actual, dentro = [], [], False
    for ch in texto:
        if ch == '"':
            dentro = not dentro
        if ch == ";" and not dentro:
            sentencias.append("".join(actual).strip())
            actual = []
        else:
            actual.append(ch)
    for s in sentencias:
        if "=" not in s:
            continue
        clave, valor = s.split("=", 1)
        clave = clave.strip()
        if clave == "DATA":
            claves[clave] = [None if x.strip('"') in ("..", ".", "...", "-") else float(x) for x in valor.split()]
            continue
        partes = re.findall(r'"([^"]*)"', valor)
        if not partes:
            claves[clave] = valor.strip()
        elif clave.startswith(("VALUES", "STUB", "HEADING")):
            claves[clave] = partes  # listas de categorías, separadas por comas
        else:
            claves[clave] = "".join(partes)  # los textos largos vienen cortados en trozos entre comillas
    return claves


def celdas_px(px: dict) -> dict[tuple, float | None]:
    """Valor de cada combinación de categorías: {(stub1, ..., heading1, ...): valor}. Orden PC-Axis: filas = STUB,
    columnas = HEADING, la última variable es la que cambia más rápido."""
    vars_ = list(px["STUB"]) + list(px["HEADING"])
    cats = [px[f'VALUES("{v}")'] for v in vars_]
    datos = px["DATA"]
    combos = list(itertools.product(*cats))
    if len(combos) != len(datos):
        raise SystemExit(f"PC-Axis: {len(datos)} datos para {len(combos)} combinaciones")
    return dict(zip(combos, datos))


# ---------- JSON-stat de Eurostat ----------

def leer_eurostat(ruta: Path) -> tuple[list[str], dict[tuple, tuple[float | None, str | None]], dict]:
    """Devuelve (dimensiones, {combinación: (valor, marca)}, json completo). Marcas: b ruptura, d definición
    distinta, u baja fiabilidad, p provisional, e estimado."""
    d = json.loads(ruta.read_text(encoding="utf-8"))
    dims = d["id"]
    cats = [[c for c, _ in sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1])] for k in dims]
    valores, marcas = d.get("value", {}), d.get("status", {})
    out = {}
    for pos, combo in enumerate(itertools.product(*cats)):
        k = str(pos)
        if k in valores or k in marcas:
            out[combo] = (valores.get(k), marcas.get(k))
    return dims, out, d


def escribir_json(nombre: str, contenido) -> Path:
    ruta = DATOS / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ruta
