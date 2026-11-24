"""Abandono temprano de la educación y la formación (18-24 años), por comunidad autónoma, sexo y año.

Uso:  python scripts/descargar.py abandono && python scripts/extraer_abandono.py

Fuentes (en datos-originales/abandono/, apuntadas en el manifest):
  - indi_01.px: Ministerio de Educación (EDUCAbase), «Explotación de las variables educativas de la EPA», tabla 1.
    Es la serie que muestra la web para España y las comunidades (con Ceuta y Melilla).
  - edat_lfse_14.json: Eurostat, España y UE-27. La web usa la UE-27; España sirve para comprobar.
  - edat_lfse_16.json: Eurostat, regiones NUTS 2. Sirve para comprobar cada comunidad y para la marca «u»
    (baja fiabilidad) de cada dato.

Comprobaciones (el script se para si alguna falla):
  - Cada valor del Ministerio coincide con el de Eurostat (que publica un decimal) con una diferencia de 0,1 puntos
    como mucho. Las que pasan de 0,05 (no explicables solo por el redondeo) se guardan en la salida.
  - Cada comunidad y año del Ministerio tiene su pareja en Eurostat, salvo los datos que Eurostat no publica.

Salida: src/data/observaciones/abandono.json (formato largo, esquema común) — no editar a mano.
"""
from __future__ import annotations

import re
import sys

from comun import POR_NUTS2, celdas_px, escribir_json, leer_eurostat, leer_px, territorio, ultimo_original

IND = "abandono_temprano"
SEXO_PX = {"Ambos sexos": "total", "Hombres": "h", "Mujeres": "m"}
SEXO_EU = {"T": "total", "M": "h", "F": "m"}
URL_MEFD = "https://estadisticas.educacion.gob.es/EducaJaxiPx/Datos.htm?path=/laborales/epa/indi/l0/&file=indi_01.px"
URL_EUROSTAT = "https://ec.europa.eu/eurostat/databrowser/view/edat_lfse_14/default/table"
URL_EUROSTAT_REG = "https://ec.europa.eu/eurostat/databrowser/view/edat_lfse_16/default/table"


def fila(terr, periodo, sexo, valor, fuente_id, url, fecha, **extra):
    return {
        "indicador_id": IND, "territorio": terr, "periodo": periodo, "titularidad": "total", "sexo": sexo,
        "etapa": "total", "valor": valor, "unidad": "pct", "error_estandar": None, "estado": "definitivo",
        "fuente_id": fuente_id, "url_fuente": url, "fecha_captura": fecha, **extra,
    }


def main() -> None:
    px_m = ultimo_original("abandono", "indi_01.px")
    e14_m = ultimo_original("abandono", "edat_lfse_14.json")
    e16_m = ultimo_original("abandono", "edat_lfse_16.json")

    px = leer_px(px_m["ruta"])
    celdas = celdas_px(px)
    if px["STUB"] != ["Comunidad autónoma"] or px["HEADING"] != ["Sexo", "periodo"]:
        sys.exit(f"indi_01.px ha cambiado de estructura: STUB={px['STUB']} HEADING={px['HEADING']}")
    nota = px.get("NOTE", "")
    # Llamada «(3)» en el nombre de la comunidad = nota 3 de la tabla (muestra pequeña, fuertes errores de muestreo)
    if not re.search(r"3\)\s*Los datos deben ser tomados con precaución", nota):
        sys.exit("La nota 3 de indi_01.px ya no es la de las muestras pequeñas: revisar las llamadas (3)")
    con_llamada = {territorio(c)["ine"] for c in px['VALUES("Comunidad autónoma")'] if c.rstrip().endswith("(3)")}
    rupturas_mefd = [int(a) for a in re.findall(r"Ruptura de serie:\s*Año\s*(\d{4})", nota)]

    dims14, e14, _ = leer_eurostat(e14_m["ruta"])
    dims16, e16, _ = leer_eurostat(e16_m["ruta"])
    i14 = {k: dims14.index(k) for k in dims14}
    i16 = {k: dims16.index(k) for k in dims16}
    eu = {(c[i14["geo"]], SEXO_EU[c[i14["sex"]]], c[i14["time"]]): v for c, v in e14.items()}
    reg = {(c[i16["geo"]], SEXO_EU[c[i16["sex"]]], c[i16["time"]]): v for c, v in e16.items() if c[i16["geo"]].startswith("ES")}

    filas, errores, difs, comprobados = [], [], [], 0
    for (ccaa, sexo, anio), valor in celdas.items():
        t = territorio(ccaa)
        s = SEXO_PX[sexo]
        # Pareja en Eurostat: España en edat_lfse_14, comunidades en edat_lfse_16 (NUTS 2)
        par = eu.get(("ES", s, anio)) if t["ine"] == "00" else reg.get((t["nuts2"], s, anio))
        marca = par[1] if par else None
        if valor is not None and par and par[0] is not None:
            comprobados += 1
            dif = abs(valor - par[0])
            if dif > 0.1 + 1e-9:
                errores.append(f"{t['nombre']} {sexo} {anio}: Ministerio {valor:.4f}, Eurostat {par[0]}")
            elif dif > 0.05 + 1e-9:
                difs.append({"territorio": t["ine"], "sexo": s, "anio": anio, "mefd": round(valor, 4), "eurostat": par[0]})
        if valor is None:
            continue
        extra = {}
        if marca and "u" in marca:
            extra["baja_fiabilidad"] = True  # Eurostat: «low reliability»
        filas.append(fila(t["ine"], anio, s, round(valor, 4), "mefd_epa", URL_MEFD, px_m["fecha_captura"], **extra))
    if errores:
        sys.exit("El Ministerio y Eurostat no coinciden:\n  " + "\n  ".join(errores))

    anios = sorted({f["periodo"] for f in filas})
    # UE-27 (composición desde 2020) para los mismos años
    for (geo, s, anio), (valor, marca) in eu.items():
        if geo == "EU27_2020" and anio in anios and valor is not None:
            filas.append(fila("UE27", anio, s, valor, "eurostat", URL_EUROSTAT, e14_m["fecha_captura"], **({"marca_eurostat": marca} if marca else {})))

    # Rupturas de serie tal como las marca cada fuente (sin interpretarlas)
    rupturas = [{"territorio": "todas", "anio": a, "fuente_id": "mefd_epa", "texto": "Ruptura de serie (nota de la tabla del Ministerio)."} for a in rupturas_mefd]
    for geo, terr in (("ES", "00"), ("EU27_2020", "UE27")):
        for anio in anios:
            m = (eu.get((geo, "total", anio)) or (None, None))[1] or ""
            if "b" in m:
                rupturas.append({"territorio": terr, "anio": int(anio), "fuente_id": "eurostat",
                                 "texto": "Eurostat marca ruptura de serie" + (" y que la definición difiere (ver sus metadatos)." if "d" in m else ".")})
    desde_d = sorted(int(a) for a in anios if "d" in ((eu.get(("ES", "total", a)) or (None, None))[1] or ""))

    salida = {
        "indicador_id": IND,
        "periodos": anios,
        "notas_fuente": [n.strip() for n in re.split(r"#", nota) if n.strip()],
        "muestra_pequena": sorted(con_llamada),
        "rupturas": sorted(rupturas, key=lambda r: (r["anio"], r["territorio"])),
        "definicion_difiere_es": desde_d,  # años de España con marca «d» de Eurostat
        "comprobacion": {"pares_comparados": comprobados, "tolerancia_puntos": 0.1, "diferencias_mayores_que_redondeo": difs},
        "filas": sorted(filas, key=lambda f: (f["territorio"], f["sexo"], f["periodo"])),
    }
    ruta = escribir_json("observaciones/abandono.json", salida)
    print(f"{ruta.relative_to(ruta.parents[2])}: {len(filas)} filas, {anios[0]}-{anios[-1]}; "
          f"{comprobados} valores comprobados con Eurostat; muestra pequeña: {sorted(con_llamada)}; "
          f"rupturas: {[(r['territorio'], r['anio']) for r in salida['rupturas']]}")


if __name__ == "__main__":
    main()
