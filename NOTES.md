# Notas de desarrollo

## Stack (comprobado en las webs hermanas, 24/11/2026)

sanidad-ccaa y presupuestos-ccaa usan lo mismo: Next.js 16 con exportación estática (`output: "export"`), TypeScript,
Vitest y Vercel Analytics (sin cookies). No hay librería de gráficos ni de mapas: todo es SVG propio. El mapa son las
siluetas del IGN (es-atlas), proyectadas una vez con `d3-geo` en `scripts/proyectar_mapa.mjs`. Los datos se preparan con
scripts de Python y se guardan como JSON en `src/data/`. La base es sanidad-ccaa, la más completa (mapa, ficha, plegables).

## Qué se reutiliza de sanidad-ccaa

- Configuración: `package.json`, `next.config.ts`, `tsconfig.json`, `vitest.config.ts`, `layout.tsx` (fuentes Inter y
  Space Grotesk, Analytics), `App.tsx` (esqueleto HTML + `iniciar()`).
- Estilos: `globals.css` entero (colores, tarjetas, mapa, ficha, tabla, plegables), con lo propio añadido al final.
- Mapa: `src/data/mapa-ccaa.json` y `scripts/proyectar_mapa.mjs` (mismos ids: AN, AR… CE, ML).
- Interfaz (`src/lib/app/ui.ts`), adaptada: mapa con tramos, tooltip, `plegable()`, línea de años con ▶, «De más a
  menos», evolución con destacadas, tabla con CSV, PNG de los gráficos, ficha con «Comparar con», estado en la dirección.
- Reglas de la casa: datos primero y explicaciones plegadas; textos claros sin jerga; tono neutral; nunca explicar
  saltos por nuestra cuenta; Ceuta y Melilla aparte.

## Qué es nuevo

- `scripts/descargar.py`: descarga cada fuente a `datos-originales/<fuente>/<fecha>/` y la apunta en
  `datos-originales/manifest.json` (URL, fecha, bytes, sha256). Si el fichero no cambia, no guarda otra copia.
- `scripts/comun.py`: lector de PC-Axis (EDUCAbase) y de JSON-stat (Eurostat), territorios y manifest.
- Esquema común en formato largo (`src/data/observaciones/<fuente>.json`) y una ficha por indicador
  (`src/data/indicadores/<id>.json`), con los campos de la ficha YAML del brief.
- Fiabilidad A/B/C y estado en cada cifra (chip junto al dato, en el PNG y en el CSV).
- España = dato oficial (ponderado), no la media de las 17 (al revés que en sanidad).
- Sin puestos del 1 al 17 con encuestas: «por encima / por debajo de España».
- Capa «Leyes y hechos» (fechas y títulos del BOE), apagada por defecto.
- Rupturas de serie tal como las marca cada fuente.
- Botón «Compartir» y enlaces «Siguiente».
- Tema «Resumen» (tarjetas con `resumen: true` en la ficha) y vista «Reparto» (barras al 100 %, `reparto: true`).
- Variantes por sexo o por titularidad (`variantes` en la ficha; clave «sexo|titularidad»).
- Tests de §7: ficha y fuente de cada cifra, rangos plausibles, saltos > 15 % solo con `revisado_hasta`, suma de
  territorios = España (indicadores aditivos), manifest con sha256.

## Decisiones que se apartan del brief (acordadas con el autor)

- Tres vistas (Datos con temas · Tu comunidad · Cómo leer los datos) en lugar de nueve pestañas: los temas del brief
  (Centros, Profesorado, Resultados, Equidad, Trayectorias, Financiación) son temas dentro de Datos. Solo se ven los que
  ya tienen datos.
- JSON en lugar de Parquet/CSV y de YAML: la web lee JSON sin dependencias. Mismos campos.
- `datos-originales/` en lugar de `data/raw/`: en git van el manifest y los ficheros pequeños (px, json, xml); los
  grandes (pdf, xls, zip…) se quedan en local (ver `.gitignore`), con su URL y sha256 en el manifest.
- Un `descargar.py` con todas las fuentes y un `extraer_<fuente>.py` por fuente, en lugar de `fetch_*`/`build_*`.
- GitHub Actions con descarga semanal: pendiente hasta la fase 2, cuando se sepa qué fuentes responden bien.
- Territorios: ids de dos letras (los del mapa) en la web y en la dirección (`ccaa=md`); el código INE (00-19) va en
  las observaciones y en `src/data/territorios.json`.

## Fase 1: abandono temprano

- Fuente principal: EDUCAbase, `indi_01.px` (2002-2025, comunidad × sexo, con Ceuta y Melilla).
- Comprobado con Eurostat: 1.392 valores del Ministerio tienen pareja en Eurostat (`edat_lfse_14` para España,
  `edat_lfse_16` para las regiones NUTS 2) y coinciden con diferencia ≤ 0,1 puntos. Dos pasan de 0,05 (Cataluña 2005 y
  Cataluña mujeres 2004): se guardan en `comprobacion` de la salida.
- Muestra pequeña: el Ministerio marca con la nota (3) a Cantabria, Navarra, La Rioja, Ceuta y Melilla; Eurostat marca
  con «u» (baja fiabilidad) datos sueltos de más comunidades (sobre todo por sexo). La web marca ambas cosas con †.
- Rupturas: el Ministerio dice «Ruptura de serie: año 2005». Eurostat marca ruptura en España en 2003, 2005, 2006, 2014
  y 2021, y «la definición difiere» desde 2021. El brief hablaba de 2014 y 2021: se muestran las de las fuentes.
- Rango plausible 0-75: Ceuta, hombres, 2005-2006 llega al 63,9 % (igual en Eurostat, marcado «u»).
- Saltos > 15 % frente al año anterior: revisados hasta 2025 (`revisado_hasta`). La mayoría están en comunidades con
  muestra pequeña o en las series por sexo, y varios en años con ruptura.

## Fase 2: EDUCAbase (Estadística de las Enseñanzas no universitarias)

`scripts/extraer_educabase.py` (descarga: `python scripts/descargar.py educabase`). Seis indicadores, por comunidad y curso:

| Indicador | Tabla | Desde | Comprobación |
|---|---|---|---|
| Alumnado por titularidad (pública, concertada, privada no concertada) | `todas_01.px` de cada curso (cálculo propio: %) | 2011-12 | partes = total; comunidades = España; recuentos = serie `alumnado_1_01`; % pública = `general_01` |
| Escolarización 0-2 años | `escolar_05.px` | 2012-13 | publicada tal cual |
| Alumnado extranjero | `extran_04.px` | 2000-01 | = `extran_02` / `alumnado_1_01`: 493 de 520 (27 diferencias, casi todas 2009-10) |
| Alumnos por profesor (todos, pública, privada) | `series07.px` | 2000-01 | = `alumnado_1_01` / `series03`: 1.475 de 1.560 (85 diferencias: Andalucía, Galicia, País Vasco y cursos antiguos, con notas de la fuente) |
| Idoneidad a los 15 años (por sexo) | `idoneidad_05.px` | 2000-01 | publicada tal cual |
| Repetición en ESO (por titularidad/financiación) | `repetidores_03.px` | 2007-08 | publicada tal cual |

- Las diferencias de los recálculos se guardan y la web las enumera («Fuentes y comprobaciones»), sin explicarlas. La web
  muestra siempre el dato publicado. El script solo se para si hay diferencias en el último curso (cambio de formato).
- Las notas de cada tabla se guardan tal cual con las comunidades y cursos que las citan (llamadas «(2)» en las etiquetas)
  y salen en el mapa, en la ficha y en «¿Qué mide esto?».
- Concertada: antes de 2011-12 la tabla por titularidad/financiación no está en EDUCAbase con el mismo formato (los
  cursos anteriores no tienen la carpeta `gen-todas`). En 2015-16 Navarra viene sin código («NAVARRA (Comunidad Foral de)
  (4)»): alias añadido en `territorios.json`.
- Escolarización 0-2 desde 2012-13: la nota 3 de la tabla dice que desde ese curso se usa la población revisada del INE;
  antes hay un cambio de criterio en Navarra (nota 2), cursos sin dato (Canarias 2003-04 a 2009-10) y saltos sin nota
  (Castilla-La Mancha 2008-09 → 2009-10: 2,3 % → 31,4 %). El avance 2025-26 no trae el desglose por sexo: solo total.
- Rangos: repetición hasta 50 (Asturias, privada no concertada, 2011-12: 41,4 %).
- Saltos > 15 %: revisados hasta el último curso. Repetición: muchos en 2021-22 (la fuente no los explica);
  extranjeros: 2000-2003 (crecimiento rápido, sin rupturas marcadas).
- Las cifras del brief eran de otra versión: concertada 24,5 % (brief 24,4 %), privada no concertada 8,7 % (brief 8,8 %).

### Financiación: aplazada (a propósito)

- La serie de gasto «en relación al PIB» por administración (`economicas/gasto/series/series_09.px`) está referida al PIB
  **de España** (Andalucía 0,55 %), no al de cada comunidad: no sirve para comparar comunidades.
- Gasto por alumno y gasto/PIB regional: están en el Sistema Estatal de Indicadores (SEIE, indicadores F), en PDF/Excel.
- El gasto público total 2024 ya es definitivo en EDUCAbase: 71.396.246 miles de euros con capítulos financieros
  (el brief citaba 71.348,8 M€ provisional).
- Conciertos por comunidad: `series_07.px` (miles de euros). Pendiente decidir el denominador (no «coste por alumno»).

## Fase 3: alumnos por clase y PISA 2025 (aprobada el 24/11/2026)

### Alumnos por clase (`alumnos_unidad`, tema «Profesorado y aulas»)
- EDUCAbase, «Número medio de alumnado por unidad», series `centros/centrosyunid/series/unidades/series_2_0x.px`: Infantil
  0-2 y 3-5, Primaria, ESO, Bachillerato, FP básica, media y superior; desde 2005-06 (primer curso común); por titularidad,
  y concertada / no concertada solo en Infantil 3-5, Primaria y ESO (no en el avance 2025-26: cada variante usa su
  último curso con dato).
- Comprobación: en Primaria y ESO, alumnado / unidades = media publicada en 2.348 de 2.520 casos; las diferencias se
  repiten cada curso en las mismas comunidades (Cataluña, y España en la privada, que la incluye). El script solo se
  para si aparece una diferencia nueva en el último curso.
- Cifras sueltas extremas en la privada no concertada (Cantabria 2005-06, 68,2 en Primaria; Murcia 2017-18, 47,6 en
  Infantil 3-5): son las publicadas; la ficha lo avisa. Rango plausible 1-70.

### PISA 2025 (`pisa_puntuacion`, `pisa_bajo`, `pisa_alto`, tema «Resultados (PISA)»)
- INEE, tablas del informe español (`tablas-informe-pisa-2025.rar`, Excel): ciencias (2.1), lectura (2.14), matemáticas
  (2.18) con error típico; niveles (2.4, 2.15, 2.19); evolución de España y OCDE-35 (2.9, 2.17, 2.21); diferencias por
  comunidad ciencias 2015-2025 (2.11) y matemáticas 2022-2025 (2.22). Hace falta UnRAR (WinRAR) para abrirlo.
- Intervalo al 95 % = valor ± 1,96 ET. «Por encima / no se distingue / por debajo de España» según si el intervalo
  de la comunidad incluye la cifra de España (aproximación, dicha en la web). Sin puestos.
- Cataluña: nota (**) del INEE (23,2 % excluido, «no deben ser utilizados para comparaciones»): sin color, fuera de
  gráficos y tablas comparativas; su cifra solo en su ficha, con el aviso (decisión del autor). Murcia: nota (*) (12,7 %,
  «con la debida cautela»): †.
- Erratas de la fuente detectadas por las comprobaciones:
  - Figura 2.11: las diferencias (y su ET) de Castilla y León y Castilla-La Mancha están intercambiadas (las medias sí
    cuadran). Se usa la resta de las medias, sin ET, con una nota.
  - Nombres distintos entre hojas: «Madrid, Comnidad de», «Madrid, C. de», «Asturias», «Com. Valenciana»… (alias en
    `territorios.json`). El script se para si una tabla de 2025 pierde una comunidad.
- España no tiene lectura 2018 (la OCDE no la publicó). Por comunidad, solo ciencias 2015 y matemáticas 2022 además
  de 2025. Ediciones anteriores completas por comunidad: solo con los microdatos del INEE (pendiente).
- Niveles: «bajo» = por debajo del nivel 2; «alto» = niveles 5 y 6. Suma de niveles publicados, sin error de la suma.

### Cambios de modelo
- Dimensiones generales: sexo, titularidad, etapa y competencia (clave «sexo|titularidad|etapa|competencia»); fichas
  con `dimensiones` (o `variantes`, las antiguas) y `filas_ficha` como objetos. Referencias (UE-27, media OCDE, total UE,
  OCDE-35) en `referencias` de la ficha.

### Tasa bruta de graduación (`tasa_graduacion`, tema «Trayectorias», publicada el 25/11/2026)
- «Las cifras de la educación en España», edición 2026, tabla C2.9 (`c2.xlsx`, solo en local): ESO, Bachillerato, FP
  básica, Técnico y Técnico superior, por sexo; cursos 2013-14, 2018-19 y 2023-24 (FP básica, los dos últimos).
- Fuera: ESO de adultos y títulos universitarios (asignados por la sede del rectorado). Puede superar el 100 %.
- Comprobación: ambos sexos entre hombres y mujeres (276 casos); las 19 comunidades y ciudades y España.
- Cataluña, FP básica: 0,0 % (2018-19) y 0,4 % (2023-24), cifras publicadas; la ficha lo dice sin explicarlo.

### Gasto público por alumno (`gasto_alumno`, tema «Financiación», publicado el 25/11/2026)
- «Las cifras de la educación», tabla B4.6 (`b4.xlsx`) y método del capítulo B4 (`b4.pdf`): 2023, 17 comunidades y
  España (sin Ceuta ni Melilla). Dos cifras oficiales: «pública y concertada» y «solo pública» (sin conciertos ni
  alumnado concertado). Método OCDE: todo el gasto público en la comunidad sin becas ni capítulos financieros;
  alumnado en equivalentes a tiempo completo, media de dos cursos.
- Solo 2023: el Ministerio cambió en 2023 el cálculo del alumnado de FP y avisa de que afecta a la comparación.
- No se calcula un coste «solo concertada» (regla 6 del brief): la ficha lo explica.

### Escolarización por edad (`escolarizacion_edad`, tema «Centros y alumnado», publicada el 25/11/2026)
- EDUCAbase, tasas netas a los 3 (`escolar_07`), 16, 17 y 18 años (`escolar_12/16/20`, metodología revisada), por sexo,
  desde 2012-13 (población revisada del INE). A los 18 no cuenta la universidad: etiqueta «18 años, sin universidad».

### Brecha socioeconómica en PISA (`pisa_brecha_isec`, tema «Equidad», publicada el 25/11/2026)
- INEE, PISA 2025, Tablas_cap_3, Figura 3.3: diferencia en ciencias entre el cuarto más alto y el más bajo del ISEC,
  con ET; comprobado que = cuarto 4 − cuarto 1 en los 22 territorios. Cataluña y Murcia, como en el resto de PISA.
- «Por encima de España» = brecha mayor; la ficha lo aclara (comparación, no valoración).

### Índice socioeconómico y cultural medio (`pisa_isec`, tema «Equidad», publicado el 25/11/2026)
- INEE, Tablas_cap_3, Figura 3.1 (ESCS de la OCDE), con ET; 4 decimales (el ET es de centésimas).
- NO se publica la «puntuación descontando el ISEC» (Figura 3.6): con la pendiente de la Figura 3.5 y el ISEC medio,
  la referencia implícita del ajuste varía entre territorios (0,11 a 0,41), así que el INEE usa otro modelo que sus
  tablas no detallan. Pendiente de encontrar su método (el informe español de 2025 no está en la web del INEE).

### Chicas y chicos en PISA (`pisa_sexo`, tema «Equidad», publicado el 25/11/2026)
- INEE, Tablas_cap_3, Figura 3.7: diferencia chicas − chicos por competencia, con ET; comprobado en los 66 casos.
- Se clasifica frente a CERO, no frente a España (`referencia_cero` y `clases` en la ficha): «a favor de las chicas /
  sin diferencia clara / a favor de los chicos», sin rojo. Textos en palabras, sin «A menos B».

### Necesidades educativas especiales (`alumnado_nee`, tema «Equidad», publicado el 25/11/2026)
- EDUCAbase, tabla acnee_02 de cada curso (2011-12 a 2024-25): % de alumnado con NEE por titularidad/financiación.
  Recuento oficial, no muestra (fiabilidad A).
- Lectura por posición: en 2024-25 la tabla repite la etiqueta «TOTAL» (la primera es el total de verdad: 4,0 % en
  España, no 3,4). Comprobado en 280 casos que el total de cada comunidad queda entre los de sus redes.
- Notas del Ministerio ligadas a su curso (Canarias y La Rioja 2012-13, Comunitat Valenciana 2016-17).

### Becas en Bachillerato y FP (`becas_bach_fp` e `importe_becario`, tema «Financiación», publicado el 25/11/2026)
- «Las cifras de la educación» 2026, tabla B5.5 (curso 2023-24, el curso lo dice la cabecera del PDF): % de alumnado
  becario e importe medio por becario, de todas las administraciones. Galicia «..» (su administración no da datos; el
  total de España usa los de Galicia de 2020-21, nota de B5.3).
- Comprobado: importe medio = importe (B5.4) / becarios (B5.3), con FP = básica + media + superior (57 casos, España
  incluida); % total entre Bachillerato y FP.
- No se usan la obligatoria (ayudas de libros y comedor de cada comunidad, no comparables: Navarra 1.938 becarios,
  Cataluña 452.670) ni la universidad (va por comunidad de la universidad, no de residencia).
- Quien tiene beca del Ministerio y de su comunidad cuenta dos veces (nota de la estadística). El aviso de la ficha cita
  el % de becarios postobligatorios no universitarios de la propia comunidad (≥ 10 %; tabla 2 de EDUCAbase becas
  2023-24): `extraer_cifras.py` falla si el texto de la ficha deja de cuadrar con los datos.

### Empleo de los titulados de FP (`empleo_fp`, tema «Trayectorias», publicado el 25/11/2026)
- EDUCAbase, Estadística de inserción laboral de las personas graduadas en FP, resultados por comunidad: tablas
  ccaa_1_01 (FP básica, desde 2015-16), ccaa_2_01 (grado medio) y ccaa_3_01 (grado superior), cohortes 2011-12 a
  2022-23 (las dos últimas, provisionales). Se usa la «tasa de afiliación» (alta laboral algún día de marzo; es la de
  F1.9), no la «tasa media». Primer año = marzo de t+2; tercer año = marzo de t+4 (metodología 2025).
- Comunidad = la del centro donde se tituló (informe 2025). Ceuta y Melilla vienen juntas: no se muestran.
- Comprobado: la cohorte 2020-21 coincide con F1.9 de «Las cifras» (216 cifras); ambos sexos entre hombres y mujeres
  (1.060 casos); tasa ≥ tasa media.
- Errata de la fuente: en el Excel de F1.9, Cataluña grado medio «previo a la graduación» ambos sexos = 89,0; el PDF y
  EDUCAbase dan 13,4 (columna que no usamos).
- Marzo de 2021 (al año para 2019-20, a los tres años para 2017-18) baja: solo se dice que coincide con la pandemia.

### Becas que paga la comunidad (`becas_comunidad`, tema «Financiación», publicado el 25/11/2026)
- Tabla 2 de la Estadística de Becas (EDUCAbase), cursos 2013-14 a 2024-25 (antes no está en este formato): comunidad /
  (Ministerio + comunidad), por importe y por becarios y por enseñanza. Cálculo propio sobre cifras oficiales.
- Comprobado: total = Ministerio + comunidad (importes con 1.000 € de tolerancia por redondeo: Baleares obligatoria
  2022-23 y 2024-25 difieren 0,5 y 0,3 miles) y suma de filas = total de España (2.048 comprobaciones).
- Galicia: 2020-21 provisional; 2021-22 repite 2020-21; desde 2022-23 sin datos de su administración. Solo universidad
  desde 2021-22. Ceuta y Melilla fuera (educación gestionada por el Ministerio).

### Sueldos del profesorado por comunidad (EN CURSO, sin publicar; 25/11/2026)
- ESTADO: estructura hecha (normas.json + calcular_sueldos.py). Analizadas: Madrid y Cataluña (caso «al empezar»).
  Plan acordado con el usuario: analizar las demás de una en una (guardando en git), y publicar al final con mapa,
  horas lectivas y € por hora semanal. Hechas también: Comunitat Valenciana, País Vasco, Illes Balears, Castilla y León, Aragón, Galicia, Asturias, Cantabria, Castilla-La Mancha, Extremadura, Murcia, Navarra y La Rioja (25/11/2026). Faltan Canarias y Andalucía. Siguiente: Andalucía (solo
  tabla 2024: buscar fuente oficial 2026) o el resto. El ct-gov-205 da error SSL en descargar.py: ya está guardado a mano.
- Andalucía (pendiente, 25/11/2026): sin tabla oficial 2026 de la pública. Piezas: tabla «fiscalizada» de 10/7/2024
  (juntadeandalucia.es/educacion/portales/web/educacion/plantilla-docente-y-retribuciones); Acuerdo del Consejo de
  Gobierno de 25/6/2025 (BOJA 123, 30/6/2025: +14,50 €/mes A2 y +16,50 € A1 en el componente básico del específico, 14
  pagas, desde 1/9/2025; «culmina» la equiparación); subidas generales 2025 (+2,5 %) y 2026 (+1,5 %, Ley 8/2025 art. 17).
  Reconstruir = cálculo propio en varios pasos: decidir con el usuario. La resolución de concertada 2026 (BOJA 21,
  2/2/2026) NO sirve para la pública.
- La Rioja: tabla oficial «Retribuciones 2026» de la Consejería (enero): específico general 815,42 maestros / 825,47
  secundaria; ANPE (nov. 2026) da 837,85 para secundaria (= 825,47 × 1,015): no se encontró norma → se usa la oficial y se
  avisa. Extras con específico: ley de presupuestos 2026. Horas: maestros 23 (Orden de julio de 2024); secundaria 18
  deducido de la tabla de reducciones de las instrucciones de 18/6/2026.
- Navarra: régimen PROPIO (campo `anual_propio` en normas.json; el script no le aplica las comprobaciones estatales).
  Sueldo inicial nivel A 31.622,50 / nivel B 26.602,94 (Gobierno Abierto, Retribuciones 2026) + específico docente en %
  del sueldo del nivel (Ley Foral 16/2025 art. 19: 33,48 % secundaria, 38,07 % maestros; importe = cálculo). Sin grado
  (antigüedad) ni el 5,45 % (solo maestros en ESO). Horas (Res. 333/2026): maestros 23 sesiones de 50 min, secundaria 18.
- Murcia: sin tabla docente oficial de 2026 → importes de 2025 (Resolución 16/12/2025, BORM 18/12/2025, anexo XI) × 1,015,
  marcados `calculo`; coinciden en los 7 conceptos con la guía de CCOO de enero de 2026. Estructura: específico bajo
  (369,21) + productividad docente mensual (437,91 / 444,36) + productividad semestral en cada extra (524,07 + 240,24 /
  295,87) + paga adicional del específico 260,96 (0 sexenios). Carrera horizontal tramo I no incluida. Horas: Acuerdo de
  1/6/2023 (BORM 22/6/2023): 23 y 18 (Inspección 2026-27: hasta 19 si hace falta).
- Descargas a mano (descargar.py da error con ellas; ya están en datos-originales y en el manifest): ct-gov-205-2026.pdf
  (SSL), ex-tablas-retributivas-docentes-2026.pdf y mu-inspeccion-horarios-secundaria-2026-27.pdf (devuelven HTML a Python;
  con curl funcionan).
- Extremadura: tablas de la DG de Personal Docente 2026 (PROFEX; anuncio DOE 65, 7/4/2026; PDF copiado de ANPE): específico
  general 544,43 + autonómico 270,29 (incluye los +80 € del Acuerdo de 13/1/2026), iguales para todos, 14 pagas (columna
  P.A.C.E.). Horas: Instrucción 15/2026: maestros 23, secundaria 18 (hasta 21).
- Castilla-La Mancha: Orden 194/2025 (DOCM 7/1/2026): anexo I (básicas y destino 2026) y anexo III (específico general
  907,43 = autonómico + general, igual para todos). Ojo: la Ley 5/2025 trae sueldos SIN las subidas: no citarla para
  importes. Extras con una mensualidad del específico (ley, funcionarios en general → supuesto). Horas: Orden 104/2026
  art. 6: secundaria 18; maestros 23 según UGT (la orden no lo dice → `resumen_sindical`). Originales del DOCM copiados de
  ANPE-CLM (el DOCM no da enlace estable para la Orden 194).
- Cantabria: Resolución de 30/1/2026 (BOC 6/2/2026): específico general 875,10 igual para todos (la resolución da anual =
  12 × mensual; la Ley 2/2024 art. 23 añade 2 pagas adicionales para funcionarios en general → supuesto, ±1.750 €);
  complemento de fomento a la formación 35,77 €/mes hasta el primer sexenio. Horas (instrucciones 2026-27): maestros 24
  (con recreos), secundaria 18 (hasta 20; aproximado).
- Asturias: BOPA 10/7/2026 (Acuerdo de 6/7/2026), anexo V: destino PROPIO (+1 % sobre el estatal); específico general
  708,37 igual para todos; complemento personal transitorio para quien no cobra sexenios (43,85 hasta agosto, 113,85 desde
  septiembre de 2026; 12 mensualidades). Extras con destino y específico: ley de presupuestos (BOE-A-2026-2888) para
  funcionarios en general → supuesto para docentes. Horas (circular de inicio de curso 2026-27): maestros 23, secundaria 18.
- Galicia: orden de nóminas DOG 26/1/2026, anexo V (específico general 779,29 igual para todos los cuerpos, 14 pagas) y
  tabla anual de transparencia (totales 35.343,50 / 39.477,00: cuadran al céntimo, campo `total_sin_otros`). Horas
  2026-27: maestros 23, secundaria 18 sesiones (resolución de xornada: PDF escaneado sin texto → leído en el resumen de
  CSIF; marcado `resumen_sindical`; si se quiere, leerlo a mano).
- Aragón: hoja oficial «Tablas_retribuciones_docentes_2026.xlsx» (transparencia) = acuerdo de Gobierno de 14/1/2026
  (+1,5 %) + tramo autonómico 2026 del acuerdo de 2024 (BOA 12/12/2024; ~2,25 %): comprobado con la hoja «anuales».
  Pagas adicionales del específico = importe propio (~90 % de la mensualidad) → campo `importe_cada_una`. Complemento de
  fondos adicionales 168,36 €/año. Horas (instrucciones 2026-27): maestros 23 (antes 24), secundaria 18 (hasta 21).
- Castilla y León: Orden PRE/1/2026 (BOCYL 5/1/2026), Anexo V: específico = parte general 294,20 + autonómica (423,45
  maestros / 424,79 profesores), en extras por el Anexo XIII.5; «Consolidación Punto 4.º» (25,27 / 27,04) incluida como
  supuesto (no dice a quién se aplica). Horas: Acuerdo 24/1/2022 (Orden EDU/43/2022): maestros 24 (21,5 + 2,5 de
  recreo); secundaria «18 o 19 periodos de forma mayoritaria» → 18, marcado aproximado. Jornada 35 h.
- Baleares: tabla «Retribucions personal funcionari gener 2026» (web nominadelprofessorat = PÚBLICA; la web
  nominaprofessorat es de la CONCERTADA, no usar). Específico general 457,75 igual para los dos cuerpos (14 pagas);
  complemento de la Comunidad Autónoma por tramos de antigüedad (418,54 al empezar, 12 pagas); indemnización de
  residencia (Mallorca 132,28 A2 / 147,09 A1, 12 pagas) incluida y avisada. Horas: 23 y 18 periodos de docencia
  directa (instrucciones de horario, junio de 2026); jornada de 35 h. Atrasos 2020-21 (sentencia TSJ) no se cuentan.
- País Vasco: Instrucción de retribuciones de 25/9/2026 (todo en 14 pagas, sin supuestos); destino PROPIO (701,21 nivel
  21; 880,09 nivel 24) → `"propio": true` en normas.json; sexenios 2.º y 3.º «capitalizados» desde el primer día (316,77
  €/mes) y complemento de complejidad docente (113,44 / 132,51 €/mes) entran en el caso «al empezar». Horas: 21 maestros
  (2026-27) y 17 secundaria (Decreto 252/2025, BOPV 29/1/2026, anexo).
- Valencia: tablas DOGV 27/2/2026 (Tabla 2 docentes; el PDF etiqueta mal la fila de sueldo y destino) + subida de 75 €/mes
  desde sept. 2026 (tabla oficial de la Conselleria: enero + 75 = septiembre, comprobado; acuerdo del Consell de 8/9/2026
  no encontrado en el DOGV, solo prensa; 200 € en total hasta 2028). Específico en 14 pagas: Ley 6/2025 art. 34.1.d
  (régimen Ley 4/2021; supuesto para docentes). Horas: 23 maestros y 18 secundaria (resoluciones de inicio de curso
  DOGV 10407, Decreto 58/2021).
- Madrid, pagas adicionales del específico para docentes: SUPUESTO (guía ANPE; ninguna norma madrileña lo dice para
  docentes: Orden art. 5.4 y Ley 6/2025 art. 21.1.d son del régimen de la Ley 1/1986; art. 23 mantiene la estructura).
- No hay fuente oficial única por comunidad. OCDE (EAG, DSD_EAG_SAL_STA): solo España (2025, USD PPA; relativo a
  titulados superiores con 15 años: España 1,03 primaria / 1,15 secundaria; OCDE 0,88/0,90; UE25 0,78/0,81). Sin
  regiones de España. España no envía sueldos reales (DF_TCH_REL vacío).
- Método propuesto: tablas oficiales de cada consejería, casos tipo (maestro y profesor de secundaria, inicio y 15 años),
  bruto anual, fiabilidad B; comprobar que sueldo base, trienio y complemento de destino (estatales) coinciden.
- Madrid: BOCM 9/2/2026, Orden 3/2/2026 de nóminas, Anexo I (sueldo A1 1.387,24; trienio 53,39; extra 856,05) y Anexo II
  (específico general: secundaria 798,41, maestros 781,84; formación permanente por periodos 93,28 / 117,70 / 156,82 /
  214,64 / 63,20). Extras: sueldo + trienios + 1 mes de destino, y 2 pagas adicionales de 1 mes de específico
  (art. 21.1.d Ley Presupuestos 2026; confirmar que alcanza a docentes).
  https://www.bocm.es/boletin/CM_Orden_BOCM/2026/02/09/BOCM-20260209-6.PDF
- Cataluña: tabla docente 2026 del portal de transparencia (solo +1,5 %; el acuerdo de junio de 2026 sube el específico
  un 30 % hasta 2029 y crea un complemento de mejora: comprobar si ya está aplicado). Secundaria 1.387,24 + 729,14 +
  720,83 = 2.837,21 €/mes; maestros 1.199,52 + 592,11 + 704,95 = 2.496,58. Estadis (sexenios): 128,88 / 135,54 /
  153,66 / 166,39 / 145,65. El PDF descoloca filas (reconstruidas por las sumas).
  https://web.gencat.cat/content/dam/webgencat/documents/la-generalitat/govern-obert/publicitat-activa/servidors-p%C3%BAblics/retribucions-2026/retribucions-personal-docent-no-universitari.pdf
- Andalucía: la Consejería solo publica la tabla de 2024 («tablas fiscalizadas 10/07/2024»); 2026 exigiría aplicar
  subidas a mano (2025 +2,5 %, acuerdo 2025 +14,50/16,50 € en específico desde sept. 2025, 2026 +1,5 %).
  https://www.juntadeandalucia.es/educacion/portales/web/educacion/plantilla-docente-y-retribuciones
- Cataluña 2026, lo que NO está en la tabla mensual publicada (solo +1,5 %):
  · Acord GOV/205/2026 (DOGC 9719, 30/7/2026): complemento de millora del Servei d'Educació, 50 €/mes y 700 €/año en
    2026 (14 pagas), efectos 1/1/2026; 2027 igual; 2028 +50; 2029 +70. https://portaldogc.gencat.cat/utilsEADOP/PDF/9719/2164754.pdf
  · Acord GOV/88/2026 (21/4/2026, DOGC 23/4/2026; modificado por GOV/287/2026 de 17/11/2026): primer tramo (8,5 % según
    CCOO) de la subida del 30 % del específico. TEXTO OFICIAL (datos-originales/sueldos/2026-11-25/
    CVE-DOGC-A-26111079-2026.pdf, descargado a mano por el usuario): +8,50 % = 839,02 €/año maestros y 857,92 €/año
    secundaria, pago único en la nómina de mayo de 2026. (8,5 % × 14 × específico de la tabla da 0,13 € menos: usar el
    importe del acuerdo.)
  · Acord GOV/203/2026: complemento por mayor dedicación lectiva (463,51 €/mes, +5 h, voluntario, especialidades de
    difícil cobertura): no entra en los casos tipo.
- Madrid: paga adicional = 100 % del específico + formación + singulares (Orden 3/2/2026 y guía ANPE); extras = sueldo
  + trienios + destino.
- Decisión del usuario (25/11/2026): no incluir subidas anunciadas (solo aviso); sí lo acordado y en vigor en 2026;
  empezar por Madrid y Cataluña; reflejar todo lo que no sea plenamente comparable.
- Cálculo provisional «al empezar» 2026 (sin trienios, sexenios ni cargos), bruto anual: Madrid maestro 35.379,20,
  secundaria 39.744,68; Cataluña maestro 35.841,76, secundaria 40.216,48 (incluyen los 700 € del complemento nuevo y el
  pago único de mayo; NO restarlos: los dos continúan desde 2027, uno igual y otro en la nómina mensual).
  Supuestos SIN norma que los confirme: específico en las extras de Cataluña; pagas adicionales de Madrid para docentes
  (solo guía ANPE); filas de la tabla catalana reconstruidas por sumas; en Madrid no se han buscado otras normas de 2026.
  Checklist por comunidad: todas las normas retributivas del año; extras confirmadas con norma; horas solo oficiales. Supuesto en Cataluña: el específico va en las 2 extras (lo apoyan los 700 €/año = 14 × 50
  del GOV/205 y el 8,5 % calculado sobre 14 pagas). Madrid: extras = sueldo + destino, más 2 pagas adicionales de
  específico. Sueldo, extras y destino (niveles 21 y 24) coinciden en las dos. Pendiente: caso 15 años (trienios y
  sexenios/estadis: importes, si entran en extras), horas lectivas, y confirmar con norma catalana lo de las extras.
- Sexenios: Madrid = «componente por formación permanente» (93,28 + 117,70 + 156,82 + 214,64 + 63,20 €/mes por
  periodo; exige formación; entra en las 2 pagas adicionales, no en las extras). Cataluña = «estadis» (tabla: 128,88 /
  135,54 / 153,66 / 166,39 / 145,65), PERO desde 2012 se cobran a los 9 años en vez de 6 («retallada dels sexennis»);
  el acuerdo de 2026 prevé compensar la deuda (pagos desde 2027, según sindicatos; 112,78 y 118,61 €/mes por estadi
  según secundaria.info). Situación vigente sin fuente oficial: el caso «15 años» en Cataluña NO es fiable todavía.
- Horas lectivas 2026-27 (OFICIAL): dependen del cuerpo/centro, no del curso (Infantil = Primaria; ESO = Bachillerato = FP).
  · Madrid (Instrucciones de inicio de curso 2026-27, Viceconsejería, ref. 59/078633.9/26): maestros 25 lectivas + 4
    complementarias (4.5.1; cuentan como lectivas los recreos vigilados); secundaria 19 periodos lectivos de ≥ 55 min para
    no tutores, 30 periodos en total (6.1.3.1, Acuerdo de 23/4/2025); tutores de ESO y Bachillerato, además 1 hora de
    convivencia. https://www.comunidad.madrid/docs/2026-07/instrucciones-inicio-de-curso-2026-2027.pdf
  · Cataluña (DOIGC «Personal docent», actualizado 10/6/2026): mestres 23 h de «docència» (incluye apoyo, tutorías y
    sustituciones cortas) + 7 complementarias; secundaria 18 lectivas + 6 complementarias. Jornada 37,5 h en ambas.
    https://documents.espai.educacio.gencat.cat/IPCNormativa/DOIGC/ORG_Personal_docent.pdf
  · No son idénticas las definiciones de «lectiva» (recreos en Madrid; «docència» amplia en Cataluña): € por hora, solo
    orientativo.
- Pagas extra Cataluña CONFIRMADO: Projecte de llei de pressupostos 2026 (BOPC 427, 27/2/2026), art. 26: extras = sueldo
  + trienios + 1 mes de destino; el específico «es percep en dotze mensualitats ordinàries i dues d'addicionals» (falta
  cotejar con la ley final publicada en el DOGC). https://www.parlament.cat/document/bopc/442982007.pdf
- Madrid 2026: no hay otra norma retributiva en vigor aparte de la Orden de nóminas; la carrera horizontal es propuesta
  (efectos 2027). Posible +0,5 % estatal con efectos 1/1/2026 (prensa): afectaría a todas por igual; solo aviso.
- Madrid anunció carrera profesional horizontal desde el 1/1/2027 (noticia 25/11/2026): los sueldos cambian deprisa,
  hace falta fijar una fecha de referencia.

### Descargas: ficheros que cambian sin cambiar
- El servidor de EDUCAbase pone en cada .px la fecha de descarga (CREATION-DATE) y un SUBJECT-CODE que varía. Sin
  ignorarlos, cada descarga parecía un fichero nuevo: `descargar.py` compara el contenido sin esas dos líneas (el
  manifest sigue guardando el sha256 real). Se quitaron 23 copias duplicadas del 25/11/2026.

### Pendiente (siguiente tanda, propuesta)
- Tasa bruta de graduación (Las cifras de la educación, C2.9) y gasto público por alumno oficial (B4.6), con la
  explicación de qué incluye «público y concertado».
- Escolarización a 3 y 16-18 años, idoneidad a los 12, repetición en Primaria, FP.
- Equidad con las tablas de PISA 2025 por comunidad (ISEC, diferencias por sexo, origen, titularidad).
- PISA 2000-2022 por comunidad desde microdatos (reproduciendo antes las cifras publicadas).

## Fuentes que no se pueden descargar solas

- EUR-Lex (objetivo de la UE para 2030, «menos del 9 %»): responde 202 vacío a las descargas automáticas. El objetivo está
  transcrito en la ficha con su enlace y la nota «objetivo político, no estadística».
- API de legislación consolidada del BOE: no tiene la LOGSE (derogada). Se usa el servicio XML de documentos
  (`diario_boe/xml.php?id=…`), que tiene todas.

## Pendiente

- `public/og.png` (vista previa al compartir): cuando el diseño esté cerrado.
- Financiación (SEIE, conciertos), becas, alumnos por grupo (tabla de centros y unidades), FP.
- Fases 3 y 4: OCDE, Eurydice, PISA (con intervalos), TIMSS, PIRLS, PIAAC.
- Comprobar la vista previa en el móvil real (headless Edge no baja de ~500 px de ancho; se probó en un marco de 390).
