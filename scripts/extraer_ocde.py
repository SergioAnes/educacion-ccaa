"""España frente a la OCDE: sueldos legales del profesorado, su evolución y las horas de clase al año.

Uso:  python scripts/descargar.py ocde && python scripts/extraer_ocde.py

Fuente (en datos-originales/ocde/, apuntadas en el manifest): OCDE, Education at a Glance, Data Explorer (SDMX):
  - eag-sueldos-legales.csv (DSD_EAG_SAL_STA@DF_TCH): sueldo legal anual en 2025, en dólares en paridad de poder
    adquisitivo (para comparar países) y en moneda nacional; al empezar, con 15 años y en el máximo de la escala;
    titulación más habitual.
  - eag-evolucion-sueldos.csv (DSD_EAG_SAL_TREND@DF_TCH_STA): índice del sueldo a precios constantes (2015 = 100).
  - eag-tiempo-ensenanza.csv (DSD_EAG_WT@DF_STA_TCH): horas de clase y de trabajo al año que fija la norma.
España es una sola cifra (media de las comunidades que calcula el Ministerio para la OCDE): no hay datos por comunidad.
Maestros = primaria (CINE 1); profesorado de secundaria = primera etapa de secundaria general (CINE 24, la ESO).

Comprobaciones (el script se para si alguna falla):
  - En España, Infantil = Primaria y ESO = Bachillerato (por eso se asignan a los dos cuerpos de la web).
  - En España, la paridad (dólares ÷ euros) es la misma en todas las celdas.
  - El sueldo en euros de 2025 es el mismo en la tabla de sueldos y en la de evolución.
  - Están España, la OCDE y la UE en todas las cifras que usa la web.
Se guarda también, como contraste, la media simple de las 17 comunidades de esta web (2026) frente a la cifra de España
de la OCDE (2025).

Salida: src/data/ocde.json — no editar a mano.
"""
from __future__ import annotations

import csv
import json
import sys

from comun import DATOS, escribir_json, ultimo_original

AREAS = {"ESP": "ES", "OECD": "OCDE", "EU25": "UE"}
CUERPO = {"maestros": "ISCED11_1", "secundaria": "ISCED11_24"}
EXP = {"EXP0": "al_empezar", "EXP15": "con_15_anios", "EXPMAX": "maximo"}
URL_INFORME = "https://www.oecd.org/en/publications/education-at-a-glance-2026_b4968bbc-en/full-report/how-much-are-teachers-and-school-heads-paid_a6233c97.html"
URL_DATOS = "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_EAG_SAL_STA%40DF_TCH&df[ag]=OECD.EDU.IMEP"


def leer(nombre: str) -> tuple[list[dict], dict]:
    m = ultimo_original("ocde", nombre)
    with open(m["ruta"], encoding="utf-8-sig") as f:
        return list(csv.DictReader(f)), m


def num(x: dict) -> float | None:
    return float(x["OBS_VALUE"]) if x["OBS_VALUE"] and x["OBS_STATUS"] in ("A", "B") else None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    errores: list[str] = []
    sal, m_sal = leer("eag-sueldos-legales.csv")
    evo, _ = leer("eag-evolucion-sueldos.csv")
    tie, _ = leer("eag-tiempo-ensenanza.csv")
    anios = {x["REF_PERIOD"] for x in sal}
    if len(anios) != 1:
        errores.append(f"la tabla de sueldos trae varios años: {anios}")
    anio = anios.pop()

    def sueldo(area, nivel, exp, unidad):
        v = [num(x) for x in sal if x["REF_AREA"] == area and x["EDUCATION_LEV"] == nivel and x["PERS_EXP_LEV"] == exp
             and x["PERS_QUAL_LEV"] == "TYP" and x["UNIT_MEASURE"] == unidad]
        return v[0] if len(v) == 1 else None

    sueldos, ppa = {}, set()
    for cuerpo, nivel in CUERPO.items():
        sueldos[cuerpo] = {}
        for exp, clave in EXP.items():
            fila = {AREAS[a]: sueldo(a, nivel, exp, "USD_PPP") for a in AREAS}
            fila["ES_euros"] = sueldo("ESP", nivel, exp, "XDC")
            for k, v in fila.items():
                if v is None:
                    errores.append(f"falta {cuerpo} {exp} {k}")
            if fila["ES"] and fila["ES_euros"]:
                ppa.add(round(fila["ES"] / fila["ES_euros"], 6))
            sueldos[cuerpo][clave] = {k: round(v, 0) if v else None for k, v in fila.items()}
        # El nivel que no se muestra debe dar lo mismo en España (Infantil = Primaria; ESO = Bachillerato)
        gemelo = {"ISCED11_1": "ISCED11_02", "ISCED11_24": "ISCED11_34"}[nivel]
        for exp in EXP:
            a, b = sueldo("ESP", nivel, exp, "XDC"), sueldo("ESP", gemelo, exp, "XDC")
            if a is None or b is None or abs(a - b) > 0.01:
                errores.append(f"España {nivel} y {gemelo} no coinciden en {exp}: {a} / {b}")
    if len(ppa) != 1:
        errores.append(f"la paridad de España no es la misma en todas las celdas: {sorted(ppa)}")

    # Evolución a precios constantes, 2015-último año
    evolucion = {}
    for cuerpo, nivel in CUERPO.items():
        evolucion[cuerpo] = {}
        for exp in ("EXP0", "EXP15"):
            fila = {}
            for a, k in AREAS.items():
                ix = {x["TIME_PERIOD"]: num(x) for x in evo if x["REF_AREA"] == a and x["EDUCATION_LEV"] == nivel
                      and x["PERS_EXP_LEV"] == exp and x["UNIT_MEASURE"] == "IX"}
                if ix.get("2015") != 100 or ix.get(anio) is None:
                    errores.append(f"índice {a} {cuerpo} {exp}: 2015={ix.get('2015')} {anio}={ix.get(anio)}")
                    continue
                fila[k] = round(ix[anio] - 100, 1) + 0.0  # sin «-0.0»
            evolucion[cuerpo][EXP[exp]] = fila
            eur = [num(x) for x in evo if x["REF_AREA"] == "ESP" and x["EDUCATION_LEV"] == nivel and x["PERS_EXP_LEV"] == exp
                   and x["UNIT_MEASURE"] == "XDC" and x["TIME_PERIOD"] == anio]
            if not eur or abs(eur[0] - sueldo("ESP", nivel, exp, "XDC")) > 0.01:
                errores.append(f"{cuerpo} {exp}: euros distintos en evolución ({eur}) y sueldos ({sueldo('ESP', nivel, exp, 'XDC')})")

    # Horas de clase y de trabajo al año (lo que fija la norma)
    def horas(area, nivel, medida):
        v = [num(x) for x in tie if x["REF_AREA"] == area and x["EDUCATION_LEV"] == nivel and x["MEASURE"] == medida
             and x["UNIT_MEASURE"] == "H_Y" and x["STATISTICAL_OPERATION"] == "OBS" and x["REF_PERIOD"] == anio]
        return round(v[0]) if v and v[0] is not None else None

    horas_clase = {c: {AREAS[a]: horas(a, n, "WKT_STA_TCH") for a in AREAS} for c, n in CUERPO.items()}
    horas_trabajo = {c: {AREAS[a]: horas(a, n, "WKT_STA_WKT") for a in AREAS} for c, n in CUERPO.items()}
    for c, fila in horas_clase.items():
        for k, v in fila.items():
            if v is None:
                errores.append(f"faltan horas de clase {c} {k}")
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))

    # Contraste: media simple de las 17 comunidades (esta web, 2026) frente a España en la OCDE (2025)
    contraste = {}
    for cuerpo in CUERPO:
        for ind, clave in (("sueldo_docente", "al_empezar"), ("sueldo_docente_15", "con_15_anios")):
            obs = json.loads((DATOS / "observaciones" / f"{ind}.json").read_text(encoding="utf-8"))
            vals = [f["valor"] for f in obs["filas"] if f["etapa"] == cuerpo]
            media = sum(vals) / len(vals)
            contraste[f"{cuerpo}_{clave}"] = {"media_17_web_2026": round(media), "espana_ocde_2025": sueldos[cuerpo][clave]["ES_euros"],
                                              "diferencia_pct": round(100 * (media / sueldos[cuerpo][clave]["ES_euros"] - 1), 1)}

    salida = {
        "edicion": "Education at a Glance 2026", "anio": anio, "url_informe": URL_INFORME, "url_datos": URL_DATOS,
        "fecha_captura": m_sal["fecha_captura"],
        "sueldos_ppa": sueldos, "evolucion_real_desde_2015_pct": evolucion,
        "horas_clase_anio": horas_clase, "horas_trabajo_anio": horas_trabajo,
        "comprobacion": {"paridad_espana": ppa.pop(), "contraste_con_la_web": contraste},
    }
    ruta = escribir_json("ocde.json", salida)
    print(f"{ruta.name}: año {anio}")
    for cuerpo in CUERPO:
        s = sueldos[cuerpo]
        print(f"  {cuerpo}: al empezar ES {s['al_empezar']['ES']:.0f} / OCDE {s['al_empezar']['OCDE']:.0f} / UE {s['al_empezar']['UE']:.0f} $ PPA; "
              f"15 años ES {s['con_15_anios']['ES']:.0f} / OCDE {s['con_15_anios']['OCDE']:.0f}; horas de clase {horas_clase[cuerpo]}; "
              f"evolución real {evolucion[cuerpo]}")
    for k, v in contraste.items():
        print(f"  contraste {k}: {v}")


if __name__ == "__main__":
    main()
