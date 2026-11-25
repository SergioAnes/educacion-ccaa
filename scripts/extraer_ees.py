"""Sueldo medio de los trabajadores por comunidad autónoma (INE, Encuesta Anual de Estructura Salarial).

Uso:  python scripts/descargar.py ees && python scripts/extraer_ees.py

Fuentes (en datos-originales/ees/, apuntadas en el manifest):
  - 28191.px: ganancia media anual por trabajador, por sexo y comunidad, 2008-…  (lo que muestra la web: ambos sexos).
  - 28213.px: coeficientes de variación de esa ganancia (es una encuesta por muestreo).
  - 36848.px: Encuesta cuatrienal de 2022, ganancia media por comunidad y tipo de jornada. Solo para comprobar
    cuánto cambia la comparación entre comunidades si se usa la media a tiempo completo (el sueldo docente que
    calcula la web es de jornada completa, y la media del INE incluye el tiempo parcial).

Comprobaciones (el script se para si alguna falla):
  - Las cifras de 2024 coinciden con la nota de prensa del INE (28/5/2026): España y las citadas en ella.
  - Están las 17 comunidades y España en todos los años; ningún coeficiente de variación pasa del 5 %.
  - Cuánto cambia la posición de cada comunidad frente a España si se usa la media a tiempo completo de 2022
    en lugar de la media total (se guarda; la web lo dice en el aviso).

Salida: src/data/observaciones/sueldo_medio.json (formato largo, esquema común) — no editar a mano.
"""
from __future__ import annotations

import sys

from comun import celdas_px, escribir_json, leer_px, territorio, ultimo_original

IND = "sueldo_medio"
URL = "https://www.ine.es/jaxiT3/Tabla.htm?t=28191"
# Nota de prensa de la Encuesta Anual de Estructura Salarial 2024 (INE, 28/5/2026)
NOTA_PRENSA_2024 = {"00": 29540.26, "16": 35170.28, "13": 34410.01, "15": 32605.28, "11": 24979.44}
CV_MAXIMO = 5.0


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    m = ultimo_original("ees", "28191.px")
    px = leer_px(m["ruta"])
    if px["STUB"] != ["Sexo", "Comunidades autónomas", "Periodo"] or px["HEADING"] != ["Medidas y percentiles"]:
        sys.exit(f"28191.px ha cambiado de estructura: STUB={px['STUB']} HEADING={px['HEADING']}")
    celdas = celdas_px(px)
    cv = celdas_px(leer_px(ultimo_original("ees", "28213.px")["ruta"]))
    filas, errores, cv_max = [], [], (0.0, None)
    anios = sorted(px['VALUES("Periodo")'])
    for (sexo, ccaa, anio, medida), valor in celdas.items():
        if sexo != "Ambos sexos" or medida != "Media":
            continue
        t = territorio(ccaa)
        if valor is None:
            errores.append(f"{ccaa} {anio}: sin dato")
            continue
        c = cv.get((ccaa, anio, "Ambos sexos"))
        if c is None or c > CV_MAXIMO:
            errores.append(f"{ccaa} {anio}: coeficiente de variación {c}")
        elif c > cv_max[0]:
            cv_max = (c, f"{t['nombre']} {anio}")
        filas.append({"indicador_id": IND, "territorio": t["ine"], "periodo": anio, "titularidad": "total", "sexo": "total",
                      "etapa": "total", "valor": round(valor, 2), "unidad": "eur", "error_estandar": None, "estado": "definitivo",
                      "fuente_id": "ine_ees", "url_fuente": URL, "fecha_captura": m["fecha_captura"]})
    for ine, v in NOTA_PRENSA_2024.items():
        dato = next((f["valor"] for f in filas if f["territorio"] == ine and f["periodo"] == "2024"), None)
        if dato is None or abs(dato - v) > 0.005:
            errores.append(f"{ine} 2024: tabla {dato}, nota de prensa {v}")
    for anio in anios:
        n = sum(1 for f in filas if f["periodo"] == anio)
        if n != 18:
            errores.append(f"{anio}: {n} territorios (deberían ser 18: España y las 17)")
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))

    # Efecto del tiempo parcial: posición frente a España con la media total de 2024 y con la de tiempo completo de 2022
    j = celdas_px(leer_px(ultimo_original("ees", "36848.px")["ruta"]))
    tc_es = j[("Total Nacional", "Ambos sexos", "Jornada a tiempo completo", "Media")]
    v24 = {f["territorio"]: f["valor"] for f in filas if f["periodo"] == "2024"}
    efecto = []
    for (ccaa, sexo, jornada, medida), v in j.items():
        # Ceuta y Melilla vienen juntas en la cuatrienal y no están en la anual
        if sexo != "Ambos sexos" or jornada != "Jornada a tiempo completo" or medida != "Media" or ccaa in ("Total Nacional", "Ceuta y Melilla"):
            continue
        ine = territorio(ccaa)["ine"]
        rel24 = 100 * (v24[ine] / v24["00"] - 1)
        rel_tc = 100 * (v / tc_es - 1)
        efecto.append({"territorio": ine, "frente_espana_2024_total": round(rel24, 1), "frente_espana_2022_tiempo_completo": round(rel_tc, 1)})
    dif_max = max(efecto, key=lambda e: abs(e["frente_espana_2024_total"] - e["frente_espana_2022_tiempo_completo"]))

    salida = {
        "indicador_id": IND,
        "periodos": anios,
        "notas_fuente": [px["NOTE"]] if px.get("NOTE") else [],
        "muestra_pequena": [], "rupturas": [], "definicion_difiere_es": [],
        "comprobacion": {
            "pares_comparados": len(NOTA_PRENSA_2024),
            "descripcion": "cifras de 2024 iguales a la nota de prensa del INE; coeficientes de variación por debajo del 5 %",
            "cv_maximo": {"valor": cv_max[0], "donde": cv_max[1]},
            "efecto_tiempo_parcial": efecto,
            "efecto_tiempo_parcial_maximo_puntos": round(abs(dif_max["frente_espana_2024_total"] - dif_max["frente_espana_2022_tiempo_completo"]), 1),
        },
        "filas": sorted(filas, key=lambda f: (f["territorio"], f["periodo"])),
    }
    ruta = escribir_json("observaciones/sueldo_medio.json", salida)
    print(f"{ruta.name}: {len(filas)} filas, {anios[0]}-{anios[-1]}; coeficiente de variación máximo {cv_max[0]} % ({cv_max[1]}); "
          f"usar la media a tiempo completo de 2022 mueve la posición frente a España como mucho "
          f"{salida['comprobacion']['efecto_tiempo_parcial_maximo_puntos']} puntos ({dif_max['territorio']})")


if __name__ == "__main__":
    main()
