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
import idoneidadFicha from "@/data/indicadores/idoneidad_15.json";
import idoneidadObs from "@/data/observaciones/idoneidad_15.json";
import repeticionFicha from "@/data/indicadores/repeticion_eso.json";
import repeticionObs from "@/data/observaciones/repeticion_eso.json";

export type Sexo = "total" | "h" | "m";

export type Territorio = { id: string; ine: string; nombre: string; abr: string; nuts2: string; alias: string[]; ciudad?: boolean };
export type Fuente = { id: string; nombre: string; corto?: string; url: string };
/** Una variante de la serie: sexo o titularidad del centro. La clave es «sexo|titularidad». */
export type Variante = { sexo?: Sexo; titularidad?: string; etiqueta: string };
export type Ficha = {
  id: string; grupo: string; nombre: string; corto: string; que: string; unidad: string;
  definicion: string; numerador: string; denominador: string; no_mide: string;
  fiabilidad: "A" | "B" | "C"; fiabilidad_txt: string; estado: string; fuentes: Fuente[]; espana: string; avisos: string[];
  objetivo?: { valor: number; texto: string; fuente: string; url: string; nota: string };
  /** Encuesta: sin puestos y con aviso de margen de error */
  encuesta?: boolean;
  /** Va en las tarjetas del Resumen */
  resumen?: boolean;
  variantes?: Variante[];
  /** Variantes que se muestran como filas en «Tu comunidad» */
  filas_ficha?: string[];
  /** Las variantes son partes de un todo (suman 100 %): vista «Reparto» con barras al 100 % */
  reparto?: boolean;
  aditivo?: boolean;
  rango: [number, number]; rango_nota?: string; revisado_hasta: string; revision?: string;
};
export type Fila = {
  indicador_id: string; territorio: string; periodo: string; titularidad: string; sexo: Sexo; etapa: string;
  valor: number; unidad: string; error_estandar: number | null; estado: string; fuente_id: string; url_fuente: string;
  fecha_captura: string; baja_fiabilidad?: boolean; marca_eurostat?: string;
};
export type Diferencia = { territorio: string; periodo: string; titularidad?: string; publicado: number; calculado: number };
export type Observaciones = {
  indicador_id: string; periodos: string[]; notas_fuente: string[];
  notas?: { texto: string; territorios: string[]; periodos: string[] }[];
  muestra_pequena: string[];
  rupturas: { territorio: string; anio: number; fuente_id: string; texto: string }[];
  definicion_difiere_es: number[];
  comprobacion: {
    pares_comparados: number; descripcion?: string; coinciden?: number; tolerancia?: number; tolerancia_puntos?: number;
    diferencias?: Diferencia[]; diferencias_mayores_que_redondeo?: unknown[];
  };
  filas: Fila[];
};

/** Temas de la vista Datos, en orden. Solo se muestran los que ya tienen indicadores (más «Resumen», en la interfaz). */
export const TEMAS: { id: string; nombre: string }[] = [
  { id: "centros", nombre: "Centros y alumnado" },
  { id: "profesorado", nombre: "Profesorado" },
  { id: "resultados", nombre: "Resultados" },
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
  par(profesorFicha, profesorObs),
  par(abandonoFicha, abandonoObs),
  par(idoneidadFicha, idoneidadObs),
  par(repeticionFicha, repeticionObs),
];

export const TERRITORIOS = territoriosJson as Territorio[];
const POR_INE = Object.fromEntries(TERRITORIOS.map((t) => [t.ine, t]));
export const clave = (sexo = "total", titularidad = "total") => `${sexo}|${titularidad}`;

/** Comprueba lo que exige el brief antes de que una cifra llegue a la web: ficha, fuente con enlace y rangos. */
export function comprobarIndicador(ficha: Ficha | undefined, obs: Observaciones): string[] {
  const err: string[] = [];
  if (!ficha) return [`${obs.indicador_id}: no tiene ficha en src/data/indicadores/`];
  if (ficha.id !== obs.indicador_id) err.push(`${ficha.id}: la ficha no corresponde a las observaciones (${obs.indicador_id})`);
  if (!ficha.fuentes.length || ficha.fuentes.some((f) => !/^https:\/\//.test(f.url))) err.push(`${ficha.id}: fuente sin enlace`);
  if (!["A", "B", "C"].includes(ficha.fiabilidad)) err.push(`${ficha.id}: fiabilidad desconocida`);
  if (!TEMAS.some((t) => t.id === ficha.grupo)) err.push(`${ficha.id}: tema desconocido ${ficha.grupo}`);
  const ids = new Set(ficha.fuentes.map((f) => f.id));
  const variantes = new Set((ficha.variantes ?? [{ etiqueta: "Total" } as Variante]).map((v) => clave(v.sexo, v.titularidad)));
  for (const k of ficha.filas_ficha ?? []) if (!variantes.has(k) && k !== "total|total") err.push(`${ficha.id}: fila de la ficha sin variante ${k}`);
  for (const f of obs.filas) {
    if (!f.url_fuente || !ids.has(f.fuente_id)) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: sin fuente`);
    if (!["prevision", "avance", "provisional", "definitivo"].includes(f.estado)) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: estado desconocido`);
    if (f.valor < ficha.rango[0] || f.valor > ficha.rango[1]) err.push(`${ficha.id} ${f.territorio} ${f.periodo}: ${f.valor} fuera del rango plausible`);
    if (f.territorio !== "UE27" && !POR_INE[f.territorio]) err.push(`${ficha.id}: territorio desconocido ${f.territorio}`);
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
  if (c.coinciden != null)
    return `Recalculado con las series del Ministerio (${c.descripcion?.replace(/^publicado = /, "")}): coincide en ${nf(0).format(c.coinciden)} de ${nf(0).format(c.pares_comparados)} casos (diferencia de 0,05 como mucho). La web muestra siempre el dato publicado.`;
  return "Dato publicado tal cual por el Ministerio.";
}

type Serie = (number | null)[];
export type IndApp = Omit<Ficha, "rango" | "rango_nota" | "revisado_hasta" | "revision" | "variantes"> & {
  /** Año de inicio de cada periodo (para el eje); la etiqueta es «2024» o «2024-25» */
  periodos: number[];
  etiquetas: string[];
  /** Índices de los periodos que la fuente da como avance */
  avance: number[];
  variantes: { clave: string; etiqueta: string }[];
  /** variante -> id de territorio (AN…ML, ES) -> valor por periodo */
  serie: Record<string, Record<string, Serie>>;
  ue: Record<string, Serie> | null;
  /** variante -> id -> índices de periodo con baja fiabilidad según Eurostat */
  baja: Record<string, Record<string, number[]>>;
  muestraPequena: string[];
  rupturas: { territorio: string; anio: number; fuente: string; texto: string }[];
  definicionDifiere: number[];
  notas: { texto: string; territorios: string[]; periodos: string[] }[];
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
  const variantes = (ficha.variantes ?? [{ etiqueta: "Total" }]).map((v) => ({ clave: clave(v.sexo, v.titularidad), etiqueta: v.etiqueta }));
  const serie: IndApp["serie"] = {}, baja: IndApp["baja"] = {}, ue: Record<string, Serie> = {};
  const avance = new Set<number>();
  for (const f of obs.filas) {
    const i = etiquetas.indexOf(f.periodo), k = clave(f.sexo, f.titularidad);
    if (f.estado === "avance") avance.add(i);
    if (f.territorio === "UE27") { (ue[k] ??= vacia())[i] = f.valor; continue; }
    const id = POR_INE[f.territorio].id;
    ((serie[k] ??= {})[id] ??= vacia())[i] = f.valor;
    if (f.baja_fiabilidad) ((baja[k] ??= {})[id] ??= []).push(i);
  }
  const nombreFuente = Object.fromEntries(ficha.fuentes.map((f) => [f.id, f.nombre]));
  const idDe = (t: string) => (t === "todas" || t === "UE27" ? t : POR_INE[t].id);
  // Notas de la fuente: las que solo citan cursos anteriores a la serie que mostramos no se enseñan
  const notas = (obs.notas ?? obs.notas_fuente.map((texto) => ({ texto, territorios: [], periodos: [] })))
    .filter((n) => !n.periodos.length || n.periodos.some((p) => p >= etiquetas[0]))
    .map((n) => ({ texto: n.texto.replace(/\s+/g, " "), territorios: n.territorios.map(idDe), periodos: n.periodos }));
  const { rango: _r, rango_nota: _rn, revisado_hasta: _rh, revision: _rv, variantes: _v, ...resto } = ficha;
  return {
    ...resto,
    periodos, etiquetas, avance: [...avance].sort((a, b) => a - b), variantes,
    serie, baja, ue: Object.keys(ue).length ? ue : null,
    muestraPequena: obs.muestra_pequena.map((ine) => POR_INE[ine].id),
    rupturas: obs.rupturas.map((r) => ({ territorio: idDe(r.territorio), anio: r.anio, fuente: nombreFuente[r.fuente_id] ?? r.fuente_id, texto: r.texto })),
    definicionDifiere: obs.definicion_difiere_es,
    notas,
    comprobacion: textoComprobacion(obs),
    diferencias: (obs.comprobacion.diferencias ?? []).map((d) => ({
      territorio: POR_INE[d.territorio].id, periodo: d.periodo, variante: clave("total", d.titularidad ?? "total"), publicado: d.publicado, calculado: d.calculado,
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
