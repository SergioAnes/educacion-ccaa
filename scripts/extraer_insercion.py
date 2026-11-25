"""Empleo de los titulados de FP: Estadística de inserción laboral de las personas graduadas en FP (Ministerio de
Educación con la Tesorería General de la Seguridad Social), resultados por comunidad autónoma en EDUCAbase.

Uso:  python scripts/descargar.py insercion cifras && python scripts/extraer_insercion.py

Indicador (salida en src/data/observaciones/empleo_fp.json):
  - empleo_fp: «tasa de afiliación» (porcentaje de titulados de alta laboral en la Seguridad Social en algún momento
    del mes de marzo) al año y a los tres años de titularse, por grado (básico, medio, superior), sexo y comunidad del
    centro donde se titularon. El periodo es la cohorte (curso en que se titularon); para la cohorte t/t+1, «al año» es
    marzo de t+2 y «a los tres años», marzo de t+4 (metodología). Cohortes con «(p)»: provisionales.
    No se usa la «tasa de afiliación media» (sale en las tablas, pero «Las cifras de la educación» publica la otra).

Comprobaciones: ambos sexos entre hombres y mujeres; tasa de afiliación ≥ tasa de afiliación media; la cohorte
2020-21 de grado medio y superior coincide con la tabla F1.9 de «Las cifras de la educación» 2026 (salvo la columna
«previo a la graduación», que no se usa: en el Excel de F1.9, Cataluña grado medio ambos sexos trae 89,0 y el PDF y
EDUCAbase, 13,4).
"""
from __future__ import annotations

import re
import sys

import openpyxl

from comun import TERRITORIOS, celdas_px, escribir_json, leer_px, territorio, ultimo_original

URL = "https://estadisticas.educacion.gob.es/EducaJaxiPx/Tabla.htm?path=/laborales/insercion/ccaa/l0/&file=ccaa_{n}_01.px"
GRADOS = {1: "fp_basica", 2: "fp_medio", 3: "fp_superior"}
MOMENTOS = {"Primer año": "al_anio", "Tercer año": "tres_anios"}
SEXOS = {"AMBOS SEXOS": "total", "Hombres": "h", "Mujeres": "m"}
TASA, MEDIA = "Tasa de afiliación", "Tasa de afiliación media"


def curso_corto(cohorte: str) -> tuple[str, bool]:
    """«2021-2022 (p)» -> («2021-22», provisional)."""
    m = re.fullmatch(r"(\d{4})-(\d{4})\s*(\(p\))?", cohorte.strip())
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        raise SystemExit(f"Cohorte inesperada: {cohorte!r}")
    return f"{m.group(1)}-{m.group(2)[2:]}", bool(m.group(3))


def main() -> None:
    errores: list[str] = []
    obs, notas_px = [], {}
    for n, grado in GRADOS.items():
        m = ultimo_original("insercion", f"ccaa_{n}_01.px")
        px = leer_px(m["ruta"])
        c = celdas_px(px)
        v_ccaa = next(k for k in px if k.startswith('VALUES("Comunidad'))
        dim_ccaa = v_ccaa[len('VALUES("'):-2]
        if px["STUB"] != ["Cohorte", dim_ccaa] or px["HEADING"] != ["Sexo", "Indicador", "Periodo de análisis"]:
            errores.append(f"ccaa_{n}_01: dimensiones inesperadas {px['STUB']} {px['HEADING']}")
            continue
        if {TASA, MEDIA} - set(px['VALUES("Indicador")']):
            errores.append(f"ccaa_{n}_01: faltan los indicadores {TASA} / {MEDIA}")
            continue
        notas_px[grado] = px.get("NOTE", "")
        for coh in px['VALUES("Cohorte")']:
            periodo, prov = curso_corto(coh)
            for et in px[v_ccaa]:
                if et == "Ceuta y Melilla":
                    continue  # vienen juntas: no se pueden mostrar como dos ciudades
                ine = "00" if et == "TOTAL" else territorio(et)["ine"]
                for s_px, sexo in SEXOS.items():
                    for p_px, momento in MOMENTOS.items():
                        v = c[(coh, et, s_px, TASA, p_px)]
                        vm = c[(coh, et, s_px, MEDIA, p_px)]
                        if v is None:
                            continue
                        if vm is not None and v + 0.05 < vm:
                            errores.append(f"{grado} {periodo} {ine} {sexo} {momento}: tasa {v} < tasa media {vm}")
                        obs.append({"indicador_id": "empleo_fp", "territorio": ine, "periodo": periodo, "titularidad": "total",
                                    "sexo": sexo, "etapa": grado, "competencia": momento, "valor": v, "unidad": "pct",
                                    "error_estandar": None, "estado": "provisional" if prov else "definitivo",
                                    "fuente_id": "mefd_insercion", "url_fuente": URL.format(n=n), "fecha_captura": m["fecha_captura"]})
    # Comprobación 1: ambos sexos entre hombres y mujeres (0,1 de margen por redondeo)
    val = {(f["etapa"], f["periodo"], f["territorio"], f["sexo"], f["competencia"]): f["valor"] for f in obs}
    entre = 0
    for (g, p, t, s, mo), v in val.items():
        if s != "total":
            continue
        h, mu = val.get((g, p, t, "h", mo)), val.get((g, p, t, "m", mo))
        if h is not None and mu is not None:
            entre += 1
            if not min(h, mu) - 0.1 <= v <= max(h, mu) + 0.1:
                errores.append(f"{g} {p} {t} {mo}: ambos sexos {v} fuera de [{h}, {mu}]")
    # Comprobación 2: la cohorte 2020-21 coincide con F1.9 de «Las cifras de la educación»
    iguales = f19(val, errores)
    # Las 17 comunidades y España en grado medio y superior, en la última cohorte con dato a los tres años
    ccaa = {t["ine"] for t in TERRITORIOS if t["ine"] not in ("18", "19")} | {"00"}
    for g in ("fp_medio", "fp_superior"):
        for mo in MOMENTOS.values():
            ult = max(p for (gg, p, t, s, m_) in val if gg == g and m_ == mo)
            hay = {t for (gg, p, t, s, m_) in val if gg == g and m_ == mo and p == ult and s == "total"}
            if ccaa - hay:
                errores.append(f"{g} {mo} {ult}: faltan {sorted(ccaa - hay)}")
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))
    nota = next(iter(notas_px.values()))
    textos = [re.sub(r"^\s*\d\)\s*", "", x).strip() for x in re.split(r"\s*#\s*", nota) if x.strip()]
    textos = [re.sub(r"\s+", " ", x) for x in textos if not x.startswith("(..)")]
    periodos = sorted({f["periodo"] for f in obs})
    provisionales = sorted({f["periodo"] for f in obs if f["estado"] == "provisional"})
    escribir_json("observaciones/empleo_fp.json", {
        "indicador_id": "empleo_fp", "periodos": periodos, "notas_fuente": textos,
        "notas": [{"texto": t, "territorios": [], "periodos": provisionales if "provisional" in t.lower() else []} for t in textos
                  if "representativa" not in t],
        "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
        "comprobacion": {"pares_comparados": entre, "iguales_f19": iguales,
                         "descripcion": "ambos sexos entre hombres y mujeres; tasa ≥ tasa media; cohorte 2020-21 = F1.9"},
        "filas": sorted(obs, key=lambda f: (f["territorio"], f["etapa"], f["competencia"], f["sexo"], f["periodo"])),
    })
    print(f"empleo_fp: {len(obs)} filas, cohortes {periodos[0]} a {periodos[-1]} (provisionales {provisionales}); "
          f"{entre} comprobaciones de sexo; {iguales} cifras iguales a F1.9")


def f19(val: dict, errores: list) -> int:
    """Compara la cohorte 2020-21 (grado medio y superior, al año y a los tres años, tres sexos) con F1.9."""
    m = ultimo_original("cifras", "f1.xlsx")
    wb = openpyxl.load_workbook(m["ruta"], read_only=True, data_only=True)
    filas = [list(r) for r in wb["F1.9"].iter_rows(values_only=True)]
    wb.close()
    if not any("Graduados 2020-2021" in str(x) for r in filas[:3] for x in r if x):
        errores.append("F1.9: no es la cohorte 2020-2021")
        return 0
    i_g = next(i for i, r in enumerate(filas) if any(str(x or "").startswith("C.F. Grado Medio") for x in r))
    grado, cols = None, {}
    for c, (g, p) in enumerate(zip(filas[i_g], filas[i_g + 1])):
        if g:
            grado = {"C.F. Grado Medio": "fp_medio", "C.F. Grado Superior": "fp_superior"}.get(str(g).strip())
        if grado and p and str(p).strip() in MOMENTOS:
            cols[c] = (grado, MOMENTOS[str(p).strip()])
    if len(cols) != 4:
        errores.append(f"F1.9: columnas inesperadas {cols}")
        return 0
    sexo, iguales = None, 0
    for r in filas[i_g + 2:]:
        if not r or not r[0]:
            continue
        et = str(r[0]).strip()
        if et.upper() in ("AMBOS SEXOS", "HOMBRES", "MUJERES"):
            sexo = {"AMBOS SEXOS": "total", "HOMBRES": "h", "MUJERES": "m"}[et.upper()]
            ine = "00"
        elif et == "Ceuta y Melilla" or et.startswith("("):
            continue
        else:
            ine = territorio(et)["ine"]
        for c, (g, mo) in cols.items():
            nuestro = val.get((g, "2020-21", ine, sexo, mo))
            if nuestro is None or abs(nuestro - float(r[c])) > 0.051:
                errores.append(f"F1.9 {et} {sexo} {g} {mo}: {r[c]} y EDUCAbase {nuestro}")
            else:
                iguales += 1
    return iguales


if __name__ == "__main__":
    main()
