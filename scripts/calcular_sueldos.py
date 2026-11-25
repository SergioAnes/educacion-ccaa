"""Sueldos del profesorado por comunidad: calcula el sueldo bruto anual de los casos tipo a partir de
src/data/sueldos/normas.json (escrito a mano, con la fuente de cada importe) y comprueba su coherencia.

Uso:  python scripts/calcular_sueldos.py

Salida: src/data/sueldos/calculo.json (todavía no se usa en la web).

Cálculo (por cuerpo, funcionario que empieza):
  12 mensualidades de sueldo + complemento de destino + complemento específico
  + 2 pagas extra de sueldo de paga extra + una mensualidad de complemento de destino
  + N pagas adicionales de complemento específico (N = 2 si la norma lo dice)
  + otros importes anuales de la comunidad (recurrentes o pagos únicos del año, que se marcan aparte).

Comprobaciones (si falla alguna, el script se detiene):
  - cada importe tiene fuente, la fuente existe y, si tiene original, está en el manifest con el mismo sha256;
  - sueldo, sueldo de paga extra y complemento de destino coinciden con los estatales (iguales en toda España);
  - si la comunidad publica el total mensual, sueldo + destino + específico lo da (al céntimo);
  - las horas lectivas tienen fuente y definición;
  - los supuestos (comprobacion = «supuesto») quedan listados en la salida, para que la web los diga.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NORMAS = RAIZ / "src/data/sueldos/normas.json"
SALIDA = RAIZ / "src/data/sueldos/calculo.json"
MANIFEST = RAIZ / "datos-originales/manifest.json"
CUERPOS = ("maestros", "secundaria")


def main() -> None:
    d = json.loads(NORMAS.read_text(encoding="utf-8"))
    errores: list[str] = []
    fuentes = d["fuentes"]
    manifest = {m["fichero"]: m for m in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    # Fuentes: enlace y, si hay original, que esté guardado y sin cambios
    for fid, f in fuentes.items():
        if not f.get("url", "").startswith("https://"):
            errores.append(f"fuente {fid}: sin enlace https")
        if f.get("original"):
            m = manifest.get(f["original"])
            ruta = RAIZ / "datos-originales" / f["original"]
            if not m:
                errores.append(f"fuente {fid}: {f['original']} no está en el manifest")
            elif ruta.exists() and hashlib.sha256(ruta.read_bytes()).hexdigest() != m["sha256"]:
                errores.append(f"fuente {fid}: {f['original']} no coincide con el sha256 del manifest")

    def dato(ccaa: str, cuerpo: str, campo: str, x: dict) -> float:
        if not isinstance(x, dict) or "valor" not in x:
            errores.append(f"{ccaa} {cuerpo} {campo}: sin valor")
            return 0.0
        if x.get("fuente") not in fuentes:
            errores.append(f"{ccaa} {cuerpo} {campo}: fuente desconocida {x.get('fuente')!r}")
        if not x.get("donde"):
            errores.append(f"{ccaa} {cuerpo} {campo}: falta dónde está en la fuente")
        return float(x["valor"])

    est = d["estatal"]
    salida, supuestos = {}, []
    for ine, c in d["comunidades"].items():
        if c.get("estado") != "analizada":
            continue
        res = {"nombre": c["nombre"], "cuerpos": {}, "avisos": c.get("avisos", [])}
        for cuerpo in CUERPOS:
            x = c["cuerpos"][cuerpo]
            if "anual_propio" in x:
                # Régimen retributivo propio (Navarra): no hay sueldo/destino/específico estatales; importes anuales con fuente
                comps = {}
                for comp in x["anual_propio"]:
                    comps[comp["concepto"]] = round(dato(ine, cuerpo, comp["concepto"], comp), 2)
                    if comp.get("comprobacion") in ("supuesto", "calculo"):
                        supuestos.append(f"{c['nombre']}, {cuerpo}: {comp['concepto']} ({comp.get('nota', comp.get('donde', ''))})")
                h = x.get("horas_lectivas", {})
                horas = dato(ine, cuerpo, "horas_lectivas", h)
                if not h.get("definicion"):
                    errores.append(f"{c['nombre']} {cuerpo}: horas lectivas sin definición")
                total = round(sum(comps.values()), 2)
                res["cuerpos"][cuerpo] = {"bruto_anual": total, "componentes": comps, "otros": [], "regimen_propio": True,
                                          "horas_lectivas": horas, "horas_definicion": h.get("definicion"),
                                          "euros_por_hora_semanal": round(total / horas, 2) if horas else None}
                continue
            g, nivel = x["grupo"], x["nivel_destino"]
            sueldo = dato(ine, cuerpo, "sueldo_mensual", x["sueldo_mensual"])
            extra = dato(ine, cuerpo, "sueldo_paga_extra", x["sueldo_paga_extra"])
            destino = dato(ine, cuerpo, "destino_mensual", x["destino_mensual"])
            especifico = dato(ine, cuerpo, "especifico_mensual", x["especifico_mensual"])
            n_adic = int(dato(ine, cuerpo, "especifico_pagas_adicionales", x["especifico_pagas_adicionales"]))
            if x["especifico_mensual"].get("comprobacion") in ("supuesto", "calculo"):
                supuestos.append(f"{c['nombre']}, {cuerpo}: complemento específico ({x['especifico_mensual'].get('nota', '')})")
            if x["especifico_pagas_adicionales"].get("comprobacion") in ("supuesto", "calculo"):
                supuestos.append(f"{c['nombre']}, {cuerpo}: pagas adicionales del específico ({x['especifico_pagas_adicionales'].get('nota', '')})")
            # Partes estatales
            destino_propio = bool(x["destino_mensual"].get("propio"))
            if destino_propio and not x["destino_mensual"].get("nota"):
                errores.append(f"{c['nombre']} {cuerpo}: complemento de destino propio sin explicación")
            for campo, v, ref in (("sueldo", sueldo, est["sueldo_mensual"][g]), ("sueldo de paga extra", extra, est["sueldo_paga_extra"][g]),
                                  (f"destino nivel {nivel}", destino, None if destino_propio else est["destino_mensual"][nivel])):
                if ref is not None and abs(v - ref) > 0.005:
                    errores.append(f"{c['nombre']} {cuerpo}: {campo} {v} distinto del estatal {ref}")
            tot_pub = c.get("totales_mensuales_publicados", {}).get(cuerpo)
            if isinstance(tot_pub, dict):  # total publicado que ya incluye una subida posterior («mas»)
                if tot_pub.get("fuente") not in fuentes:
                    errores.append(f"{c['nombre']} {cuerpo}: total publicado sin fuente")
                mas, tot_pub = tot_pub.get("mas", 0.0), tot_pub["valor"]
            else:
                mas = 0.0
            if tot_pub is not None and abs(sueldo + destino + especifico + mas - tot_pub) > 0.005:
                errores.append(f"{c['nombre']} {cuerpo}: {sueldo} + {destino} + {especifico} + {mas} no da el total publicado {tot_pub}")
            anual_pub = c.get("totales_anuales_publicados", {}).get(cuerpo, {})
            for campo, mensual in (("destino", destino), ("especifico", especifico)):
                if campo in anual_pub and abs(14 * mensual - anual_pub[campo]) > 0.05:
                    errores.append(f"{c['nombre']} {cuerpo}: 14 × {campo} {mensual} no da el anual publicado {anual_pub[campo]}")
            otros = x.get("otros_anuales", [])
            for o in otros:
                if o.get("comprobacion") in ("supuesto", "calculo"):
                    supuestos.append(f"{c['nombre']}, {cuerpo}: {o.get('concepto')} ({o.get('donde', '')})")
                if o.get("fuente") not in fuentes or not o.get("donde") or o.get("tipo") not in ("recurrente", "pago_unico_2026"):
                    errores.append(f"{c['nombre']} {cuerpo}: otro importe mal descrito: {o.get('concepto')}")
            h = x.get("horas_lectivas", {})
            horas = dato(ine, cuerpo, "horas_lectivas", h)
            if not h.get("definicion"):
                errores.append(f"{c['nombre']} {cuerpo}: horas lectivas sin definición")
            componentes = {
                "mensualidades": round(12 * (sueldo + destino + especifico), 2),
                "pagas_extra": round(2 * (extra + destino), 2),
                # Si la norma fija otro importe para cada paga adicional (Aragón: un 90 % de la mensualidad), se usa ese
                "pagas_adicionales_especifico": round(n_adic * float(x["especifico_pagas_adicionales"].get("importe_cada_una", especifico)), 2),
                "otros_recurrentes": round(sum(o["importe"] for o in otros if o["tipo"] == "recurrente"), 2),
                "pagos_unicos_del_anio": round(sum(o["importe"] for o in otros if o["tipo"] == "pago_unico_2026"), 2),
            }
            total = round(sum(componentes.values()), 2)
            # Total anual publicado por la comunidad (sin los «otros» importes): debe coincidir con el cálculo
            tot_anual = anual_pub.get("total_sin_otros")
            if tot_anual is not None:
                sin_otros = componentes["mensualidades"] + componentes["pagas_extra"] + componentes["pagas_adicionales_especifico"]
                if abs(sin_otros - tot_anual) > 0.1:
                    errores.append(f"{c['nombre']} {cuerpo}: el cálculo da {sin_otros:.2f} y el total anual publicado es {tot_anual}")
            res["cuerpos"][cuerpo] = {
                "bruto_anual": total, "componentes": componentes, "otros": otros,
                "horas_lectivas": horas, "horas_definicion": h.get("definicion"),
                "euros_por_hora_semanal": round(total / horas, 2) if horas else None,
            }
        salida[ine] = res
    if errores:
        sys.exit("Comprobaciones fallidas:\n  " + "\n  ".join(errores))
    SALIDA.write_text(json.dumps({"anio": d["anio"], "casos": d["casos"], "supuestos": supuestos, "comunidades": salida},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for ine, r in salida.items():
        for cuerpo, x in r["cuerpos"].items():
            print(f"{r['nombre']:10} {cuerpo:10} {x['bruto_anual']:10.2f} € al año ({x['horas_lectivas']:.0f} h de clase; "
                  f"{x['euros_por_hora_semanal']:.0f} € por hora semanal)  {x['componentes']}")
    print(f"Supuestos sin norma explícita o importes calculados: {len(supuestos)}")
    for s in supuestos:
        print("  -", s[:160])


if __name__ == "__main__":
    main()
