# CLAUDE.md

Proyecto: web estática (Next.js + TypeScript) con datos oficiales de educación por comunidad autónoma. Tercera web de la
familia de `sanidad-ccaa` y `presupuestos-ccaa` (mismo estilo y mismas reglas). Brief original y decisiones: `NOTES.md`.

## Estructura de la web

- Una página con tres vistas por `#hash`: Datos (tema «Resumen» + Centros y alumnado, Profesorado y aulas, Resultados
  (PISA), Trayectorias), Tu
  comunidad (`#comunidad-md?vs=ct`, último dato de cada indicador) y Cómo leer los datos (`#metodo`, siete trampas de
  `src/lib/app/textos.ts`). Estado de Datos en la dirección:
  `#datos?tema=…&dato=…&periodo=2024-25&sexo=h|m&tit=publica&etapa=eso&comp=lectura&ccaa=md&graf=ranking|reparto|evolucion|tabla&leyes=si&sel=an,md`.
- Periodos: año («2025», EPA) o curso («2024-25», Ministerio); en el eje, el año de inicio. «Avance» se marca siempre.
- Dimensiones (sexo, titularidad, etapa, competencia) en la ficha (`dimensiones`, o `variantes` en las antiguas); la
  primera opción es la de por defecto; cada variante usa su último periodo con dato. `intervalo: true` (PISA): puntos con
  intervalo al 95 %, mapa en tres grupos frente a España, sin puestos. `no_comparable` (Cataluña en PISA): fuera de mapa,
  gráficos y tablas; su cifra solo en su ficha con el aviso de la fuente. `reparto: true` añade la
  vista de barras al 100 %; `resumen: true`, la tarjeta del Resumen; `encuesta: true`, sin puestos y con avisos de muestra.
- `src/lib/app/datos-app.ts` une fichas y observaciones (`REGISTRO`) y hace fallar la compilación si una cifra no tiene
  ficha, fuente con enlace, estado o valor dentro del rango plausible. Solo se muestran los temas con datos.
- `src/lib/app/ui.ts` pinta todo con DOM imperativo (adaptado de sanidad); `esqueleto.ts` es el HTML fijo.
- Datos primero: explicaciones plegadas con `plegable()`. Ceuta y Melilla aparte (gestión directa del Ministerio y
  muestras pequeñas): no cambian los colores del mapa ni se comparan con las 17.

## Reglas de datos

- Ninguna cifra a mano en el código. Todo sale de `src/data/`, generado por los scripts desde `datos-originales/`.
- Cada cifra lleva periodo, estado (previsión / avance / provisional / definitivo), fuente con enlace y fiabilidad
  (A oficial periódica, B oficial con limitaciones, C estudio). Los C, en un bloque aparte «Estudios, no estadística oficial».
- España = dato oficial (ponderado), no la media de las comunidades. Decirlo.
- Encuestas (EPA): sin puestos del 1 al 17. PISA: nunca rankings; puntuación con intervalo de confianza; si no hay dato
  comparable (p. ej. por exclusiones), decir «sin dato comparable» con la explicación.
- Alumnos por profesor ≠ alumnos por grupo; no calcular coste por alumno pública/concertada (series separadas).
- Si un dato no existe, decirlo; no rellenar. Nunca explicar saltos por nuestra cuenta: solo lo que diga la fuente.
- Rupturas de serie: tal como las marque cada fuente. Leyes: fecha del BOE, no de aplicación; no sugerir causas.

## Flujo de datos

1. `python scripts/descargar.py [fuente…]` → `datos-originales/<fuente>/<fecha>/` + `datos-originales/manifest.json`
   (URL, fecha, sha256). Los originales no se editan.
2. `python scripts/extraer_<fuente>.py` → `src/data/observaciones/<fuente>.json` (esquema largo: `indicador_id`,
   `territorio` INE 00-19 o `UE27`, `periodo`, `titularidad`, `sexo`, `etapa`, `valor`, `unidad`, `error_estandar`,
   `estado`, `fuente_id`, `url_fuente`, `fecha_captura`) y comprobaciones propias de la fuente.
3. Ficha del indicador a mano en `src/data/indicadores/<id>.json` (definición, numerador, denominador, qué no mide,
   fiabilidad, fuentes, avisos, rango plausible, `revisado_hasta`) y alta en `REGISTRO` de `datos-app.ts`.
- `extraer_abandono.py`: EDUCAbase `indi_01.px` + Eurostat (comprueba cada valor, ≤ 0,1 puntos; marca «u» = baja fiabilidad).
- `extraer_educabase.py`: seis indicadores de EDUCAbase (titularidad, 0-2 años, extranjeros, alumnos por profesor,
  idoneidad a los 15, repetición en ESO). Recalcula lo que puede; guarda las diferencias (la web las enumera) y se para
  solo si las hay en el último curso. Notas de cada tabla con las comunidades y cursos que las citan.
- Gasto: el «% del PIB» por administración de EDUCAbase es sobre el PIB de España, no el regional: no usarlo para comparar.
- `extraer_educabase.py` también genera `alumnos_unidad` (alumnos por grupo por etapa, fuente «unidades») y `alumnado_nee`
  (fuente «nee», tabla acnee_02 de cada curso, leída por posición: en 2024-25 repite la etiqueta «TOTAL»).
- `extraer_pisa.py`: tablas del informe PISA 2025 del INEE (RAR; necesita UnRAR de WinRAR). Comprueba que las cifras
  cuadran entre hojas y que ninguna tabla pierde una comunidad (hay erratas de nombre en la fuente: alias).
- `extraer_cifras.py`: tablas Excel de «Las cifras de la educación» (C2.9 graduación, B4.6 gasto por alumno, B5.5 becas en
  Bachillerato y FP comprobadas con B5.3/B5.4; fuente «cifras», xlsx solo en local). Las becas usan también la tabla 2 de
  EDUCAbase becas (fuente «becas») para el aviso de la ficha `becas_bach_fp`, que el script exige que cuadre.
- `extraer_hitos.py`: leyes desde las fichas XML del BOE → `src/data/hitos.json`.
- Un salto > 15 % frente al periodo anterior posterior a `revisado_hasta` hace fallar los tests: revisarlo y subir la fecha.

## Comandos

- `npm run dev` (http://localhost:3000) · `npm test` · `npm run build` (exporta a `out/`).
- En PowerShell, `npm.cmd` / `npx.cmd`. Ejecutar los tests desde `C:\Proyectos\educacion-ccaa` (C mayúscula).
