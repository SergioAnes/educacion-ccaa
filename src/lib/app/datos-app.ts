/**
 * Prepara, en compilación, el paquete de datos que usa la interfaz (src/lib/app/ui.ts).
 * Todo sale de src/data (generado por los scripts de scripts/); aquí solo se reordena.
 * La compilación falla si una cifra no tiene ficha de indicador o fuente (ver comprobarIndicador).
 */
import territoriosJson from "@/data/territorios.json";
import mapaJson from "@/data/mapa-ccaa.json";
import hitosJson from "@/data/hitos.json";
import abandonoFicha from "@/data/indicadores/abandono_temprano.json";
import abandonoObs from "@/data/observaciones/abandono.json";
import titularidadFicha from "@/data/indicadores/alumnado_titularidad.json";
import titularidadObs from "@/data/observaciones/alumnado_titularidad.json";
import escolarizacionFicha from "@/data/indicadores/escolarizacion_0_2.json";
import escolarizacionObs from "@/data/observaciones/escolarizacion_0_2.json";
import extranjeroFicha from "@/data/indicadores/alumnado_extranjero.json";
import extranjeroObs from "@/data/observaciones/alumnado_extranjero.json";
import profesorFicha from "@/data/indicadores/alumnos_profesor.json";
import profesorObs from "@/data/observaciones/alumnos_profesor.json";
import unidadFicha from "@/data/indicadores/alumnos_unidad.json";
import unidadObs from "@/data/observaciones/alumnos_unidad.json";
import idoneidadFicha from "@/data/indicadores/idoneidad_15.json";
import idoneidadObs from "@/data/observaciones/idoneidad_15.json";
import repeticionFicha from "@/data/indicadores/repeticion_eso.json";
import repeticionObs from "@/data/observaciones/repeticion_eso.json";
import graduacionFicha from "@/data/indicadores/tasa_graduacion.json";
import graduacionObs from "@/data/observaciones/tasa_graduacion.json";
import pisaFicha from "@/data/indicadores/pisa_puntuacion.json";
import pisaObs from "@/data/observaciones/pisa_puntuacion.json";
import pisaBajoFicha from "@/data/indicadores/pisa_bajo.json";
import pisaBajoObs from "@/data/observaciones/pisa_bajo.json";
import pisaAltoFicha from "@/data/indicadores/pisa_alto.json";
import pisaAltoObs from "@/data/observaciones/pisa_alto.json";

/** Dimensiones en las que una serie puede variar. La clave de una variante es «sexo|titularidad|etapa|competencia». */
export const DIMS = ["sexo", "titularidad", "etapa", "competencia"] as const;
export type Dim = (typeof DIMS)[number];
export type Combinacion = Partial<Record<Dim, string>>;
export const clave = (c: Combinacion = {}) => DIMS.map((d) => c[d] ?? "total").join("|");
export const ETIQUETA_DIM: Record<Dim, string> = { sexo: "Sexo", titularidad: "Titularidad", etapa: "Etapa", competencia: "Competencia" };

export type Territorio = { id: string; ine: string; nombre: string; abr: string; nuts2: string; alias: string[]; ciudad?: boolean };
export type Fuente = { id: string; nombre: string; corto?: string; url: string };
/** Variante de las fichas antiguas (una sola dimensión): sexo o titularidad, con su etiqueta. */
export type Variante = { sexo?: string; titularidad?: string; etiqueta: string };
export type Dimension = { dim: Dim; nombre: string; opciones: { id: string; etiqueta: string }[] };
export type Referencia = { id: string; nombre: string; fuente_id: string; ranking: boolean; evolucion: boolean };
export type Ficha = {
  id: string; grupo: string; nombre: string; corto: string; que: string; unidad: string; unidad_txt?: string;
  definicion: string; numerador: string; denominador: string; no_mide: string;
  fiabilidad: "A" | "B" | "C"; fiabilidad_txt: string; estado: string; fuentes: Fuente[]; espana: string; avisos: string[];
  objetivo?: { valor: number; texto: string; fuente: string; url: string; nota: string };
  /** Encuesta o muestra: sin puestos y con avisos de margen de error */
  encuesta?: boolean;
  /** Cada cifra tiene error típico: se muestra con su intervalo al 95 % */
  intervalo?: boolean;
  /** Va en las tarjetas del Resumen */
  resumen?: boolean;
  variantes?: Variante[];
  dimensiones?: Dimension[];
  /** Filas que se muestran en «Tu comunidad» (la combinación de dimensiones de cada una) */
  filas_ficha?: Combinacion[];
  /** Las variantes son partes de un todo (suman 100 %): vista «Reparto» con barras al 100 % */
  reparto?: boolean;
  aditivo?: boolean;
  referencias?: Referencia[];
  no_comparable_txt?: string;
  rango: [number, number]; rango_nota?: string; revisado_hasta: string; revision?: string;
};
export type Fila = {
  indicador_id: string; territorio: string; periodo: string; titularidad: string; sexo: string; etapa: string; competencia?: string;
  valor: number; unidad: string; error_estandar: number | null; estado: string; fuente_id: string; url_fuente: string;
  fecha_captura: string; baja_fiabilidad?: boolean; marca_eurostat?: string;
};
export type Diferencia = { territorio: string; periodo: string; titularidad?: string; etapa?: string; publicado: number; calculado: number };
export type Observaciones = {
  indicador_id: string; periodos: string[]; notas_fuente: string[];
  notas?: { texto: string; territorios: string[]; periodos: string[]; etapa?: string }[];
  muestra_pequena: string[];
  rupturas: { territorio: string; anio: number; fuente_id: string; texto: string }[];
  definicion_difiere_es: number[];
  no_comparable?: { territorio: string; texto: string }[];
  cautela?: { territorio: string; texto: string }[];
  cambios?: { territorio: string; competencia: string; desde: string; hasta: string; diferencia: number; error_estandar: number | null; nota?: string }[];
  comprobacion: {
    pares_comparados: number; descripcion?: string; coinciden?: number; tolerancia?: number; tolerancia_puntos?: number;
    diferencias?: Diferencia[]; diferencias_mayores_que_redondeo?: unknown[];
  };
  filas: Fila[];
};

/** Temas de la vista Datos, en orden. Solo se muestran los que ya tienen indicadores (más «Resumen», en la interfaz). */
export const TEMAS: { id: string; nombre: string }[] = [
  { id: "centros", nombre: "Centros y alumnado" },
  { id: "profesorado", nombre: "Profesorado y aulas" },
  { id: "resultados", nombre: "Resultados (PISA)" },
  { id: "equidad", nombre: "Equidad" },
  { id: "trayectorias", nombre: "Trayectorias" },
  { id: "financiacion", nombre: "Financiación" },
];

const par = (ficha: unknown, obs: unknown) => ({ ficha: ficha as Ficha, obs: obs as Observaciones });
/** Registro de indicadores: ficha (qué mide) + observaciones (cifras). Cada uno nuevo se añade aquí. */
export const REGISTRO: { ficha: Ficha; obs: Observaciones }[] = [
  par(titularidadFicha, titularidadObs),
  par(escolarizacionFicha, escolarizacionObs),
  par(extranjeroFicha, extranjeroObs),
  par(unidadFicha, unidadObs),
  par(profesorFicha, profesorObs),
  par(pisaFicha, pisaObs),
  par(pisaBajoFicha, pisaBajoObs),
  par(pisaAltoFicha, pisaAltoObs),
  par(abandonoFicha, abandonoObs),
  par(idoneidadFicha, idoneidadObs),
  par(repeticionFicha, repeticionObs),
  par(graduacionFicha, graduacionObs),
];

export const TERRITORIOS = territoriosJson as Territorio[];
const POR_INE = Object.fromEntries(TERRITORIOS.map((t) => [t.ine, t]));

/** Dimensiones de una ficha: las declaradas o, en las fichas antiguas, la única que cambia en sus variantes. */
export function dimensionesDe(ficha: Ficha): Dimension[] {
  if (ficha.dimensiones) return ficha.dimensiones;
  if (!ficha.variantes) return [];
  const dim: Dim = ficha.variantes.some((v) => v.sexo && v.sexo !== "total") ? "sexo" : "titularidad";
  return [{ dim, nombre: ETIQUETA_DIM[dim], opciones: ficha.variantes.map((v) => ({ id: (dim === "sexo" ? v.sexo : v.titularidad) ?? "total", etiqueta: v.etiqueta })) }];
}

/** Comprueba lo que exige el brief antes de que una cifra llegue a la web: ficha, fuente con enlace y rangos. */
export function comprobarIndicador(ficha: Ficha | undefined, obs: Observaciones): string[] {
  const err: string[] = [];
  if (!ficha) return [`${obs.indicador_id}: no tiene ficha en src/data/indicadores/`];
  if (ficha.id !== obs.indicador_id) err.push(`${ficha.id}: la ficha no corresponde a las observaciones (${obs.indicador_id})`);
  if (!ficha.fuentes.length || ficha.fuentes.some((f) => !/^https:\/\//.test(f.url))) err.push(`${ficha.id}: fuente sin enlace`);
  if (!["A", "B", "C"].includes(ficha.fiabilidad)) err.push(`${ficha.id}: fiabilidad desconocida`);
  if (!TEMAS.some((t) => t.id === ficha.grupo)) err.push(`${ficha.id}: tema desconocido ${ficha.grupo}`);
  const ids = new Set(ficha.fuentes.map((f) => f.id));
  const refs = new Set((ficha.referencias ?? []).map((r) => r.id));
  const dims = dimensionesDe(ficha);
  for (const c of ficha.filas_ficha ?? []) {
    for (const [d, v] of Object.entries(c)) if (!dims.some((x) => x.dim === d && x.opciones.some((o) => o.id === v))) err.push(`${ficha.id}: fila de la ficha con ${d}=${v} desconocido`);
  }
  for (const f of obs.filas) {
    if (!f.url_fuente || !ids.has(f.fuente_id)) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: sin fuente`);
    if (!["prevision", "avance", "provisional", "definitivo"].includes(f.estado)) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: estado desconocido`);
    if (f.valor < ficha.rango[0] || f.valor > ficha.rango[1]) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: ${f.valor} fuera del rango plausible`);
    if (!refs.has(f.territorio) && !POR_INE[f.territorio]) err.push(`${ficha.id}: territorio desconocido ${f.territorio}`);
    if (ficha.intervalo && f.error_estandar == null && !refs.has(f.territorio)) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: sin error típico`);
    for (const d of DIMS) {
      const v = (f as Record<string, unknown>)[d] as string | undefined;
      if (v && v !== "total" && !dims.some((x) => x.dim === d && x.opciones.some((o) => o.id === v))) err.push(`${ficha.id}: ${d}=${v} no está en la ficha`);
    }
  }
  return err;
}

const nf = (d: number) => new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: true });

/** Qué se comprobó al generar los datos, en una frase (sale de la propia salida del script). */
export function textoComprobacion(obs: Observaciones): string {
  const c = obs.comprobacion;
  if (obs.indicador_id === "abandono_temprano")
    return `Las ${nf(0).format(c.pares_comparados)} cifras del Ministerio que también publica Eurostat coinciden (diferencia máxima de 0,1 puntos, por redondeo).`;
  if (obs.indicador_id === "alumnado_titularidad")
    return `En cada curso y comunidad, pública + concertada + privada no concertada = total; la suma de las comunidades (con Ceuta y Melilla) da España; los ${nf(0).format(c.pares_comparados)} recuentos coinciden con la serie de alumnado del Ministerio, y el porcentaje de la pública, con el que publica el Ministerio.`;
  if (obs.indicador_id === "pisa_puntuacion")
    return "Las cifras de España y de las comunidades son las mismas en las tablas de 2025, en las de evolución y en las de diferencias entre ediciones, y cada diferencia publicada es la resta de sus dos medias. Excepción: en la tabla de ciencias 2015-2025, las diferencias de Castilla y León y de Castilla-La Mancha vienen intercambiadas (ver sus notas).";
  if (obs.indicador_id.startsWith("pisa_"))
    return "Los porcentajes de todos los niveles de cada territorio suman 100 (con la tolerancia del redondeo).";
  if (c.coinciden != null)
    return `Recalculado con las series del Ministerio (${c.descripcion?.replace(/^publicado = /, "")}): coincide en ${nf(0).format(c.coinciden)} de ${nf(0).format(c.pares_comparados)} casos (diferencia de 0,05 como mucho). La web muestra siempre el dato publicado.`;
  return "Dato publicado tal cual por el Ministerio.";
}

type Serie = (number | null)[];
export type IndApp = Omit<Ficha, "rango" | "rango_nota" | "revisado_hasta" | "revision" | "variantes" | "dimensiones" | "referencias"> & {
  /** Año de inicio de cada periodo (para el eje); la etiqueta es «2024», «2024-25»… */
  periodos: number[];
  etiquetas: string[];
  /** Índices de los periodos que la fuente da como avance */
  avance: number[];
  dims: Dimension[];
  /** Combinaciones con datos, en el orden de las dimensiones */
  variantes: { clave: string; etiqueta: string }[];
  /** variante -> id de territorio (AN…ML, ES) o de referencia -> valor por periodo */
  serie: Record<string, Record<string, Serie>>;
  /** Igual, con el error típico (solo si la ficha tiene «intervalo») */
  et: Record<string, Record<string, Serie>>;
  refs: { id: string; nombre: string; ranking: boolean; evolucion: boolean; fuente: string }[];
  /** variante -> id -> índices de periodo con baja fiabilidad según Eurostat */
  baja: Record<string, Record<string, number[]>>;
  muestraPequena: string[];
  noComparable: Record<string, string>;
  cautelas: Record<string, string>;
  cambios: { territorio: string; clave: string; desde: string; hasta: string; diferencia: number; et: number | null; nota?: string }[];
  rupturas: { territorio: string; anio: number; fuente: string; texto: string }[];
  definicionDifiere: number[];
  notas: { texto: string; territorios: string[]; periodos: string[]; clave?: string }[];
  comprobacion: string;
  diferencias: { territorio: string; periodo: string; variante: string; publicado: number; calculado: number }[];
  fechaCaptura: string;
};

function construirIndicador(ficha: Ficha, obs: Observaciones): IndApp {
  const errores = comprobarIndicador(ficha, obs);
  if (errores.length) throw new Error("Datos sin la información mínima:\n" + errores.slice(0, 20).join("\n"));
  const etiquetas = obs.periodos;
  const periodos = etiquetas.map((p) => Number(p.slice(0, 4)));
  const vacia = (): Serie => periodos.map(() => null);
  const dims = dimensionesDe(ficha);
  const refs = new Set((ficha.referencias ?? []).map((r) => r.id));
  const serie: IndApp["serie"] = {}, et: IndApp["et"] = {}, baja: IndApp["baja"] = {};
  const avance = new Set<number>();
  const idDe = (t: string) => (refs.has(t) || t === "todas" || t === "UE27" ? t : POR_INE[t].id);
  for (const f of obs.filas) {
    const i = etiquetas.indexOf(f.periodo), k = clave(f as Combinacion), id = idDe(f.territorio);
    if (f.estado === "avance") avance.add(i);
    ((serie[k] ??= {})[id] ??= vacia())[i] = f.valor;
    if (ficha.intervalo && f.error_estandar != null) ((et[k] ??= {})[id] ??= vacia())[i] = f.error_estandar;
    if (f.baja_fiabilidad) ((baja[k] ??= {})[id] ??= []).push(i);
  }
  // Variantes: las combinaciones de las opciones de cada dimensión que tienen dato de España, en el orden de la ficha
  let combos: Combinacion[] = [{}];
  for (const d of dims) combos = combos.flatMap((c) => d.opciones.map((o) => ({ ...c, [d.dim]: o.id })));
  const variantes = combos.filter((c) => serie[clave(c)]?.ES).map((c) => ({
    clave: clave(c),
    etiqueta: dims.map((d) => d.opciones.find((o) => o.id === c[d.dim])?.etiqueta).filter(Boolean).join(" · ") || "Total",
  }));
  const nombreFuente = Object.fromEntries(ficha.fuentes.map((f) => [f.id, f.nombre]));
  // Notas de la fuente: las que solo citan cursos anteriores a la serie que mostramos no se enseñan
  const notas = (obs.notas ?? obs.notas_fuente.map((texto) => ({ texto, territorios: [] as string[], periodos: [] as string[] })))
    .filter((n) => !n.periodos.length || n.periodos.some((p) => p >= etiquetas[0]))
    .map((n) => ({ texto: n.texto.replace(/\s+/g, " "), territorios: n.territorios.map(idDe), periodos: n.periodos,
      ...("etapa" in n && n.etapa ? { clave: `etapa:${n.etapa}` } : {}) }));
  const { rango: _r, rango_nota: _rn, revisado_hasta: _rh, revision: _rv, variantes: _v, dimensiones: _d, referencias: _rf, ...resto } = ficha;
  return {
    ...resto,
    periodos, etiquetas, avance: [...avance].sort((a, b) => a - b), dims, variantes,
    serie, et, baja,
    refs: (ficha.referencias ?? []).map((r) => ({ id: r.id, nombre: r.nombre, ranking: r.ranking, evolucion: r.evolucion, fuente: nombreFuente[r.fuente_id] ?? r.fuente_id })),
    muestraPequena: obs.muestra_pequena.map((ine) => POR_INE[ine].id),
    noComparable: Object.fromEntries((obs.no_comparable ?? []).map((n) => [POR_INE[n.territorio].id, n.texto])),
    cautelas: Object.fromEntries((obs.cautela ?? []).map((n) => [POR_INE[n.territorio].id, n.texto])),
    cambios: (obs.cambios ?? []).map((c) => ({ territorio: idDe(c.territorio), clave: clave({ competencia: c.competencia }), desde: c.desde, hasta: c.hasta,
      diferencia: c.diferencia, et: c.error_estandar, ...(c.nota ? { nota: c.nota } : {}) })),
    rupturas: obs.rupturas.map((r) => ({ territorio: idDe(r.territorio), anio: r.anio, fuente: nombreFuente[r.fuente_id] ?? r.fuente_id, texto: r.texto })),
    definicionDifiere: obs.definicion_difiere_es,
    notas,
    comprobacion: textoComprobacion(obs),
    diferencias: (obs.comprobacion.diferencias ?? []).map((d) => ({
      territorio: POR_INE[d.territorio].id, periodo: d.periodo, variante: clave({ titularidad: d.titularidad, etapa: d.etapa }), publicado: d.publicado, calculado: d.calculado,
    })),
    fechaCaptura: obs.filas.reduce((m, f) => (f.fecha_captura > m ? f.fecha_captura : m), ""),
  };
}

export type Hito = { id: string; corto: string; tipo: string; titulo: string; fecha: string; anio: number; url: string };

export type DatosApp = {
  ccaa: { id: string; nombre: string; abr: string }[];
  ciudades: { id: string; nombre: string; abr: string }[];
  geo: typeof mapaJson;
  temas: { id: string; nombre: string }[];
  inds: IndApp[];
  hitos: Hito[];
};

export function construirDatos(): DatosApp {
  const inds = REGISTRO.map(({ ficha, obs }) => construirIndicador(ficha, obs));
  const corto = (t: Territorio) => ({ id: t.id, nombre: t.nombre, abr: t.abr });
  return {
    ccaa: TERRITORIOS.filter((t) => t.id !== "ES" && !t.ciudad).map(corto),
    ciudades: TERRITORIOS.filter((t) => t.ciudad).map(corto),
    geo: mapaJson,
    temas: TEMAS.filter((t) => inds.some((i) => i.grupo === t.id)),
    inds,
    hitos: (hitosJson as Hito[]).map(({ id, corto, tipo, titulo, fecha, anio, url }) => ({ id, corto, tipo, titulo, fecha, anio, url })),
  };
}
