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
