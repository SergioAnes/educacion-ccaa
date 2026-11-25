"""Indicadores de «Las cifras de la educación en España» (Ministerio de Educación), tablas en Excel.

Uso:  python scripts/descargar.py cifras && python scripts/extraer_cifras.py

Indicadores (salida en src/data/observaciones/):
  - tasa_graduacion (tabla C2.9): tasa bruta de población que se gradúa en ESO, Bachillerato y FP (básica, grado medio
    y grado superior), por sexo, cursos 2013-14, 2018-19 y 2023-24 (FP básica, solo los dos últimos). No se usan ESO de
    adultos ni las titulaciones universitarias (se asignan por la sede del rectorado, no por la residencia: nota 4).

Comprobaciones: las 19 comunidades y ciudades y España en cada sexo; el valor de ambos sexos queda entre el de hombres
y el de mujeres (con 0,1 de margen por redondeo); cabecera de enseñanzas y cursos como se espera.
"""
from __future__ import annotations

import re
import sys

import openpyxl

from comun import TERRITORIOS, escribir_json, territorio, ultimo_original

URL_CIFRAS = "https://www.educacionfpydeportes.gob.es/servicios-al-ciudadano/estadisticas/indicadores/cifras-educacion-espana/2023-2024.html"
ENSENANZAS = {"Graduado en ESO": "eso", "Bachillerato": "bachillerato", "Profesional Básico": "fp_basica",
              "Técnico": "fp_medio", "Técnico Superior": "fp_superior"}
SEXOS = {"AMBOS SEXOS": "total", "HOMBRES": "h", "MUJERES": "m"}


def limpio(x) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", re.sub(r"\s+", " ", str(x or ""))).strip()


def graduacion(errores: list) -> None:
    m = ultimo_original("cifras", "c2.xlsx")
    wb = openpyxl.load_workbook(m["ruta"], read_only=True, data_only=True)
    filas = [list(r) for r in wb["C2.9"].iter_rows(values_only=True)]
    wb.close()
    # Cabecera: enseñanza (celdas combinadas: se arrastra hacia la derecha) y curso
    i_ens = next(i for i, r in enumerate(filas) if any(limpio(x) == "Graduado en ESO" for x in r))
    ens, cols = None, {}
    for c, (e, curso) in enumerate(zip(filas[i_ens], filas[i_ens + 1])):
        if e:
            ens = ENSENANZAS.get(limpio(e))
            if limpio(e) and limpio(e) not in ENSENANZAS and not limpio(e).startswith(("Graduado en ESO Adulto", "Grado", "Máster")):
                errores.append(f"C2.9: enseñanza desconocida «{limpio(e)}»")
        if ens and curso and re.fullmatch(r"\d{4}-\d{2}", str(curso).strip()):
            cols[c] = (ens, str(curso).strip())
    notas = [re.sub(r"\s+", " ", str(r[0])).strip() for r in filas if r and r[0] and str(r[0]).strip().startswith("(")]
    obs, sexo = [], None
    citas: dict[str, set] = {}
    for r in filas[i_ens + 2:]:
        if not r or not r[0]:
            continue
        et = str(r[0]).strip()
        if et in SEXOS:
            sexo = SEXOS[et]
            continue
        if et.startswith("("):
            continue
        t = territorio(et)
        for n in re.findall(r"\((\d+)\)", et):
            citas.setdefault(n, set()).add(t["ine"])
        for c, (e, curso) in cols.items():
            v = r[c] if c < len(r) else None
            if isinstance(v, (int, float)):
                obs.append({"indicador_id": "tasa_graduacion", "territorio": t["ine"], "periodo": curso, "titularidad": "total",
                            "sexo": sexo, "etapa": e, "valor": float(v), "unidad": "pct", "error_estandar": None, "estado": "definitivo",
                            "fuente_id": "mefd_cifras", "url_fuente": URL_CIFRAS, "fecha_captura": m["fecha_captura"]})
    # Comprobaciones
    todos = {t["ine"] for t in TERRITORIOS}
    for s in SEXOS.values():
        hay = {f["territorio"] for f in obs if f["sexo"] == s}
        if todos - hay:
            errores.append(f"C2.9 {s}: faltan {sorted(todos - hay)}")
    val = {(f["territorio"], f["etapa"], f["periodo"], f["sexo"]): f["valor"] for f in obs}
    entre = 0
    for (t, e, p, s), v in val.items():
        if s != "total":
            continue
        h, mu = val.get((t, e, p, "h")), val.get((t, e, p, "m"))
        if h is not None and mu is not None:
            entre += 1
            if not (min(h, mu) - 0.1 <= v <= max(h, mu) + 0.1):
                errores.append(f"C2.9 {t} {e} {p}: ambos sexos {v} fuera de [{h}, {mu}]")
    # Notas: solo las que tocan a lo que mostramos (2, 3 y 6; la 1 es de ESO de adultos y la 4 y la 5, de universidad)
    usadas = []
    for texto in notas:
        n = re.match(r"\((\d+)\)", texto).group(1)
        if n in ("2", "3", "6"):
            usadas.append({"texto": re.sub(r"^\(\d+\)\s*", "", texto), "territorios": sorted(citas.get(n, [])), "periodos": []})
    periodos = sorted({f["periodo"] for f in obs})
    escribir_json("observaciones/tasa_graduacion.json", {
        "indicador_id": "tasa_graduacion", "periodos": periodos, "notas_fuente": [n["texto"] for n in usadas], "notas": usadas,
        "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
        "comprobacion": {"pares_comparados": entre, "descripcion": "ambos sexos entre hombres y mujeres; 19 territorios y España"},
        "filas": sorted(obs, key=lambda f: (f["territorio"], f["etapa"], f["sexo"], f["periodo"])),
    })
    print(f"tasa_graduacion: {len(obs)} filas, cursos {periodos}, {entre} comprobaciones; notas {[n['territorios'] for n in usadas]}")


def gasto_alumno(errores: list) -> None:
    """B4.6: gasto público por alumno en enseñanza no universitaria (euros), «público y concertado» y «público»."""
    m = ultimo_original("cifras", "b4.xlsx")
    wb = openpyxl.load_workbook(m["ruta"], read_only=True, data_only=True)
    filas = [list(r) for r in wb["B4.6"].iter_rows(values_only=True)]
    wb.close()
    i_cab = next(i for i, r in enumerate(filas) if any("por alumno público y concertado" in limpio(x) for x in r))
    cab = [limpio(x) for x in filas[i_cab]]
    anios = [str(x).strip() for x in filas[i_cab + 1] if x]
    c_pc = next(c for c, x in enumerate(cab) if "público y concertado" in x)
    c_p = next(c for c, x in enumerate(cab) if x.startswith("Gasto público por alumno público") and "concertado" not in x)
    if len(set(anios)) != 1 or not re.fullmatch(r"\d{4}", anios[0]):
        errores.append(f"B4.6: años inesperados {anios}")
        return
    anio = anios[0]
    obs = []
    for r in filas[i_cab + 2:]:
        if r and r[0] and str(r[0]).strip().startswith("("):
            break  # empiezan las notas (que siguen en varias filas)
        if not r or not r[0]:
            continue
        t = territorio(str(r[0]))
        for c, tit in ((c_pc, "publica_y_concertada"), (c_p, "publica")):
            v = r[c]
            v = float(str(v).replace(".", "")) if isinstance(v, str) and re.fullmatch(r"[\d.]+", v.strip()) else v
            if isinstance(v, (int, float)):
                obs.append({"indicador_id": "gasto_alumno", "territorio": t["ine"], "periodo": anio, "titularidad": tit, "sexo": "total",
                            "etapa": "total", "valor": float(v), "unidad": "eur", "error_estandar": None, "estado": "definitivo",
                            "fuente_id": "mefd_cifras", "url_fuente": URL_CIFRAS, "fecha_captura": m["fecha_captura"]})
    # Comprobaciones: las 17 comunidades y España en las dos columnas; España entre la menor y la mayor comunidad
    ccaa = {f"{i:02d}" for i in range(1, 18)}
    for tit in ("publica_y_concertada", "publica"):
        hay = {f["territorio"]: f["valor"] for f in obs if f["titularidad"] == tit}
        if ccaa - set(hay) or "00" not in hay:
            errores.append(f"B4.6 {tit}: faltan {sorted((ccaa | {'00'}) - set(hay))}")
        elif not min(hay[c] for c in ccaa) <= hay["00"] <= max(hay[c] for c in ccaa):
            errores.append(f"B4.6 {tit}: España fuera del rango de las comunidades")
    nota = " ".join(limpio(r[0]) for r in filas if r and r[0] and (str(r[0]).strip().startswith("(1)") or (obs and str(r[0]).strip()[:1].islower())))
    escribir_json("observaciones/gasto_alumno.json", {
        "indicador_id": "gasto_alumno", "periodos": [anio], "notas_fuente": [nota] if nota else [],
        "notas": [{"texto": re.sub(r"^\(1\)\s*", "", nota), "territorios": [], "periodos": []}] if nota else [],
        "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
        "comprobacion": {"pares_comparados": len(obs), "descripcion": "17 comunidades y España en las dos columnas; España entre la menor y la mayor"},
        "filas": sorted(obs, key=lambda f: (f["territorio"], f["titularidad"])),
    })
    print(f"gasto_alumno: {len(obs)} filas, año {anio}; nota: {nota[:90]}…")


def main() -> None:
    errores: list[str] = []
    graduacion(errores)
    gasto_alumno(errores)
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))


if __name__ == "__main__":
    main()
