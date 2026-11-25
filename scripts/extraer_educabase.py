"""Indicadores de la Estadística de las Enseñanzas no universitarias (EDUCAbase), por comunidad autónoma y curso.

Uso:  python scripts/descargar.py educabase && python scripts/extraer_educabase.py

Salida: src/data/observaciones/<indicador>.json (esquema común, formato largo) — no editar a mano.

Indicadores:
  - alumnado_titularidad: % del alumnado de Régimen General en centros públicos, privados concertados y privados no
    concertados (cálculo propio: cada grupo / total, con los recuentos de todas_01 de cada curso, 2011-12 en adelante).
  - escolarizacion_0_2: tasa neta de escolarización de 0 a 2 años (publicada), por sexo.
  - alumnado_extranjero: % de alumnado extranjero en Régimen General (publicado).
  - alumnos_profesor: número medio de alumnos por profesor (publicado), por titularidad.
  - idoneidad_15: tasa de idoneidad a los 15 años (publicada), por sexo.
  - repeticion_eso: tasa de alumnado repetidor en ESO, todos los cursos (publicada), por titularidad/financiación.

Comprobaciones (el script se para si fallan):
  - Titularidad: pública + privada = total y concertada + no concertada = privada en cada comunidad; la suma de las
    comunidades (con Ceuta y Melilla) = España; total, pública y privada = serie alumnado_1_01; % en pública = el
    publicado en general_01 (redondeo).
  - Alumnos por profesor = alumnado (alumnado_1_01) / profesorado (series03), como dice la nota de la tabla.
  - % de alumnado extranjero = extranjeros (extran_02) / alumnado (alumnado_1_01).
Las notas de cada tabla se guardan tal cual, con las comunidades y cursos que las citan.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

from comun import POR_ALIAS, celdas_px, escribir_json, leer_px, territorio, ultimo_original

FUENTE = "educabase"
URL_TABLA = "https://estadisticas.educacion.gob.es/EducaJaxiPx/Tabla.htm?path=/{ruta}/&file={fichero}"
RUTAS = {
    "alumnado_1_01.px": "no-universitaria/alumnado/matriculado/series/AlumnadoGen/l0",
    "general_01.px": "no-universitaria/alumnado/matriculado/series/gen-porcen-gen/l0",
    "escolar_05.px": "no-universitaria/alumnado/matriculado/series/gen-escolar/l0",
    "idoneidad_05.px": "no-universitaria/alumnado/matriculado/series/gen-idoneidad/l0",
    "repetidores_03.px": "no-universitaria/alumnado/matriculado/series/gen-repetidores/l0",
    "extran_02.px": "no-universitaria/alumnado/matriculado/series/extranjeros/l0",
    "extran_04.px": "no-universitaria/alumnado/matriculado/series/extranjeros/l0",
    "series03.px": "no-universitaria/profesorado/estadistica/series/l0",
    "series07.px": "no-universitaria/profesorado/estadistica/series/l0",
}
# Número medio de alumnado por unidad (grupo), por etapa: fuente «unidades» de descargar.py
U = "no-universitaria/centros/centrosyunid/series/unidades/l0"
ETAPAS_UNIDAD = {  # etapa -> tabla
    "infantil1": "series_2_02.px", "infantil2": "series_2_03.px", "primaria": "series_2_04.px", "eso": "series_2_06.px",
    "bachillerato": "series_2_07.px", "fp_basica": "series_2_08.px", "fp_medio": "series_2_09.px", "fp_superior": "series_2_10.px",
}
RUTAS.update({n: U for n in [*ETAPAS_UNIDAD.values(), "series_1_04.px", "series_1_06.px"]})
RUTAS.update({"alumnado_3_01.px": RUTAS["alumnado_1_01.px"], "alumnado_4_01.px": RUTAS["alumnado_1_01.px"]})
FUENTE_DE = {n: "unidades" for n in [*ETAPAS_UNIDAD.values(), "series_1_04.px", "series_1_06.px", "alumnado_3_01.px", "alumnado_4_01.px"]}
SEXO = {"AMBOS SEXOS": "total", "HOMBRES": "h", "MUJERES": "m"}
TITULARIDAD = {
    "TODOS LOS CENTROS": "total", "TOTAL": "total", "CENTROS PÚBLICOS": "publica", "CENTROS PRIVADOS": "privada",
    "CENTROS PRIVADOS TOTAL": "privada", "CENTROS PRIVADOS E. CONCERTADA": "concertada",
    "CENTROS PRIVADOS E. NO CONCERTADA": "privada_no_concertada",
    "ENSEÑANZA PRIVADA CONCERTADA": "concertada", "ENSEÑANZA PRIVADA NO CONCERTADA": "privada_no_concertada",
    "CENTROS PRIVADOS CONCERTADOS": "concertada", "CENTROS PRIVADOS NO CONCERTADOS": "privada_no_concertada",
}
DESDE = "2000-01"  # las series largas se muestran desde este curso


def llamadas(etiqueta: str) -> list[str]:
    return re.findall(r"\((\d+|\*)\)", etiqueta)


def sin_llamadas(etiqueta: str) -> str:
    return re.sub(r"\s*\((\d+|\*)\)", "", etiqueta).strip()


def curso(etiqueta: str) -> str:
    """«2025-2026 (*)» o «2025-26 (*)» -> «2025-26»."""
    m = re.match(r"(\d{4})-(\d{2,4})", etiqueta.strip())
    if not m:
        sys.exit(f"Curso no reconocido: {etiqueta!r}")
    return f"{m.group(1)}-{m.group(2)[-2:]}"


def notas_de(px: dict) -> dict[str, str]:
    """Notas numeradas de la tabla: {"1": "texto", ...}. «*) Datos avance» se trata aparte (estado del dato)."""
    out = {}
    for trozo in (px.get("NOTE") or "").split("#"):
        t = re.sub(r"\s+", " ", trozo).strip()
        m = re.match(r"\(?(\d+)\)\s*(.+)", t)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def codigo(etiqueta: str) -> str | None:
    """Código INE de una fila «13 MADRID, COMUNIDAD DE» (o de una comunidad sin código, como «NAVARRA (Comunidad Foral
    de) (4)» en 2015-16); None si la fila es una provincia."""
    et = sin_llamadas(etiqueta)
    if et[:2].isdigit():
        return et[:2]
    return territorio(et)["ine"] if et in POR_ALIAS else None


def tabla(nombre: str) -> tuple[dict, dict, dict]:
    m = ultimo_original(FUENTE_DE.get(nombre, FUENTE), nombre)
    px = leer_px(m["ruta"])
    return px, celdas_px(px), m


def dim(px: dict, empieza: str) -> str:
    for v in px["STUB"] + px["HEADING"]:
        if v.lower().startswith(empieza.lower()):
            return v
    sys.exit(f"{px.get('TITLE')}: no hay dimensión «{empieza}»")


def fila(ind, terr, periodo, valor, unidad, url, fecha, estado, sexo="total", titularidad="total", etapa="total"):
    return {"indicador_id": ind, "territorio": terr, "periodo": periodo, "titularidad": titularidad, "sexo": sexo,
            "etapa": etapa, "valor": valor, "unidad": unidad, "error_estandar": None, "estado": estado,
            "fuente_id": "mefd_educabase", "url_fuente": url, "fecha_captura": fecha}


def notas_citadas(px: dict) -> list[dict]:
    """Cada nota de la tabla con las comunidades y cursos que la citan (las que no cita nadie, generales)."""
    textos = notas_de(px)
    terr_dim = dim(px, "Comunidad")
    citas = defaultdict(lambda: {"territorios": set(), "periodos": set()})
    for etiqueta in px[f'VALUES("{terr_dim}")']:
        for n in llamadas(etiqueta):
            citas[n]["territorios"].add(territorio(etiqueta)["ine"])
    for etiqueta in px[f'VALUES("{dim(px, "periodo")}")']:
        for n in llamadas(etiqueta):
            citas[n]["periodos"].add(curso(etiqueta))
    return [{"texto": t, "territorios": sorted(citas[n]["territorios"]), "periodos": sorted(citas[n]["periodos"])}
            for n, t in sorted(textos.items(), key=lambda x: int(x[0]))]


def serie(ind: str, nombre: str, unidad: str, fijos: dict | None = None, desde: str = DESDE) -> tuple[list, dict]:
    """Filas de una tabla con dimensiones comunidad × periodo (+ sexo o titularidad, + dimensiones fijadas)."""
    px, celdas, m = tabla(nombre)
    vars_ = px["STUB"] + px["HEADING"]
    iterr, iper = vars_.index(dim(px, "Comunidad")), vars_.index(dim(px, "periodo"))
    url = URL_TABLA.format(ruta=RUTAS[nombre], fichero=nombre)
    filas = []
    for combo, valor in celdas.items():
        if valor is None:
            continue
        extra = {"sexo": "total", "titularidad": "total"}
        saltar = False
        for i, v in enumerate(vars_):
            if i in (iterr, iper):
                continue
            etiqueta = sin_llamadas(combo[i]).upper()
            if fijos and v in fijos:
                saltar |= sin_llamadas(combo[i]) != fijos[v]
            elif v.lower().startswith("sexo"):
                extra["sexo"] = SEXO[etiqueta]
            elif v.lower().startswith("titularidad"):
                extra["titularidad"] = TITULARIDAD[etiqueta]
            else:
                sys.exit(f"{nombre}: dimensión sin tratar «{v}»")
        if saltar:
            continue
        per = curso(combo[iper])
        if per < desde:
            continue
        estado = "avance" if "*" in llamadas(combo[iper]) else "definitivo"
        filas.append(fila(ind, territorio(combo[iterr])["ine"], per, valor, unidad, url, m["fecha_captura"], estado, **extra))
    return filas, px


def por_clave(filas: list[dict]) -> dict:
    return {(f["territorio"], f["periodo"], f["sexo"], f["titularidad"]): f["valor"] for f in filas}


def comprobar_cociente(nombre: str, publicado: dict, num: dict, den: dict, escala: float, tol: float, errores: list) -> dict:
    """Recalcula el dato publicado. Las diferencias se guardan (la web las enumera, sin explicarlas); solo se para si
    aparece alguna nueva en el último curso, que suele indicar un cambio de formato o un error de lectura."""
    n, difs = 0, []
    for k, v in publicado.items():
        if k in num and k in den and den[k]:
            n += 1
            calc = num[k] / den[k] * escala
            if abs(calc - v) > tol:
                difs.append({"territorio": k[0], "periodo": k[1], "titularidad": k[3], "publicado": v, "calculado": round(calc, 3)})
    # Solo se para si en el último curso aparece una diferencia nueva (comunidad y titularidad que no la tenían en el
    # curso anterior): las que se repiten curso a curso son una forma de publicar de la fuente, no un error de lectura.
    cursos = sorted({k[1] for k in publicado})
    ultimo, anterior = cursos[-1], cursos[-2]
    antes = {(d["territorio"], d["titularidad"]) for d in difs if d["periodo"] == anterior}
    errores += [f"{nombre} {d}" for d in difs if d["periodo"] == ultimo and (d["territorio"], d["titularidad"]) not in antes]
    return {"pares_comparados": n, "coinciden": n - len(difs), "tolerancia": tol, "diferencias": sorted(difs, key=lambda d: (d["periodo"], d["territorio"]))}


def titularidad_alumnado(errores: list) -> tuple[list, dict]:
    """% del alumnado en pública, concertada y privada no concertada, de los ficheros todas_01 de cada curso."""
    serie_tit, _ = serie("x", "alumnado_1_01.px", "num", desde="2011-12")
    oficial = por_clave(serie_tit)
    pct_pub, _ = serie("x", "general_01.px", "pct", desde="2011-12")
    pct_pub = por_clave(pct_pub)
    filas, notas, comprobados = [], [], 0
    manifest = [m for m in __import__("json").loads((Path(__file__).parent.parent / "datos-originales/manifest.json").read_text(encoding="utf-8"))
                if m["fuente"] == FUENTE and m["fichero"].split("/")[-1].startswith("todas_01_")]
    for nombre in sorted({Path(m["fichero"]).name for m in manifest}):
        px, celdas, m = tabla(nombre)
        a = re.search(r"(\d{4})-(\d{4})", nombre)
        per = f"{a.group(1)}-{a.group(2)[2:]}"
        url = f"https://estadisticas.educacion.gob.es/EducaJaxiPx/Tabla.htm?path=/no-universitaria/alumnado/matriculado/{a.group(1)}-{a.group(2)}-rd/gen-todas/l0/&file=todas_01.px"
        terr_dim = dim(px, "Comunidad")
        recuento = defaultdict(dict)
        for (tit, sexo, terr, ens), v in celdas.items():
            if sexo != "AMBOS SEXOS" or ens != "TOTAL":
                continue
            cod = codigo(terr)
            if cod is None:
                continue  # provincia
            recuento[cod][TITULARIDAD[tit.upper()]] = v or 0
        for n, texto in notas_de(px).items():
            cita = [t for t in px[f'VALUES("{terr_dim}")'] if n in llamadas(t)]
            if cita:
                notas.append({"texto": texto, "territorios": [codigo(c) for c in cita], "periodos": [per]})
        if len(recuento) != 20:
            errores.append(f"{nombre}: {len(recuento)} territorios en lugar de 20")
        for cod, r in recuento.items():
            if r["publica"] + r["privada"] != r["total"] or r["concertada"] + r["privada_no_concertada"] != r["privada"]:
                errores.append(f"{nombre} {cod}: las partes no suman el total ({r})")
            for t in ("total", "publica", "privada"):
                ref = oficial.get((cod, per, "total", t))
                if ref is not None:
                    comprobados += 1
                    if ref != r[t]:
                        errores.append(f"{nombre} {cod} {t}: {r[t]} frente a {ref} en alumnado_1_01")
            pub = pct_pub.get((cod, per, "total", "total"))
            if pub is not None and abs(r["publica"] / r["total"] * 100 - pub) > 0.051:
                errores.append(f"{nombre} {cod}: % en pública {r['publica'] / r['total'] * 100:.2f} frente a {pub} publicado")
            for t in ("publica", "concertada", "privada_no_concertada"):
                filas.append(fila("alumnado_titularidad", cod, per, round(r[t] / r["total"] * 100, 4), "pct", url, m["fecha_captura"],
                                  "definitivo", titularidad=t))
        for t in ("total", "publica", "concertada", "privada_no_concertada"):
            suma = sum(r[t] for c, r in recuento.items() if c != "00")
            if suma != recuento["00"][t]:
                errores.append(f"{nombre} {t}: suma de comunidades {suma} frente a España {recuento['00'][t]}")
    return filas, {"pares_comparados": comprobados, "notas": notas}


def guardar(ind: str, filas: list[dict], notas: list[dict], comprobacion: dict) -> None:
    periodos = sorted({f["periodo"] for f in filas})
    escribir_json(f"observaciones/{ind}.json", {
        "indicador_id": ind, "periodos": periodos,
        "notas_fuente": [n["texto"] for n in notas], "notas": notas,
        "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
        "comprobacion": comprobacion,
        "filas": sorted(filas, key=lambda f: (f["territorio"], f["etapa"], f["sexo"], f["titularidad"], f["periodo"])),
    })
    print(f"{ind}: {len(filas)} filas, {periodos[0]} a {periodos[-1]}; {comprobacion}")


def main() -> None:
    errores: list[str] = []

    filas, comp = titularidad_alumnado(errores)
    notas = comp.pop("notas")
    guardar("alumnado_titularidad", filas, notas, {**comp, "descripcion": "partes = total, suma de comunidades = España, recuentos = serie alumnado_1_01, % en pública = general_01"})

    # 0-2 años: desde 2012-13, el curso desde el que la tabla usa la población revisada del INE (su nota 3). Antes hay
    # cambios de criterio (nota 2, Navarra) y cursos sin dato en varias comunidades.
    for ind, nombre, unidad, fijos, desde in [
        ("escolarizacion_0_2", "escolar_05.px", "pct", None, "2012-13"),
        ("idoneidad_15", "idoneidad_05.px", "pct", None, DESDE),
        ("repeticion_eso", "repetidores_03.px", "pct", {"Curso": "TODOS LOS CURSOS"}, DESDE),
    ]:
        filas, px = serie(ind, nombre, unidad, fijos, desde)
        if ind == "escolarizacion_0_2":
            filas = [f for f in filas if f["sexo"] == "total"]  # el avance no trae el desglose por sexo
        if ind == "repeticion_eso":
            filas = [f for f in filas if f["titularidad"] != "privada"]  # concertada y no concertada van por separado
        guardar(ind, filas, notas_citadas(px), {"pares_comparados": 0, "descripcion": "dato publicado tal cual"})

    # Alumnos por profesor: publicado = alumnado / profesorado
    filas, px = serie("alumnos_profesor", "series07.px", "ratio")
    alumnos = por_clave(serie("x", "alumnado_1_01.px", "num")[0])
    profes = por_clave(serie("x", "series03.px", "num")[0])
    c = comprobar_cociente("alumnos por profesor", por_clave(filas), alumnos, profes, 1, 0.051, errores)
    guardar("alumnos_profesor", filas, notas_citadas(px), {**c, "descripcion": "publicado = alumnado (alumnado_1_01) / profesorado (series03)"})

    # % de alumnado extranjero: publicado = extranjeros / alumnado
    filas, px = serie("alumnado_extranjero", "extran_04.px", "pct")
    extr = por_clave(serie("x", "extran_02.px", "num")[0])
    c = comprobar_cociente("% extranjero", por_clave(filas), extr, alumnos, 100, 0.051, errores)
    guardar("alumnado_extranjero", filas, notas_citadas(px), {**c, "descripcion": "publicado = extranjeros (extran_02) / alumnado (alumnado_1_01)"})

    # Alumnos por unidad (grupo) en cada etapa, desde 2005-06 (primer curso común a todas las etapas). Comprobación:
    # en Primaria y ESO, alumnado / unidades = número medio publicado (las demás etapas no tienen las dos series).
    filas, notas, comps = [], [], {}
    for etapa, nombre in ETAPAS_UNIDAD.items():
        fe, px = serie("alumnos_unidad", nombre, "ratio", desde="2005-06")
        filas += [{**f, "etapa": etapa} for f in fe]
        notas += [{**n, "etapa": etapa} for n in notas_citadas(px)]
    for etapa, alum, unid in [("primaria", "alumnado_3_01.px", "series_1_04.px"), ("eso", "alumnado_4_01.px", "series_1_06.px")]:
        pub = por_clave([f for f in filas if f["etapa"] == etapa])
        comps[etapa] = comprobar_cociente(f"alumnos por unidad ({etapa})", pub, por_clave(serie("x", alum, "num", desde="2005-06")[0]),
                                          por_clave(serie("x", unid, "num", desde="2005-06")[0]), 1, 0.051, errores)
    guardar("alumnos_unidad", filas, notas, {
        "pares_comparados": sum(c["pares_comparados"] for c in comps.values()),
        "coinciden": sum(c["coinciden"] for c in comps.values()), "tolerancia": 0.051,
        "diferencias": [{**d, "etapa": e} for e, c in comps.items() for d in c["diferencias"]],
        "descripcion": "publicado = alumnado / unidades (Primaria y ESO)"})

    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores[:40]) + (f"\n  … y {len(errores) - 40} más" if len(errores) > 40 else ""))


if __name__ == "__main__":
    main()
