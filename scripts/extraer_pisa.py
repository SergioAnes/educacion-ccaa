"""PISA 2025 por comunidad autónoma: tablas del informe español del INEE (Ministerio de Educación).

Uso:  python scripts/descargar.py pisa && python scripts/extraer_pisa.py

Fuente: datos-originales/pisa/<fecha>/tablas-informe-pisa-2025.rar (Excel por capítulo). Hace falta UnRAR (WinRAR) para
abrirlo; el contenido se extrae a una carpeta temporal, no a datos-originales.

Indicadores (salida en src/data/observaciones/):
  - pisa_puntuacion: puntuación media en ciencias, lectura y matemáticas con su error típico (ET).
      2025: las 17 comunidades, Ceuta, Melilla, España, media OCDE y total UE (Figuras 2.1, 2.14 y 2.18).
      Ediciones anteriores: España y media OCDE-35 (2.9, 2.17, 2.21); comunidades, solo ciencias 2015 (2.11) y
      matemáticas 2022 (2.22). Las diferencias entre ediciones, con su ET oficial, van aparte («cambios»).
  - pisa_bajo / pisa_alto: % del alumnado por debajo del nivel 2 / en los niveles 5 y 6 (suma de los niveles publicados en
    2.4, 2.15 y 2.19; la fuente no da el error de la suma).
Cataluña: el INEE dice que sus datos no deben compararse (23,2 % de alumnado excluido): se marca «no comparable».
Murcia: comparable con cautela (12,7 % excluido): se marca con su aviso. Los textos salen de las propias tablas.

Comprobaciones: España y las comunidades valen lo mismo en las tablas de 2025 y en las de evolución; los niveles de
cada territorio suman 100 (±0,6 por redondeo); la diferencia publicada = 2025 − edición anterior (±0,05).
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import openpyxl

from comun import POR_ALIAS, TERRITORIOS, escribir_json, ultimo_original

NOMBRE = {t["ine"]: t["nombre"] for t in TERRITORIOS}

UNRAR = Path(r"C:\Program Files\WinRAR\UnRAR.exe")
URL_INEE = "https://www.educacionfpydeportes.gob.es/inee/evaluaciones-internacionales/pisa/pisa-2025.html"
COMPETENCIAS = {"ciencias": ("Figura 2.1", "Figura 2.9", "Figura 2.4"), "lectura": ("Figura 2.14", "Figura 2.17", "Figura 2.15"),
                "matematicas": ("Figura 2.18", "Figura 2.21", "Figura 2.19")}
REFERENCIAS = {"Promedio OCDE": "OCDE", "Total UE": "UE", "Promedio OCDE-35": "OCDE35", "Promedio OCDE - 35": "OCDE35"}


def territorio(etiqueta: str) -> tuple[str | None, str]:
    """(código, llamada) de una fila: «Cataluña (**)» -> ("09", "**"); países -> (None, "")."""
    et = str(etiqueta).strip()
    llamada = (re.search(r"\((\*+)\)\s*$", et) or [None, ""])[1]
    limpio = re.sub(r"\s*\(\*+\)\s*$", "", et).strip()
    if limpio in REFERENCIAS:
        return REFERENCIAS[limpio], llamada
    t = POR_ALIAS.get(limpio)
    return (t["ine"] if t else None), llamada


def filas_hoja(ws) -> list[list]:
    return [list(r) for r in ws.iter_rows(values_only=True)]


def tabla_simple(ws) -> dict[str, tuple[float, float, str]]:
    """Hojas «Jurisdicción | valor | ET»: {código: (valor, ET, llamada)}."""
    out = {}
    for r in filas_hoja(ws):
        if not r or r[0] is None:
            continue
        cod, llamada = territorio(r[0])
        nums = [x for x in r[1:] if isinstance(x, (int, float))]
        if cod and len(nums) >= 2:
            out[cod] = (nums[0], nums[1], llamada)
    return out


def notas_hoja(ws) -> dict[str, str]:
    """Notas «(*) …» y «(**) …» al pie de la hoja."""
    out = {}
    for r in filas_hoja(ws):
        for x in r:
            m = re.match(r"\((\*+)\)\s*(.+)", str(x or "").strip(), re.S)
            if m:
                out[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
    return out


def evolucion(ws) -> dict[str, dict[str, tuple[float, float]]]:
    """Hojas de evolución (cabecera de años, luego valor/ET por año). Se lee por columnas: hay celdas vacías
    (España no tiene lectura en 2018)."""
    filas = filas_hoja(ws)
    i = next(k for k, r in enumerate(filas) if r and r[0] == "Jurisdicción")
    anios = {c: str(v) for c, v in enumerate(filas[i]) if v and re.fullmatch(r"\d{4}", str(v))}
    out = {}
    for r in filas[i + 2:]:
        cod, _ = territorio(r[0]) if r and r[0] else (None, "")
        if not cod:
            continue
        out[cod] = {a: (r[c], r[c + 1]) for c, a in anios.items() if isinstance(r[c], (int, float))}
    return out


def cambios(ws, comp: str, desde: str, errores: list) -> tuple[list[dict], dict[str, tuple[float, float]]]:
    """Hojas de diferencias entre ediciones: media y ET de cada edición, diferencia y su ET."""
    out, anteriores = [], {}
    for r in filas_hoja(ws):
        if not r or r[0] is None:
            continue
        cod, _ = territorio(r[0])
        nums = [x for x in r[1:] if isinstance(x, (int, float))]
        if not cod or len(nums) < 6:
            continue
        a, ea, b, eb, d, ed = nums[:6]
        anteriores[cod] = (a, ea)
        out.append({"territorio": cod, "competencia": comp, "desde": desde, "hasta": "2025", "diferencia": round(d, 2), "error_estandar": round(ed, 2), "valor_2025": b, "_calc": b - a})
    # Diferencia publicada ≠ resta de las medias. Si coincide con la de otra fila, la tabla las trae intercambiadas
    # (en 2.11, Castilla y León y Castilla-La Mancha): se usa la resta de las medias y se quita el ET, que no sabemos
    # de quién es. Cualquier otro descuadre para el script.
    for c in out:
        if abs(c["_calc"] - c["diferencia"]) <= 0.05:
            continue
        pareja = next((o for o in out if o is not c and abs(o["_calc"] - c["diferencia"]) <= 0.05), None)
        if not pareja:
            errores.append(f"{ws.title} {c['territorio']}: diferencia publicada {c['diferencia']} y calculada {c['_calc']:.2f}")
            continue
        c["nota"] = (f"La tabla del INEE ({ws.title}) trae intercambiadas las diferencias de esta comunidad y de "
                     f"{NOMBRE.get(pareja['territorio'], pareja['territorio'])}. Mostramos la resta de las dos medias publicadas, que sí cuadran, sin su error típico "
                     "(no sabemos cuál es el suyo).")
        c["diferencia"], c["error_estandar"] = round(c["_calc"], 2), None
    for c in out:
        del c["_calc"]
    return out, anteriores


def fila(ind, terr, periodo, valor, unidad, et, fecha, comp, estado="definitivo"):
    return {"indicador_id": ind, "territorio": terr, "periodo": periodo, "titularidad": "total", "sexo": "total", "etapa": "total",
            "competencia": comp, "valor": round(valor, 4 if unidad == "indice" else 2), "unidad": unidad,
            "error_estandar": None if et is None else round(et, 4 if unidad == "indice" else 2),
            "estado": estado, "fuente_id": "inee_pisa", "url_fuente": URL_INEE, "fecha_captura": fecha}


def main() -> None:
    m = ultimo_original("pisa", "tablas-informe-pisa-2025.rar")
    if not UNRAR.exists():
        sys.exit(f"No encuentro {UNRAR}: hace falta para abrir el .rar del INEE")
    errores: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([str(UNRAR), "x", "-y", "-inul", str(m["ruta"]), tmp + "\\"], check=True)
        wb = openpyxl.load_workbook(Path(tmp) / "Tablas_cap_2.xlsx", read_only=True, data_only=True)
        punt, bajo, alto, todos_cambios = [], [], [], []
        no_comparable, cautela = {}, {}
        for comp, (h25, hevo, hniv) in COMPETENCIAS.items():
            d25 = tabla_simple(wb[h25])
            notas = notas_hoja(wb[h25])
            for cod, (v, et, llamada) in d25.items():
                punt.append(fila("pisa_puntuacion", cod, "2025", v, "puntos", et, m["fecha_captura"], comp))
                if llamada == "**":
                    no_comparable[cod] = notas["**"]
                elif llamada == "*":
                    cautela[cod] = notas["*"]
            # Evolución: España y media OCDE-35 (2015-2022; 2025 ya está arriba para España)
            for cod, porAnio in evolucion(wb[hevo]).items():
                for anio, (v, et) in porAnio.items():
                    if cod == "00" and anio == "2025":
                        if abs(v - d25["00"][0]) > 0.005:
                            errores.append(f"{hevo}: España 2025 {v} frente a {d25['00'][0]} en {h25}")
                        continue
                    punt.append(fila("pisa_puntuacion", cod, anio, v, "puntos", et, m["fecha_captura"], comp))
            # Niveles de rendimiento: < nivel 2 y niveles 5-6
            filas = filas_hoja(wb[hniv])
            cab = next(r for r in filas if r and r[0] == "Jurisdicción")
            niveles = [str(x).strip() for x in cab[1:] if x]
            for r in filas:
                cod, _ = territorio(r[0]) if r and r[0] else (None, "")
                if not cod or cod == "OCDE35":
                    continue
                pct = [x for x in r[1:] if isinstance(x, (int, float))][0::2]  # % y ET alternan
                if len(pct) != len(niveles):
                    continue
                if abs(sum(pct) - 100) > 0.6:
                    errores.append(f"{hniv} {cod}: los niveles suman {sum(pct):.1f}")
                nv = dict(zip(niveles, pct))
                b = sum(v for n, v in nv.items() if re.search(r"<\s*1|1a|1b", n))
                a = nv.get("Nivel 5", 0) + nv.get("Nivel 6", 0)
                bajo.append(fila("pisa_bajo", cod, "2025", b, "pct", None, m["fecha_captura"], comp))
                alto.append(fila("pisa_alto", cod, "2025", a, "pct", None, m["fecha_captura"], comp))
        # Comunidades en ediciones anteriores: ciencias 2015 y matemáticas 2022, con la diferencia y su ET oficial
        for hoja, comp, desde in (("Figura 2.11", "ciencias", "2015"), ("Figura 2.22", "matematicas", "2022")):
            camb, anteriores = cambios(wb[hoja], comp, desde, errores)
            todos_cambios += camb
            ref25 = {f["territorio"]: f["valor"] for f in punt if f["competencia"] == comp and f["periodo"] == "2025"}
            for c in camb:
                if c["territorio"] in ref25 and abs(ref25[c["territorio"]] - c["valor_2025"]) > 0.005:
                    errores.append(f"{hoja} {c['territorio']}: 2025 = {c['valor_2025']} frente a {ref25[c['territorio']]}")
            ya = {(f["territorio"], f["periodo"]) for f in punt if f["competencia"] == comp}
            for cod, (v, et) in anteriores.items():
                if (cod, desde) not in ya:
                    punt.append(fila("pisa_puntuacion", cod, desde, v, "puntos", et, m["fecha_captura"], comp))
                elif cod == "00":
                    previo = next(f["valor"] for f in punt if f["territorio"] == "00" and f["periodo"] == desde and f["competencia"] == comp)
                    if abs(previo - v) > 0.01:
                        errores.append(f"{hoja}: España {desde} {v} frente a {previo} en la tabla de evolución")
        wb.close()  # en modo lectura el Excel queda abierto; Windows no deja borrar la carpeta temporal si no
        # Equidad (capítulo 3): diferencia en ciencias entre el cuarto más favorecido y el menos favorecido del índice
        # socioeconómico (ISEC), con su ET (Figura 3.3). Comprobación: diferencia publicada = cuarto 4 − cuarto 1.
        wb3 = openpyxl.load_workbook(Path(tmp) / "Tablas_cap_3.xlsx", read_only=True, data_only=True)
        brecha = []
        for r in filas_hoja(wb3["Figura 3.3"]):
            cod, _ = territorio(r[0]) if r and r[0] else (None, "")
            nums = [x for x in r[1:] if isinstance(x, (int, float))]
            if not cod or len(nums) < 10:
                continue
            q1, q4, dif, et = nums[0], nums[6], nums[8], nums[9]
            if abs((q4 - q1) - dif) > 0.05:
                errores.append(f"Figura 3.3 {cod}: diferencia {dif:.2f} y cuarto 4 − cuarto 1 = {q4 - q1:.2f}")
            brecha.append({**fila("pisa_brecha_isec", cod, "2025", dif, "puntos", et, m["fecha_captura"], "total")})
        # Índice socioeconómico y cultural (ISEC, «ESCS» de la OCDE) medio de cada territorio, con su ET (Figura 3.1)
        isec = []
        for cod, (v, et, _) in tabla_simple(wb3["Figura 3.1"]).items():
            isec.append(fila("pisa_isec", cod, "2025", v, "indice", et, m["fecha_captura"], "total"))
        wb3.close()
    # Ninguna tabla de 2025 puede perder una comunidad (p. ej. por una errata en el nombre: «Madrid, Comnidad de»)
    todos = {t["ine"] for t in TERRITORIOS}
    for nombre, filas in (("puntuación", punt), ("rendimiento bajo", bajo), ("rendimiento alto", alto)):
        for comp in COMPETENCIAS:
            hay = {f["territorio"] for f in filas if f["periodo"] == "2025" and f["competencia"] == comp}
            if todos - hay:
                errores.append(f"{nombre}, {comp} 2025: faltan {sorted(todos - hay)}")
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))

    def guardar(ind, filas, extra):
        periodos = sorted({f["periodo"] for f in filas})
        escribir_json(f"observaciones/{ind}.json", {
            "indicador_id": ind, "periodos": periodos, "notas_fuente": [], "notas": [], "muestra_pequena": [], "rupturas": [],
            "definicion_difiere_es": [],
            "no_comparable": [{"territorio": k, "texto": v} for k, v in no_comparable.items()],
            "cautela": [{"territorio": k, "texto": v} for k, v in cautela.items()],
            **extra,
            "filas": sorted(filas, key=lambda f: (f["territorio"], f["competencia"], f["periodo"])),
        })
        print(f"{ind}: {len(filas)} filas, ediciones {periodos}")

    guardar("pisa_puntuacion", punt, {"cambios": [{k: v for k, v in c.items() if k != "valor_2025"} for c in todos_cambios],
            "comprobacion": {"pares_comparados": len(todos_cambios), "descripcion": "mismos valores en las tablas de 2025, de evolución y de diferencias; diferencia publicada = 2025 − edición anterior"}})
    guardar("pisa_bajo", bajo, {"comprobacion": {"pares_comparados": len(bajo), "descripcion": "los niveles de cada territorio suman 100"}})
    guardar("pisa_alto", alto, {"comprobacion": {"pares_comparados": len(alto), "descripcion": "los niveles de cada territorio suman 100"}})
    falta = {t["ine"] for t in TERRITORIOS} - {f["territorio"] for f in brecha}
    if falta:
        sys.exit(f"Figura 3.3: faltan {sorted(falta)}")
    guardar("pisa_brecha_isec", brecha, {"comprobacion": {"pares_comparados": len(brecha), "descripcion": "diferencia publicada = cuarto 4 − cuarto 1"}})
    falta = {t["ine"] for t in TERRITORIOS} - {f["territorio"] for f in isec}
    if falta:
        sys.exit(f"Figura 3.1: faltan {sorted(falta)}")
    guardar("pisa_isec", isec, {"comprobacion": {"pares_comparados": len(isec), "descripcion": "las 19 comunidades y ciudades, España, OCDE y UE"}})
    print("no comparable:", list(no_comparable), "| cautela:", list(cautela))


if __name__ == "__main__":
    main()
