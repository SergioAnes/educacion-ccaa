/**
 * Comprobaciones que bloquean el despliegue (brief, §7). Si algo falla aquí, no se publica.
 */
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import { REGISTRO, comprobarIndicador, construirDatos, type Fila, type Ficha, type Observaciones } from "@/lib/app/datos-app";
import hitos from "@/data/hitos.json";

const RAIZ = process.cwd();
const leer = (ruta: string) => JSON.parse(readFileSync(join(RAIZ, ruta), "utf8"));
const jsons = (dir: string) => readdirSync(join(RAIZ, dir)).filter((f) => f.endsWith(".json"));

/** Cambios de más del 15 % frente al periodo anterior en la misma serie (territorio, sexo, titularidad, etapa). */
export function saltos(filas: Fila[], umbral = 0.15) {
  const series = new Map<string, Fila[]>();
  for (const f of filas) {
    const k = [f.territorio, f.sexo, f.titularidad, f.etapa, f.competencia ?? "total"].join("|");
    series.set(k, [...(series.get(k) ?? []), f]);
  }
  const out: { serie: string; periodo: string; de: number; a: number }[] = [];
  for (const [k, fs] of series) {
    const orden = fs.slice().sort((a, b) => a.periodo.localeCompare(b.periodo));
    orden.slice(1).forEach((f, i) => {
      const prev = orden[i].valor;
      if (prev !== 0 && Math.abs(f.valor / prev - 1) > umbral) out.push({ serie: k, periodo: f.periodo, de: prev, a: f.valor });
    });
  }
  return out;
}

/** En indicadores aditivos (recuentos, euros), la suma de los territorios debe dar España. */
export function sumaCuadra(filas: Fila[], tolerancia = 0.5) {
  const grupos = new Map<string, { es?: number; suma: number; n: number }>();
  for (const f of filas) {
    if (f.territorio === "UE27") continue;
    const k = [f.periodo, f.sexo, f.titularidad, f.etapa, f.competencia ?? "total"].join("|");
    const g = grupos.get(k) ?? { suma: 0, n: 0 };
    if (f.territorio === "00") g.es = f.valor; else { g.suma += f.valor; g.n++; }
    grupos.set(k, g);
  }
  return [...grupos].filter(([, g]) => g.es != null && Math.abs(g.suma - g.es) > tolerancia).map(([k, g]) => `${k}: suma ${g.suma}, España ${g.es}`);
}

describe("fichas y fuentes", () => {
  it("cada fichero de observaciones tiene su ficha y está en el registro", () => {
    const enRegistro = new Set(REGISTRO.map((r) => r.obs.indicador_id));
    const fichas = new Set(jsons("src/data/indicadores").map((f) => leer(`src/data/indicadores/${f}`).id));
    for (const f of jsons("src/data/observaciones")) {
      const id = leer(`src/data/observaciones/${f}`).indicador_id;
      expect(fichas.has(id), `${f}: falta src/data/indicadores/${id}.json`).toBe(true);
      expect(enRegistro.has(id), `${f}: añadirlo a REGISTRO en datos-app.ts`).toBe(true);
    }
    for (const f of jsons("src/data/indicadores")) expect(f).toBe(`${leer(`src/data/indicadores/${f}`).id}.json`);
  });

  it("cada indicador tiene fuente con enlace, estado, fiabilidad y valores dentro de su rango plausible", () => {
    for (const { ficha, obs } of REGISTRO) expect(comprobarIndicador(ficha, obs)).toEqual([]);
  });

  it("una cifra sin fuente o fuera de rango hace fallar la compilación", () => {
    const { ficha, obs } = REGISTRO[0];
    const mala: Observaciones = { ...obs, filas: [{ ...obs.filas[0], fuente_id: "inventada" }, { ...obs.filas[1], valor: ficha.rango[1] + 1 }] };
    expect(comprobarIndicador(ficha, mala).length).toBe(2);
    expect(comprobarIndicador(undefined, obs)[0]).toMatch(/no tiene ficha/);
    expect(() => construirDatos()).not.toThrow();
  });

  it("la web solo muestra los temas que ya tienen datos", () => {
    const d = construirDatos();
    expect(d.temas.map((t) => t.id)).toEqual([...new Set(d.inds.map((i) => i.grupo))]);
  });
});

describe("variaciones", () => {
  it("un cambio de más del 15 % frente al periodo anterior exige que la ficha esté revisada hasta ese periodo", () => {
    for (const { ficha, obs } of REGISTRO) {
      const sinRevisar = saltos(obs.filas).filter((s) => s.periodo > (ficha as Ficha).revisado_hasta);
      expect(sinRevisar, `${ficha.id}: revisar estos saltos y subir «revisado_hasta» en la ficha`).toEqual([]);
    }
  });

  it("la detección de saltos y la suma de territorios funcionan", () => {
    const base = REGISTRO[0].obs.filas[0];
    const f = (territorio: string, periodo: string, valor: number) => ({ ...base, territorio, periodo, valor });
    expect(saltos([f("01", "2020", 10), f("01", "2021", 12)]).length).toBe(1);
    expect(saltos([f("01", "2020", 10), f("01", "2021", 11)]).length).toBe(0);
    expect(sumaCuadra([f("00", "2020", 30), f("01", "2020", 10), f("02", "2020", 20)])).toEqual([]);
    expect(sumaCuadra([f("00", "2020", 31), f("01", "2020", 10), f("02", "2020", 20)]).length).toBe(1);
  });

  it("en los indicadores aditivos, la suma de los territorios es España", () => {
    for (const { ficha, obs } of REGISTRO) if ((ficha as Ficha & { aditivo?: boolean }).aditivo) expect(sumaCuadra(obs.filas)).toEqual([]);
  });
});

describe("abandono temprano", () => {
  const obs = REGISTRO.find((r) => r.ficha.id === "abandono_temprano")!.obs;
  it("tiene las 19 comunidades y ciudades, España y la UE-27 en el último año, por sexo", () => {
    const ult = obs.periodos.at(-1)!;
    for (const sexo of ["total", "h", "m"]) {
      const t = obs.filas.filter((f) => f.periodo === ult && f.sexo === sexo).map((f) => f.territorio).sort();
      expect(t).toEqual(["00", ...Array.from({ length: 19 }, (_, i) => String(i + 1).padStart(2, "0")), "UE27"]);
    }
  });
  it("se comprobó con Eurostat y las rupturas vienen de las fuentes", () => {
    expect(obs.comprobacion.pares_comparados).toBeGreaterThan(1000);
    expect(obs.rupturas.some((r) => r.fuente_id === "mefd_epa")).toBe(true);
    expect(obs.muestra_pequena.length).toBeGreaterThan(0);
  });
});

describe("EDUCAbase", () => {
  const obs = (id: string) => REGISTRO.find((r) => r.ficha.id === id)!.obs;

  it("titularidad: pública + concertada + privada no concertada = 100 % en cada comunidad y curso", () => {
    const suma = new Map<string, number>();
    for (const f of obs("alumnado_titularidad").filas) suma.set(`${f.territorio}|${f.periodo}`, (suma.get(`${f.territorio}|${f.periodo}`) ?? 0) + f.valor);
    expect(suma.size).toBe(20 * obs("alumnado_titularidad").periodos.length);
    for (const [k, v] of suma) expect(Math.abs(v - 100), k).toBeLessThan(0.001); // cada parte va redondeada a 4 decimales
  });

  it("en el último curso no aparecen diferencias nuevas en los recálculos (si no, la tabla ha cambiado de formato)", () => {
    for (const id of ["alumnos_profesor", "alumnado_extranjero", "alumnos_unidad"]) {
      const o = obs(id), [ant, ult] = o.periodos.slice(-2), difs = o.comprobacion.diferencias ?? [];
      const clave = (d: { territorio: string; titularidad?: string; etapa?: string }) => `${d.territorio}|${d.titularidad}|${d.etapa ?? ""}`;
      const antes = new Set(difs.filter((d) => d.periodo === ant).map(clave));
      expect(o.comprobacion.pares_comparados, id).toBeGreaterThan(400);
      expect(difs.filter((d) => d.periodo === ult && !antes.has(clave(d))), id).toEqual([]);
    }
  });

  it("alumnos por clase: las ocho etapas, con España en el último curso", () => {
    const o = obs("alumnos_unidad"), ult = o.periodos.at(-1);
    const etapas = new Set(o.filas.filter((f) => f.territorio === "00" && f.periodo === ult && f.titularidad === "total").map((f) => f.etapa));
    expect([...etapas].sort()).toEqual(["bachillerato", "eso", "fp_basica", "fp_medio", "fp_superior", "infantil1", "infantil2", "primaria"]);
  });

  // 12 y no 17: en algunas comunidades no hay privada no concertada en ESO (repetición: 14 con dato)
  it("cada variante tiene España y, en su último periodo con dato, al menos 12 comunidades", () => {
    const d = construirDatos();
    for (const i of d.inds) for (const v of i.variantes) {
      const es = i.serie[v.clave].ES, k = es.map((x) => x != null).lastIndexOf(true);
      const n = Object.entries(i.serie[v.clave]).filter(([id, s]) => id.length === 2 && id !== "ES" && s[k] != null).length;
      expect(k, `${i.id} ${v.clave}`).toBeGreaterThanOrEqual(0);
      expect(n, `${i.id} ${v.clave}`).toBeGreaterThanOrEqual(12);
    }
  });
});

describe("PISA 2025", () => {
  const obs = (id: string) => REGISTRO.find((r) => r.ficha.id === id)!.obs;
  const terr = ["00", ...Array.from({ length: 19 }, (_, i) => String(i + 1).padStart(2, "0"))];

  it("las tres competencias, con las 19 comunidades y ciudades y España, cada una con su error típico", () => {
    for (const comp of ["ciencias", "matematicas", "lectura"]) {
      const f = obs("pisa_puntuacion").filas.filter((x) => x.periodo === "2025" && x.competencia === comp && terr.includes(x.territorio));
      expect(f.map((x) => x.territorio).sort(), comp).toEqual(terr);
      expect(f.every((x) => x.error_estandar != null && x.error_estandar > 0), comp).toBe(true);
    }
  });

  it("Cataluña no es comparable y Murcia va con cautela, con el texto del INEE", () => {
    for (const id of ["pisa_puntuacion", "pisa_bajo", "pisa_alto"]) {
      expect(obs(id).no_comparable?.map((n) => n.territorio), id).toEqual(["09"]);
      expect(obs(id).no_comparable?.[0].texto, id).toMatch(/no deben ser utilizados para comparaciones/);
      expect(obs(id).cautela?.map((n) => n.territorio), id).toEqual(["14"]);
    }
    const d = construirDatos().inds.find((i) => i.id === "pisa_puntuacion")!;
    expect(Object.keys(d.noComparable)).toEqual(["CT"]);
  });

  it("los cambios entre ediciones tienen su error, salvo los dos que la tabla trae intercambiados (y lo dicen)", () => {
    const cambios = obs("pisa_puntuacion").cambios ?? [];
    expect(cambios.length).toBeGreaterThan(30);
    for (const c of cambios) expect(c.error_estandar != null || /intercambiadas/.test(c.nota ?? ""), c.territorio).toBe(true);
  });
});

describe("originales y leyes", () => {
  const manifest = leer("datos-originales/manifest.json") as { fichero: string; url: string; sha256: string; fecha_captura: string }[];
  const dir = join(RAIZ, "datos-originales");
  const todos = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? todos(join(d, f)) : [join(d, f)]);

  it("cada fichero de datos-originales está en el manifest con su sha256 y su dirección de origen", () => {
    const apuntados = new Set(manifest.map((m) => m.fichero));
    // es-atlas: el mapa ya proyectado (src/data/mapa-ccaa.json) viene de sanidad-ccaa; su origen está en scripts/proyectar_mapa.mjs
    const locales = todos(dir).map((f) => relative(dir, f).replace(/\\/g, "/")).filter((f) => f !== "manifest.json" && !f.startsWith("es-atlas/"));
    for (const f of locales) expect(apuntados.has(f), `${f} no está en el manifest`).toBe(true);
    for (const m of manifest) {
      expect(m.url).toMatch(/^https:\/\//);
      expect(m.sha256).toMatch(/^[0-9a-f]{64}$/);
      const ruta = join(dir, m.fichero);
      if (existsSync(ruta)) expect(createHash("sha256").update(readFileSync(ruta)).digest("hex"), m.fichero).toBe(m.sha256);
    }
  });

  it("cada ley o hecho enlaza a su norma del BOE y su fecha es la del título", () => {
    for (const h of hitos) {
      expect(h.url).toBe(`https://www.boe.es/buscar/act.php?id=${h.id}`);
      expect(h.titulo).toContain(String(h.anio));
    }
  });
});
