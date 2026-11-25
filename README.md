# Educación por comunidades

Datos oficiales del sistema educativo de las 17 comunidades autónomas (con Ceuta y Melilla aparte). Cada cifra lleva su
año, su estado, su fuente y su fiabilidad. Proyecto hermano de [Sanidad por comunidades](https://sanidad-ccaa.vercel.app/)
y [Presupuestos por comunidades](https://presupuestos-ccaa.vercel.app/).

## Datos

- Abandono temprano de la educación y la formación, 2002-2025: Ministerio de Educación, Formación Profesional y Deportes
  (explotación de las variables educativas de la EPA del INE), comprobado con Eurostat; UE-27 de Eurostat.
- Alumnado por titularidad (pública, concertada, privada), escolarización de 0 a 2 años, alumnado extranjero, alumnos
  por profesor, idoneidad a los 15 años y repetición en ESO: Ministerio de Educación, EDUCAbase (Estadística de las
  Enseñanzas no universitarias y del Profesorado).
- Leyes: fichas del Boletín Oficial del Estado.

Los ficheros originales están en `datos-originales/` y en `datos-originales/manifest.json` (dirección de descarga, fecha y
sha256).

## Uso

```
python scripts/descargar.py          # descarga las fuentes
python scripts/extraer_abandono.py   # genera src/data/observaciones/abandono.json
python scripts/extraer_educabase.py  # genera los indicadores de EDUCAbase
python scripts/extraer_insercion.py  # empleo de los titulados de FP
python scripts/extraer_hitos.py      # genera src/data/hitos.json
npm install
npm test
npm run dev
```
