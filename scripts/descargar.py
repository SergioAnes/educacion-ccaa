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
import re
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
        "no-universitaria/alumnado/matriculado/series/gen-escolar/l0/escolar_07.px",      # escolarización a los 3 años
        "no-universitaria/alumnado/matriculado/series/gen-escolar/l0/escolar_12.px",      # a los 16 (metodología revisada)
        "no-universitaria/alumnado/matriculado/series/gen-escolar/l0/escolar_16.px",      # a los 17
        "no-universitaria/alumnado/matriculado/series/gen-escolar/l0/escolar_20.px",      # a los 18
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
    # EDUCAbase: % de alumnado con necesidades educativas especiales por titularidad/financiación (un fichero por curso)
    "nee": [(f"acnee_02_{a}-{a + 1}.px", f"{PX}/no-universitaria/alumnado/apoyo/{a}-{a + 1}/acnee/l0/acnee_02.px") for a in range(2011, 2025)],
    # «Las cifras de la educación en España», edición 2026 (curso 2023-24): tablas en Excel por capítulo
    "cifras": [
        ("c2.xlsx", "https://www.educacionfpydeportes.gob.es/dam/jcr:e9366cb1-7e92-438b-8a65-36bc8d8a0800/c2.xlsx"),  # C2.9 graduación
        ("b4.xlsx", "https://www.educacionfpydeportes.gob.es/dam/jcr:5d6ffa47-ff10-48d7-af1d-a43245a562cf/b4.xlsx"),  # B4.6 gasto por alumno
        ("b4.pdf", "https://www.educacionfpydeportes.gob.es/dam/jcr:889aecfe-3db1-4964-a3a8-5734c716234b/b4.pdf"),    # metodología de B4.6
        ("b5.xlsx", "https://www.educacionfpydeportes.gob.es/dam/jcr:5fc7ccb7-8e3e-434e-903f-f7a1970eae13/b5.xlsx"),  # B5.3-B5.5 becas
        ("b5.pdf", "https://www.educacionfpydeportes.gob.es/dam/jcr:84688174-3025-4371-87ea-cac6574c6431/b5.pdf"),    # notas de B5.5
        ("f1.xlsx", "https://www.educacionfpydeportes.gob.es/dam/jcr:3326bdd0-8638-4a23-9903-d4480db11ccb/f1.xlsx"),  # F1.9 inserción FP
        ("f1.pdf", "https://www.educacionfpydeportes.gob.es/dam/jcr:43facf9c-1248-4aef-aafd-6311b762d65e/f1.pdf"),
    ],
    # EDUCAbase: Estadística de Becas y Ayudas al estudio, tabla 2 (becarios por comunidad y administración que paga)
    "becas": [(f"todas2_{a}-{a + 1}.px", f"{PX}/economicas/becas/{a}-{a + 1}/todasense/l0/todas2.px") for a in range(2013, 2025)],
    # EDUCAbase: Estadística de inserción laboral de las personas graduadas en FP, por comunidad (1 básica, 2 media, 3 superior),
    # y su metodología
    "insercion": [(f"ccaa_{n}_01.px", f"{PX}/laborales/insercion/ccaa/l0/ccaa_{n}_01.px") for n in (1, 2, 3)] + [
        ("metodo-2025.pdf", "https://www.educacionfpydeportes.gob.es/dam/jcr:1ae997fc-346b-4b39-800c-3d8bde091367/metodo-2025.pdf"),
        ("informe-2025.pdf", "https://www.educacionfpydeportes.gob.es/dam/jcr:21b3b21d-fe39-44ad-848e-e1af5aee3061/informe-2025.pdf"),
    ],
    # Sueldos del profesorado (tablas y normas de cada comunidad; se completan a mano en src/data/sueldos/normas.json).
    # El Acuerdo GOV/88/2026 (DOGC 9651) se descargó a mano: el portal del DOGC rechaza las descargas automáticas.
    "sueldos": [
        ("md-orden-nominas-2026.pdf", "https://www.bocm.es/boletin/CM_Orden_BOCM/2026/02/09/BOCM-20260209-6.PDF"),
        ("md-instrucciones-inicio-curso-2026-27.pdf", "https://www.comunidad.madrid/docs/2026-07/instrucciones-inicio-de-curso-2026-2027.pdf?VersionId=_c5Q9Tfeyrrw4858fl2O5svnHcAVLidV"),
        ("ct-taules-docents-2026.pdf", "https://web.gencat.cat/content/dam/webgencat/documents/la-generalitat/govern-obert/publicitat-activa/servidors-p%C3%BAblics/retribucions-2026/retribucions-personal-docent-no-universitari.pdf"),
        ("ct-gov-205-2026.pdf", "https://portaldogc.gencat.cat/utilsEADOP/PDF/9719/2164754.pdf"),
        ("ct-projecte-llei-pressupostos-2026.pdf", "https://www.parlament.cat/document/bopc/442982007.pdf"),
        ("ct-doigc-personal-docent.pdf", "https://documents.espai.educacio.gencat.cat/IPCNormativa/DOIGC/ORG_Personal_docent.pdf"),
        ("vc-salarios-brutos-sept-2026.pdf", "https://ceice.gva.es/documents/162909733/164256878/Salarios+brutos+2026.pdf/416d6ef4-1505-4ce7-23e1-cfde522c2fe8"),
        ("vc-dogv-tablas-retributivas-2026.pdf", "https://dogv.gva.es/datos/2026/02/27/pdf/2026_6352_es.pdf"),
        ("vc-ley-presupuestos-2025.pdf", "https://www.boe.es/eli/es-vc/l/2025/05/30/6/dof/spa/pdf"),
        ("vc-instrucciones-secundaria-2026-27.pdf", "https://dogv.gva.es/datos/2026/07/17/pdf/2026_24443_es.pdf"),
        ("vc-instrucciones-infantil-primaria-2026-27.pdf", "https://dogv.gva.es/datos/2026/07/17/pdf/2026_24423_es.pdf"),
        ("pv-instruccion-retribuciones-sep-2026.pdf", "https://www.euskadi.eus/contenidos/informacion/langile_nominas_servicio/es_def/adjuntos/Instruccion-retribuciones_sep_2026-.pdf"),
        ("pv-decreto-252-2025-acuerdo-regulador.pdf", "https://www.euskadi.eus/contenidos/informacion/langile_nominas_servicio/es_def/adjuntos/DECRETO-252-2025-Acuerdo-regulador.pdf"),
        ("ib-retribucions-funcionari-2026.pdf", "https://www.caib.es/sites/nominadelprofessorat/ca/d/retribucions_personal_funcionari_2026/"),
        ("ib-instruccions-horaris-2026-27.pdf", "https://apps.caib.es/sites/planificacioicentres/f/513202"),
        ("cl-orden-pre-1-2026-retribuciones.pdf", "https://bocyl.jcyl.es/boletines/2026/01/05/pdf/BOCYL-D-05012026-2-2.pdf"),
        ("cl-acuerdo-2022-horario-lectivo.pdf", "https://bocyl.jcyl.es/boletines/2022/01/27/pdf/BOCYL-D-27012022-9.pdf"),
        ("ar-tablas-retribuciones-docentes-2026.xlsx", "https://www.aragon.es/documents/20127/128260047/Tablas_retribuciones_docentes_2026.xlsx/3b5db2d8-f24b-ae7e-6eaf-829018eb5115?version=1.0&download=true"),
        ("ar-acuerdo-retribuciones-20260114.pdf", "https://www.aragon.es/documents/20127/128260047/Certificado_acuerdo_GA_retribuciones_educacion_20260114.pdf/22e0bb78-ea04-d888-17f6-5ea2edd749fb?version=1.0&download=true"),
        ("ar-instrucciones-ceip-2026-27.pdf", "https://educa.aragon.es/documents/20126/6844122/CSVFV3YLJW6LZ120XFIL+Instrucciones+curso+2026-2027+para+centros+educativos._01+CEIP+2026-2027-%28Instrucciones%29+V8.pdf/f5138622-13a8-a516-6f3e-6467cbc50664"),
        ("ga-retribucions-docentes-2026.pdf", "https://ficheiros-web.xunta.gal/transparencia/retribucions/2026/funcionarios-docentes.pdf"),
        ("ga-orden-nominas-2026.html", "https://www.xunta.gal/dog/Publicados/2026/20260126/AnuncioG0597-220126-0002_es.html"),
        ("ga-resolucion-xornada-2026-27.pdf", "https://www.edu.xunta.gal/portal/sites/web/files/resolucion_instrucions_xornada_de_traballo_docente_2026_2027_sin.pdf"),
        ("as-bopa-retribuciones-2026.pdf", "https://www.asturias.es/bopa/2026/07/10/2026-05918.pdf"),
        ("as-ley-presupuestos-2026.pdf", "https://www.boe.es/boe/dias/2026/02/09/pdfs/BOE-A-2026-2888.pdf"),
        ("as-circular-inicio-curso-2026-27.pdf", "https://www.educastur.es/documents/34868/38433/CIC_CPUBLICOS_20260715.pdf/6c44c1f6-1982-0b16-6b3d-0e2c57a54440"),
        ("cn-resolucion-nominas-docentes-2026.pdf", "https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=430558"),
        ("cn-instrucciones-ceip-2026-27.pdf", "https://www.educantabria.es/documents/d/educantabria/instrucciones-ceip-inicio-de-curso-26-27_vfinal_signed"),
        ("cn-instrucciones-ies-2026-27.pdf", "https://www.educantabria.es/documents/d/educantabria/instrucciones-ies-inicio-curso-26-27_vfinal_signed"),
        ("cm-orden-194-2025-anexo-iii-docentes.pdf", "https://anpecastillalamancha.es/openFile.php?link=notices/att/7/anexo-iii---conceptosretributivospersonaldocente_e_t1767869514_7_3.pdf"),
        ("cm-orden-194-2025.pdf", "https://anpecastillalamancha.es/openFile.php?link=notices/att/7/orden-194_2025normas-ejecucion-presupuestos-2026_t1767869346_7_2.pdf"),
        ("cm-ley-5-2025-presupuestos.pdf", "https://anpecastillalamancha.es/openFile.php?link=notices/att/7/leypresupuestosclm_2026_t1767869346_7_1.pdf"),
        ("cm-orden-104-2026-instrucciones.pdf", "https://docm.jccm.es/portaldocm/descargarArchivo.do?ruta=2026%2F07%2F10%2Fpdf%2F2026_5253.pdf&tipo=rutaDocm"),
        ("ex-doe-65-2026-anuncio-tablas.pdf", "https://doe.juntaex.es/pdfs/doe/2026/650o/26080505.pdf"),
        ("ex-tablas-retributivas-docentes-2026.pdf", "https://anpeextremadura.es/openFile.php?link=retribuciones%2F12%2Fretribuciones-2026_t1779992191_12_a.pdf"),
        ("ex-instruccion-15-2026-inicio-curso.pdf", "https://www.educarex.es/pub/cont/com/0054/documentos/Instrucciones_inicio_curso_26_27%28F%29%281%29.pdf"),
        ("mu-borm-resolucion-16-12-2025-retribuciones.pdf", "https://www.borm.es/services/anuncio/ano/2025/numero/6124/pdf"),
        ("mu-guia-retribuciones-ccoo-enero-2026.pdf", "https://murcia.fe.ccoo.es/5374e343d0772497a4f17e7bc1b26533000063.pdf"),
        ("mu-borm-jornada-docente-2023.pdf", "https://www.borm.es/services/anuncio/ano/2023/numero/3891/pdf?id=820185"),
        ("mu-inspeccion-horarios-secundaria-2026-27.pdf", "https://www.carm.es/web/descarga?ARCHIVO=DOCUMENTO+APOYO+HORARIOS+SECUNDARIA+2026-2027_260812.pdf&ALIAS=ARCH&IDCONTENIDO=178976&IDTIPO=60&RASTRO=c794%24m5042"),
        ("na-retribuciones-2026.pdf", "https://gobiernoabierto.navarra.es/sites/default/files/assets/files/pagina-interior/transparencia/Retribuciones2026.pdf"),
        ("na-resolucion-333-2026-instrucciones.pdf", "https://www.educacion.navarra.es/documents/27590/0/Resol+333-2026+INSTRUCCIONES+CURSO+2026-2027.pdf/7dc9d00a-5409-e128-52e6-34b1f875cc1a"),
        ("na-ley-foral-16-2025-art-19.html", "https://www.iberley.es/legislacion/articulo-19-presupuestos-generales-ano-2026-navarra"),
        ("ri-tabla-retribuciones-docentes-2026.pdf", "https://www.larioja.org/larioja-client/cm/edu-recursos-humanos/images?idMmedia=1698473"),
        ("ri-ley-presupuestos-2026-bor-252.pdf", "https://www.boe.es/ccaa/bor/2025/252/l22598-22880.pdf"),
        ("ri-instrucciones-18-06-2026.pdf", "https://www.larioja.org/larioja-client/cm/edu-recursos-humanos/images?idMmedia=1735625"),
        ("ri-anpe-retribuciones-2026-nov.pdf", "https://documentos.anperioja.es/Retribuciones_La_Rioja.pdf"),
        ("ic-retribuciones-2026-personal-docente.pdf", "https://www.gobiernodecanarias.org/cmsgob1/export/sites/transparencia/temas/institucional-organizativa/retribuciones/retribuciones-personal/personal-funcionario/doc/retribuciones-2026-personal-docente.pdf"),
        ("ic-resolucion-73-2026-instrucciones.pdf", "https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/normativa-internas/resolucion-73-instrucciones-organizacion-funcionamiento-centros-curso-26-27.pdf"),
        ("an-tablas-retribuciones-docentes-2024.pdf", "https://www.juntadeandalucia.es/educacion/portales/documents/20123/999421/tablas_fiscalizadas_10_07_2024.pdf/5f7c7109-0587-e99a-013d-8950f7719993?version=1.0"),
        ("an-boja-150-2024-acuerdo-curso-2024-25.pdf", "https://www.juntadeandalucia.es/boja/2024/150/BOJA24-150-00002-49031-01_00305981.pdf"),
        ("an-boja-123-2025-acuerdo-curso-2025-26.pdf", "https://www.juntadeandalucia.es/eboja/2025/123/BOJA25-123-00002-9205-01_00322804.pdf"),
        ("an-ugt-retribuciones-enero-2026.pdf", "https://ugtserviciospublicosandalucia.es/images/2023/ENSE%C3%91ANZA/PDF/RETRIBUCIONES_DEL_PROFESORADO_enero2026.pdf"),
        ("an-orden-31-08-2026-horario.html", "https://www.juntadeandalucia.es/boja/2026/168/c03/2"),
        ("ar-instrucciones-ies-2026-27.pdf", "https://educa.aragon.es/documents/20126/6844128/CSVFV61LMW0LZ120XFIL+Instrucciones+curso+2026-2027+para+centros+educativos._03+IES+2026-2027+V8-(Instrucciones).pdf/ff9b76e8-b92f-291b-b736-6f093187162c"),
    ],
    # Sueldos con 15 años de servicio: normas sobre sexenios, grados y carrera que no estaban en «sueldos»
    "sueldos_antiguedad": [
        ("ct-ordre-edf-56-2025-estadis.pdf", "https://portaldogc.gencat.cat/utilsEADOP/AppJava/PdfProviderServlet?documentId=1011571&type=01&language=ca_ES"),
        ("ib-boib-166-2025-carrera-segundo-tramo.pdf", "https://intranet.caib.es/eboibfront/pdf/es/2025/166/1208703"),
        ("na-dfl-251-1993-estatuto-consolidado.pdf", "https://www.boe.es/buscar/pdf/1993/BON-n-1993-90004-consolidado.pdf"),
        ("cl-carrera-docente-preguntas-frecuentes.pdf", "https://www.educa.jcyl.es/profesorado/es/gestion-personal-docente/carrera-profesional-horizontal-personal-docente/categoria-profesional-i-proceso-ordinario-acceso-carr-dec9a.ficheros/1825877-Preguntas%20frecuentes.pdf"),
        ("cl-proyecto-decreto-carrera-docente-2025.pdf", "https://transparencia.jcyl.es/huellanormativa/EDU/2025-284%20Decreto%20carrera%20profesional%20docentes/7.%20Proyecto%20Decreto%20carrera%20profesional%20horizontal%20docente%20(22-09-2025).pdf"),
    ],
    # INEE: tablas del informe español de PISA 2025 (Excel dentro de un RAR)
    "pisa": [("tablas-informe-pisa-2025.rar", "https://www.educacionfpydeportes.gob.es/dam/jcr:4f7056b5-02d7-4e6d-a454-2caa3e04893f/tablas-informe-pisa-2025.rar")],
}


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huella_contenido(datos: bytes) -> str:
    """sha256 sin las líneas CREATION-DATE y SUBJECT-CODE de los PC-Axis: el servidor del Ministerio pone la fecha de cada
    descarga y un SUBJECT-CODE que cambia («null», «Alum», «RD»…), así que sin quitarlas cada día parecería un fichero
    nuevo. El manifest guarda siempre el sha256 del fichero tal cual."""
    return hashlib.sha256(re.sub(rb'(CREATION-DATE|SUBJECT-CODE)="[^"]*";\r?\n?', b"", datos)).hexdigest()


def leer_manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def descargar(url: str) -> bytes:
    # Sin datos personales en la petición: solo un nombre genérico de cliente.
    # Algunas webs autonómicas rechazan un User-Agent que no parezca de navegador; sigue sin datos personales.
    pet = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (educacion-ccaa; datos abiertos)", "Accept": "application/json, */*"})
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
            # Si una tabla no existe, el servidor redirige a una página web con código 200: que no se guarde como .px
            if nombre.endswith(".pdf") and not contenido.startswith(b"%PDF"):
                fallos.append(f"{fuente}/{nombre}: no es un PDF (¿página de error?)")
                print(f"{fuente}/{nombre}: ERROR no es un PDF")
                continue
            if nombre.endswith(".px") and not contenido.lstrip().startswith(b"AXIS-VERSION"):
                fallos.append(f"{fuente}/{nombre}: no es un PC-Axis (¿tabla inexistente?)")
                print(f"{fuente}/{nombre}: ERROR no es un PC-Axis")
                continue
            huella = hashlib.sha256(contenido).hexdigest()
            previos = [m for m in manifest if m["fuente"] == fuente and Path(m["fichero"]).name == nombre]
            if previos:
                ultimo = max(previos, key=lambda m: m["fecha_captura"])
                anterior = ORIGINALES / ultimo["fichero"]
                if ultimo["sha256"] == huella or (anterior.exists() and huella_contenido(anterior.read_bytes()) == huella_contenido(contenido)):
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
