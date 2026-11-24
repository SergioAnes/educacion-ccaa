/**
 * «Cómo leer los datos»: las siete trampas del brief (§6), cada una con de dónde sale el dato, qué denominador usa
 * y qué no mide. Sin cifras: cuando el indicador esté en la web, sus números saldrán de los datos, no de aquí.
 * Texto en HTML sencillo (contenido propio).
 */
export type Trampa = { titulo: string; origen: string; denominador: string; noMide: string; enWeb?: string };

export const TRAMPAS: Trampa[] = [
  {
    titulo: "Coste por alumno: pública frente a concertada",
    origen: "La Estadística del Gasto Público en Educación del Ministerio recoge lo que gastan las administraciones, y dentro de ello lo que pagan a los centros concertados (los conciertos).",
    denominador: "Si se divide el gasto en conciertos entre el alumnado de la concertada, y el resto del gasto entre el de la pública, los dos cocientes no cubren los mismos gastos: el concierto no paga todo lo que cuesta una plaza concertada, y el gasto de la red pública incluye partidas que no son de un alumno concreto (servicios de la administración, transporte, comedor, educación especial…). Además, las dos redes no tienen por qué escolarizar al mismo alumnado ni en las mismas etapas.",
    noMide: "Ni el coste real de una plaza en cada red ni cuál es más eficiente.",
    enWeb: "Por eso esta web no calcula un «coste por alumno» de cada red: mostrará el gasto en conciertos y el alumnado concertado como series separadas.",
  },
  {
    titulo: "Alumnos por profesor no es alumnos por clase",
    origen: "Las dos cifras salen de la Estadística de las Enseñanzas no universitarias del Ministerio y aparecen en su Sistema Estatal de Indicadores de la Educación.",
    denominador: "«Alumnos por profesor» divide el alumnado entre todo el profesorado, también el que no tiene un grupo propio (apoyos, desdobles, orientación, especialistas, equipos directivos). «Alumnos por grupo» divide el alumnado entre los grupos o aulas.",
    noMide: "La primera cifra no es el tamaño de la clase: siempre sale bastante más baja que la segunda.",
    enWeb: "En esta web nunca irán en el mismo gráfico sin decir cuál es cuál.",
  },
  {
    titulo: "PISA: entre ediciones y entre comunidades",
    origen: "PISA es una evaluación de la OCDE a una muestra de alumnos de 15 años cada pocos años. Las comunidades que amplían su muestra tienen resultado propio.",
    denominador: "Es una muestra, no todo el alumnado: cada puntuación tiene un margen de error. Una parte del alumnado se excluye de la prueba (por ejemplo, por necesidades educativas o por desconocer el idioma), y ese porcentaje cambia entre comunidades y ediciones. La prueba pasó de papel a ordenador en 2015, y el índice socioeconómico (ESCS) se ha recalculado entre ediciones.",
    noMide: "Diferencias pequeñas de puntos no suelen ser significativas, y un cambio entre ediciones puede venir de la prueba o de la muestra. Tampoco mide todo lo que se aprende en la escuela.",
    enWeb: "La web no hará rankings con PISA: mostrará cada puntuación con su intervalo de confianza. Si la OCDE no da un dato comparable de una comunidad, se dirá «sin dato comparable» con la explicación, nunca un hueco ni un cero.",
  },
  {
    titulo: "Abandono temprano no es fracaso escolar",
    origen: "Sale de la Encuesta de Población Activa del INE, con la definición de Eurostat; el Ministerio publica la serie por comunidad.",
    denominador: "Jóvenes de 18 a 24 años que viven en la comunidad. Cuenta a los que, como mucho, tienen la ESO y no estudian ni se forman.",
    noMide: "No es el porcentaje de alumnos que no titulan en la ESO: quien tiene la ESO y no sigue estudiando cuenta como abandono, y quien no la tiene pero estudia, no. Se cuenta donde vive el joven, no donde estudió. Al ser una encuesta, en las comunidades pequeñas el margen de error es grande.",
    enWeb: "Ya está en la web: tema «Trayectorias».",
  },
  {
    titulo: "Ministerio frente a OCDE",
    origen: "El Ministerio publica el gasto público en educación; la OCDE (Education at a Glance) publica el gasto en instituciones educativas con una metodología común internacional.",
    denominador: "No suman lo mismo: el Ministerio cuenta el gasto de las administraciones (también becas y otras partidas), y la OCDE, el gasto en centros educativos, público y privado, con sus propias reglas. Por eso el «gasto en educación sobre el PIB» de una y otra fuente no coincide. Con los salarios pasa algo parecido: la OCDE y Eurydice comparan salarios reglamentarios (lo que fija la norma), no lo que cobra cada docente en nómina.",
    noMide: "Una cifra no corrige a la otra: miden cosas distintas.",
    enWeb: "La web dirá siempre de qué fuente es cada cifra de gasto y no mezclará las dos.",
  },
  {
    titulo: "Interinidad, segregación y acoso: cifras de estudios",
    origen: "No hay una estadística oficial periódica, por comunidad y con un método común, para estos tres temas. Las cifras que circulan salen de estudios, sindicatos, encuestas propias o explotaciones de PISA.",
    denominador: "Cada estudio usa el suyo: la segregación depende del índice elegido y de los datos de partida; la interinidad, de qué docentes se cuentan y en qué fecha; el acoso, de cómo se pregunta.",
    noMide: "Dos estudios pueden dar cifras muy distintas sin que ninguno esté mal. No sirven para seguir la evolución año a año.",
    enWeb: "Si se incluyen, irán marcados con la letra C, en un bloque aparte: «Estudios, no estadística oficial».",
  },
  {
    titulo: "Escolarización de 0 a 3 años no es plazas públicas",
    origen: "La Estadística de las Enseñanzas no universitarias cuenta los niños matriculados en centros autorizados, públicos y privados.",
    denominador: "La tasa de escolarización divide los niños matriculados entre todos los niños de esa edad.",
    noMide: "Ni cuántas plazas públicas hay ni cuántas familias se quedan sin plaza. No hemos encontrado una estadística oficial periódica de plazas públicas de 0 a 3 años por comunidad; si la hay, la añadiremos.",
  },
];
