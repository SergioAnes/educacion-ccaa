"""Descarga los ficheros originales de cada fuente a datos-originales/<fuente>/<AAAA-MM-DD>/ y los apunta
en datos-originales/manifest.json (URL de origen, fecha de captura, tamaño y sha256).

Uso:
    python scripts/descargar.py                # todas las fuentes
    python scripts/descargar.py abandono boe   # solo esas

Si el fichero descargado es idéntico (mismo sha256) al último que ya hay de esa fuente, no se guarda otra copia:
así el manifest solo crece cuando la fuente cambia de verdad. Los ficheros de datos-originales nunca se editan.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGINALES = RAIZ / "datos-originales"
MANIFEST = ORIGINALES / "manifest.json"

EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
# Servicio XML de documentos del BOE: cubre también las normas derogadas (la API de legislación consolidada, no)
BOE = "https://www.boe.es/diario_boe/xml.php?id="
PX = "https://estadisticas.educacion.gob.es/EducaJaxiPx/files/_px/es/px"

# Normas que se marcan en los gráficos de evolución (capa «Leyes y hechos»). Solo el identificador del BOE:
# la fecha y el título se leen de la propia ficha del BOE.
NORMAS_BOE = [
    "BOE-A-1990-24172",  # LOGSE
    "BOE-A-2006-7899",   # LOE
    "BOE-A-2012-5337",   # Real Decreto-ley 14/2012 (gasto público en el ámbito educativo)
    "BOE-A-2013-12886",  # LOMCE
    "BOE-A-2020-3692",   # Real Decreto 463/2020 (estado de alarma)
    "BOE-A-2020-17264",  # LOMLOE
    "BOE-A-2022-5139",   # Ley Orgánica 3/2022 de Formación Profesional
    "BOE-A-2023-7500",   # LOSU
]

# fuente -> lista de (nombre del fichero, URL)
FUENTES: dict[str, list[tuple[str, str]]] = {
    # Ministerio de Educación, Formación Profesional y Deportes: explotación de las variables educativas de la EPA
    "abandono": [
        ("indi_01.px", "https://estadisticas.educacion.gob.es/EducaJaxiPx/files/_px/es/px/laborales/epa/indi/l0/indi_01.px"),
        # Eurostat: España y UE-27 (edat_lfse_14) y regiones NUTS 2 (edat_lfse_16), para comprobar y para la UE
        ("edat_lfse_14.json", f"{EUROSTAT}/edat_lfse_14?format=JSON&lang=EN&geo=EU27_2020&geo=ES&sex=T&sex=M&sex=F&wstatus=POP&age=Y18-24&unit=PC"),
        ("edat_lfse_16.json", f"{EUROSTAT}/edat_lfse_16?format=JSON&lang=EN&sex=T&sex=M&sex=F&age=Y18-24&unit=PC&geoLevel=nuts2"),
    ],
    "boe": [(f"{i}.xml", f"{BOE}{i}") for i in NORMAS_BOE],
    # EDUCAbase: Estadística de las Enseñanzas no universitarias (alumnado y profesorado), series por comunidad
    "educabase": [(Path(r).name, f"{PX}/{r}") for r in [
        "no-universitaria/alumnado/matriculado/series/AlumnadoGen/l0/alumnado_1_01.px",   # alumnado por titularidad
        "no-universitaria/alumnado/matriculado/series/gen-porcen-gen/l0/general_01.px",   # % en centros públicos
        "no-universitaria/alumnado/matriculado/series/gen-escolar/l0/escolar_05.px",      # escolarización 0-2 años
        "no-universitaria/alumnado/matriculado/series/gen-idoneidad/l0/idoneidad_05.px",  # idoneidad a los 15 años
        "no-universitaria/alumnado/matriculado/series/gen-repetidores/l0/repetidores_03.px",  # repetición en ESO
        "no-universitaria/alumnado/matriculado/series/extranjeros/l0/extran_02.px",       # alumnado extranjero
        "no-universitaria/alumnado/matriculado/series/extranjeros/l0/extran_04.px",       # % de alumnado extranjero
        "no-universitaria/profesorado/estadistica/series/l0/series03.px",                 # profesorado por titularidad
        "no-universitaria/profesorado/estadistica/series/l0/series07.px",                 # alumnos por profesor
    ]] + [
        # Alumnado por titularidad/financiación (pública, concertada, privada no concertada): un fichero por curso.
        # Antes de 2011-12 la tabla no está en este formato.
        (f"todas_01_{a}-{a + 1}.px", f"{PX}/no-universitaria/alumnado/matriculado/{a}-{a + 1}-rd/gen-todas/l0/todas_01.px")
        for a in range(2011, 2025)
    ],
    # EDUCAbase: número medio de alumnado por unidad (grupo) por etapa, y unidades y alumnado para comprobarlo
    "unidades": [(Path(r).name, f"{PX}/{r}") for r in [
        *[f"no-universitaria/centros/centrosyunid/series/unidades/l0/series_2_{n}.px" for n in ("02", "03", "04", "06", "07", "08", "09", "10")],
        "no-universitaria/centros/centrosyunid/series/unidades/l0/series_1_04.px",   # unidades de Primaria
        "no-universitaria/centros/centrosyunid/series/unidades/l0/series_1_06.px",   # unidades de ESO
        "no-universitaria/alumnado/matriculado/series/AlumnadoGen/l0/alumnado_3_01.px",  # alumnado de Primaria
        "no-universitaria/alumnado/matriculado/series/AlumnadoGen/l0/alumnado_4_01.px",  # alumnado de ESO
    ]],
    # «Las cifras de la educación en España», edición 2026 (curso 2023-24): tablas en Excel por capítulo
    "cifras": [
        ("c2.xlsx", "https://www.educacionfpydeportes.gob.es/dam/jcr:e9366cb1-7e92-438b-8a65-36bc8d8a0800/c2.xlsx"),  # C2.9 graduación
    ],
    # INEE: tablas del informe español de PISA 2025 (Excel dentro de un RAR)
    "pisa": [("tablas-informe-pisa-2025.rar", "https://www.educacionfpydeportes.gob.es/dam/jcr:4f7056b5-02d7-4e6d-a454-2caa3e04893f/tablas-informe-pisa-2025.rar")],
}


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def leer_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def descargar(url: str) -> bytes:
    # Sin datos personales en la petición: solo un nombre genérico de cliente.
    pet = urllib.request.Request(url, headers={"User-Agent": "educacion-ccaa/1.0 (datos abiertos)", "Accept": "application/json, */*"})
    with urllib.request.urlopen(pet, timeout=120) as r:
        if r.status != 200:
            raise RuntimeError(f"{url}: HTTP {r.status}")
        return r.read()


def main(fuentes: list[str]) -> None:
    manifest = leer_manifest()
    hoy = dt.date.today().isoformat()
    fallos: list[str] = []
    for fuente in fuentes:
        for nombre, url in FUENTES[fuente]:
            try:
                contenido = descargar(url)
            except Exception as e:  # una fuente caída no impide guardar las demás
                fallos.append(f"{fuente}/{nombre}: {e}")
                print(f"{fuente}/{nombre}: ERROR {e}")
                continue
            huella = hashlib.sha256(contenido).hexdigest()
            previos = [m for m in manifest if m["fuente"] == fuente and Path(m["fichero"]).name == nombre]
            if previos and max(previos, key=lambda m: m["fecha_captura"])["sha256"] == huella:
                print(f"{fuente}/{nombre}: sin cambios")
                continue
            destino = ORIGINALES / fuente / hoy / nombre
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(contenido)
            manifest = [m for m in manifest if m["fichero"] != destino.relative_to(ORIGINALES).as_posix()]
            manifest.append({
                "fuente": fuente,
                "fichero": destino.relative_to(ORIGINALES).as_posix(),
                "url": url,
                "fecha_captura": hoy,
                "bytes": len(contenido),
                "sha256": huella,
            })
            print(f"{fuente}/{nombre}: guardado ({len(contenido):,} bytes)")
    manifest.sort(key=lambda m: (m["fuente"], m["fichero"]))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(FUENTES)
    desconocidas = [f for f in pedidas if f not in FUENTES]
    if desconocidas:
        sys.exit(f"Fuentes desconocidas: {desconocidas}. Disponibles: {list(FUENTES)}")
    main(pedidas)
