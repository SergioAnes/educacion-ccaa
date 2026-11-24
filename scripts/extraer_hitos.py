"""Leyes y hechos que se pueden marcar en los gráficos de evolución (capa «Leyes y hechos», apagada por defecto).

Uso:  python scripts/descargar.py boe && python scripts/extraer_hitos.py

La fecha y el título salen de la ficha XML de cada norma en el BOE (datos-originales/boe/). Aquí solo se pone el
nombre corto con el que se la conoce y una comprobación de que el identificador es la norma que creemos.
Es la fecha de la norma, no la de su aplicación en las aulas (que suele ser gradual): la web lo dice.

Salida: src/data/hitos.json — no editar a mano.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

from comun import escribir_json, ultimo_original

# identificador del BOE -> (nombre corto, texto que debe aparecer en el título oficial, tipo)
NORMAS = {
    "BOE-A-1990-24172": ("LOGSE", "Ley Orgánica 1/1990", "ley"),
    "BOE-A-2006-7899": ("LOE", "Ley Orgánica 2/2006", "ley"),
    "BOE-A-2012-5337": ("RDL 14/2012 (gasto educativo)", "Real Decreto-ley 14/2012", "gasto"),
    "BOE-A-2013-12886": ("LOMCE", "Ley Orgánica 8/2013", "ley"),
    "BOE-A-2020-3692": ("COVID: estado de alarma", "Real Decreto 463/2020", "covid"),
    "BOE-A-2020-17264": ("LOMLOE", "Ley Orgánica 3/2020", "ley"),
    "BOE-A-2022-5139": ("Ley de FP", "Ley Orgánica 3/2022", "ley"),
    "BOE-A-2023-7500": ("LOSU (universidades)", "Ley Orgánica 2/2023", "ley"),
}


def main() -> None:
    hitos = []
    for ident, (corto, esperado, tipo) in NORMAS.items():
        m = ultimo_original("boe", f"{ident}.xml")
        meta = ET.parse(m["ruta"]).getroot().find("metadatos")
        titulo = meta.findtext("titulo").strip()
        fecha = meta.findtext("fecha_disposicion")
        if meta.findtext("identificador") != ident or esperado not in titulo:
            sys.exit(f"{ident}: el BOE dice «{titulo}», no «{esperado}»")
        hitos.append({
            "id": ident, "corto": corto, "tipo": tipo, "titulo": titulo,
            "fecha": f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}", "anio": int(fecha[:4]),
            "url": f"https://www.boe.es/buscar/act.php?id={ident}",
            "fecha_captura": m["fecha_captura"],
        })
    hitos.sort(key=lambda h: h["fecha"])
    ruta = escribir_json("hitos.json", hitos)
    print(f"{ruta.name}: {[(h['corto'], h['fecha']) for h in hitos]}")


if __name__ == "__main__":
    main()
