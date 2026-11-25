"""Indicadores de «Las cifras de la educación en España» (Ministerio de Educación), tablas en Excel.

Uso:  python scripts/descargar.py cifras && python scripts/extraer_cifras.py

Indicadores (salida en src/data/observaciones/):
  - tasa_graduacion (tabla C2.9): tasa bruta de población que se gradúa en ESO, Bachillerato y FP (básica, grado medio
    y grado superior), por sexo, cursos 2013-14, 2018-19 y 2023-24 (FP básica, solo los dos últimos). No se usan ESO de
    adultos ni las titulaciones universitarias (se asignan por la sede del rectorado, no por la residencia: nota 4).

  - becas_bach_fp e importe_becario (tabla B5.5, curso 2023-24): % de alumnado becario e importe medio por becario en
    Bachillerato y FP, de todas las administraciones (Ministerio y comunidades), tal cual los publica el Ministerio.
    Se comprueba con B5.3 y B5.4 (importe / becarios) y con la tabla 2 de la estadística de becas (EDUCAbase).

Comprobaciones: las 19 comunidades y ciudades y España en cada sexo; el valor de ambos sexos queda entre el de hombres
y el de mujeres (con 0,1 de margen por redondeo); cabecera de enseñanzas y cursos como se espera.
"""
from __future__ import annotations

import re
import sys

import openpyxl

from comun import RAIZ, TERRITORIOS, celdas_px, escribir_json, leer_px, territorio, ultimo_original

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


ETAPAS_BECAS = {"TOTAL": "total", "BACHILLERATO": "bachillerato", "FORMACIÓN PROFESIONAL": "fp"}
UMBRAL_AUTONOMICAS = 10  # % de becarios con beca de su comunidad a partir del cual se cita en el aviso de la ficha
NOMBRES = {"01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Illes Balears", "05": "Canarias", "06": "Cantabria",
           "07": "Castilla y León", "08": "Castilla-La Mancha", "09": "Cataluña", "10": "Comunitat Valenciana", "11": "Extremadura",
           "12": "Galicia", "13": "Madrid", "14": "Murcia", "15": "Navarra", "16": "País Vasco", "17": "La Rioja"}


def _hoja(m: dict, nombre: str) -> list[list]:
    wb = openpyxl.load_workbook(m["ruta"], read_only=True, data_only=True)
    filas = [list(r) for r in wb[nombre].iter_rows(values_only=True)]
    wb.close()
    return filas


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


def becas(errores: list) -> None:
    """B5.5: % de alumnado becario e importe medio por becario en Bachillerato y FP (todas las administraciones)."""
    m = ultimo_original("cifras", "b5.xlsx")
    filas = _hoja(m, "B5.5")
    i_cab = next(i for i, r in enumerate(filas) if any(limpio(x).upper() == "BACHILLERATO" for x in r))
    etapa, cols = None, {}
    for c, (e, med) in enumerate(zip(filas[i_cab], filas[i_cab + 1])):
        if e:
            etapa = ETAPAS_BECAS.get(limpio(e).upper())
            if etapa is None:
                errores.append(f"B5.5: enseñanza desconocida «{limpio(e)}»")
        med = limpio(med)
        if etapa and med:
            ind = "becas_bach_fp" if med.startswith("% Alumnos") else "importe_becario" if med.startswith("Importe medio") else None
            if ind is None:
                errores.append(f"B5.5: medida desconocida «{med}»")
            else:
                cols[c] = (ind, etapa)
    if len(cols) != 6:
        errores.append(f"B5.5: se esperaban 6 columnas y hay {len(cols)}")
        return
    # El curso no va en el Excel: va en la cabecera del PDF («CURSO 2023-24»)
    curso = "2023-24"
    if f"CURSO {curso}" not in _texto_pdf(ultimo_original("cifras", "b5.pdf")["ruta"]):
        errores.append(f"B5.5: el PDF no dice «CURSO {curso}»")
    obs, sin_dato = [], []
    for r in filas[i_cab + 2:]:
        if not r or not r[0]:
            continue
        if str(r[0]).strip().startswith("("):
            break
        t = territorio(str(r[0]))
        vals = {c: _num(r[c]) for c in cols}
        if all(v is None for v in vals.values()):
            sin_dato.append(t["ine"])
            continue
        for c, (ind, et) in cols.items():
            if vals[c] is None:
                errores.append(f"B5.5 {t['ine']}: falta {ind} {et}")
                continue
            obs.append({"indicador_id": ind, "territorio": t["ine"], "periodo": curso, "titularidad": "total", "sexo": "total",
                        "etapa": et, "valor": round(vals[c], 4 if ind == "becas_bach_fp" else 2),
                        "unidad": "pct" if ind == "becas_bach_fp" else "eur", "error_estandar": None, "estado": "definitivo",
                        "fuente_id": "mefd_cifras", "url_fuente": URL_CIFRAS, "fecha_captura": m["fecha_captura"]})
    val = {(f["indicador_id"], f["territorio"], f["etapa"]): f["valor"] for f in obs}
    hay = sorted({f["territorio"] for f in obs})
    # Comprobación 1: importe medio = importe (B5.4, miles de euros) / becarios (B5.3); FP = básica + media + superior
    becarios, importes = _por_ensenanza(_hoja(m, "B5.3")), _por_ensenanza(_hoja(m, "B5.4"))
    grupos = {"bachillerato": ["Bachillerato"], "fp": ["FP de Grado Básico", "FP de Grado Medio", "FP de Grado Superior"]}
    grupos["total"] = grupos["bachillerato"] + grupos["fp"]
    n_imp = 0
    for ine in hay:
        b, i = becarios.get(ine), importes.get(ine)
        if not b or not i:
            errores.append(f"B5.3/B5.4: falta {ine}")
            continue
        for et, cs in grupos.items():
            calc = 1000 * sum(i[c] for c in cs) / sum(b[c] for c in cs)
            n_imp += 1
            if abs(calc - val[("importe_becario", ine, et)]) > 0.5:
                errores.append(f"B5.5 {ine} {et}: importe medio {val[('importe_becario', ine, et)]} y B5.4/B5.3 dan {calc:.2f}")
    # Comprobación 2: el % del total queda entre el de Bachillerato y el de FP
    for ine in hay:
        tot, ba, fp = (val[("becas_bach_fp", ine, e)] for e in ("total", "bachillerato", "fp"))
        if not min(ba, fp) - 0.05 <= tot <= max(ba, fp) + 0.05:
            errores.append(f"B5.5 {ine}: % total {tot} fuera de [{ba}, {fp}]")
    todos = {t["ine"] for t in TERRITORIOS}
    if todos - set(hay) - set(sin_dato):
        errores.append(f"B5.5: faltan {sorted(todos - set(hay) - set(sin_dato))}")
    # Nota de Galicia (en el Excel va en B5.3 y B5.4; en el PDF, también en B5.5)
    nota_gal = next((re.sub(r"^\(\d+\)\s*", "", limpio(r[0])) for r in _hoja(m, "B5.3")
                     if r and r[0] and str(r[0]).startswith("(") and "Galicia" in str(r[0])), None)
    if sin_dato and not nota_gal:
        errores.append(f"B5.5: sin dato {sin_dato} y sin nota que lo explique")
    # La nota dice que el total de España incluye los datos de Galicia de 2020-21: se cita también en España
    notas = [{"texto": nota_gal, "territorios": sin_dato + ["00"], "periodos": [curso]}] if nota_gal and sin_dato else []
    # Peso de las becas de la propia comunidad (tabla 2 de la estadística de becas, enseñanzas postobligatorias no
    # universitarias, curso 2023-24): cálculo propio para el aviso de la ficha; aquí se comprueba que el aviso cuadra.
    autonomicas = _becas_autonomicas(errores)
    citadas = sorted(((ine, p) for ine, p in autonomicas.items() if p >= UMBRAL_AUTONOMICAS), key=lambda x: -x[1])
    frase = ", ".join(f"{NOMBRES[ine]} ({round(p):d} %)" for ine, p in citadas)
    ficha = (RAIZ / "src/data/indicadores/becas_bach_fp.json").read_text(encoding="utf-8")
    if frase not in ficha:
        errores.append(f"La ficha becas_bach_fp debe citar, en este orden: «{frase}»")
    for ind in ("becas_bach_fp", "importe_becario"):
        filas_ind = sorted((f for f in obs if f["indicador_id"] == ind), key=lambda f: (f["territorio"], f["etapa"]))
        escribir_json(f"observaciones/{ind}.json", {
            "indicador_id": ind, "periodos": [curso], "notas_fuente": [n["texto"] for n in notas], "notas": notas,
            "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
            "becas_autonomicas": {ine: round(p, 1) for ine, p in sorted(autonomicas.items())},
            "comprobacion": {"pares_comparados": n_imp, "descripcion": "importe medio = importe (B5.4) / becarios (B5.3); % total entre Bachillerato y FP"},
            "filas": filas_ind,
        })
        print(f"{ind}: {len(filas_ind)} filas, curso {curso}; sin dato: {sin_dato}")
    print(f"becas: {n_imp} importes medios comprobados; becas de la propia comunidad >= {UMBRAL_AUTONOMICAS} %: {frase}")


def _texto_pdf(ruta) -> str:
    import subprocess
    try:
        return subprocess.run(["pdftotext", "-layout", str(ruta), "-"], capture_output=True, check=True).stdout.decode("latin-1", "ignore")
    except Exception as e:
        raise SystemExit(f"No se pudo leer {ruta} con pdftotext: {e}")


def _por_ensenanza(filas: list[list]) -> dict[str, dict[str, float]]:
    """Primer bloque (valores absolutos) de B5.3 / B5.4: {territorio: {enseñanza: valor}}."""
    i_cab = next(i for i, r in enumerate(filas) if r and r[0] is None and any(limpio(x) == "TOTAL" for x in r[1:] if x))
    cab = [re.sub(r"\s*\(\d+\)$", "", re.sub(r"\s+", " ", str(x or "")).replace("- ", "").replace("-\n", "")).strip() for x in filas[i_cab]]
    out: dict[str, dict[str, float]] = {}
    empezado = False
    for r in filas[i_cab + 1:]:
        if r and r[0] and str(r[0]).strip() == "TOTAL":
            if empezado:
                break  # empieza el bloque de porcentajes
            empezado = True
        if not empezado or not r or not r[0] or str(r[0]).startswith(("(", "Sin especificar")):
            continue
        ine = "00" if str(r[0]).strip() == "TOTAL" else territorio(str(r[0]))["ine"]
        nums = {cab[c]: _num(r[c]) for c in range(1, len(cab)) if cab[c]}
        if all(v is not None for v in nums.values()):
            out[ine] = nums
    for c in ("Bachillerato", "FP de Grado Básico", "FP de Grado Medio", "FP de Grado Superior"):
        if not out or c not in next(iter(out.values())):
            raise SystemExit(f"B5.3/B5.4: no encuentro la columna «{c}» en {cab}")
    return out


def _becas_autonomicas(errores: list) -> dict[str, float]:
    """% de los becarios de enseñanzas postobligatorias no universitarias que lo son de su comunidad (tabla 2)."""
    m = ultimo_original("becas", "todas2_2023-2024.px")
    px = leer_px(m["ruta"])
    c = celdas_px(px)
    e = "Enseñanzas postobligatorias no universitarias"
    becarios = next(v for v in px['VALUES("Becarios, becas e importe")'] if v.startswith("BECARIOS"))
    todas, minis, ccaa = px['VALUES("Nivel de administración educativa financiadora")']
    out = {}
    for et in px['VALUES("Comunidad autónoma de destino")']:
        if et.startswith(("TOTAL", "Sin especificar", "UNED")):
            continue
        t = territorio(et)
        if t["ine"] not in NOMBRES:
            continue
        tot, mi, ca = (c[(et, becarios, e, a)] for a in (todas, minis, ccaa))
        if ca is None:
            continue  # Galicia: sin datos de su administración
        if tot != mi + ca:
            errores.append(f"Becas tabla 2 {et}: total {tot} distinto de Ministerio {mi} + comunidad {ca}")
        out[t["ine"]] = 100 * ca / tot
    if len(out) != 16:
        errores.append(f"Becas tabla 2: se esperaban 16 comunidades con datos y hay {len(out)}")
    return out


def main() -> None:
    errores: list[str] = []
    graduacion(errores)
    gasto_alumno(errores)
    becas(errores)
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))


if __name__ == "__main__":
    main()
