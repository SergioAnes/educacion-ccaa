// @ts-nocheck -- Interfaz imperativa (DOM + SVG), adaptada de sanidad-ccaa (src/lib/app/ui.ts).
// Recibe los datos ya preparados en compilación (datos-app.ts) y pinta las tres vistas por #hash.
import type { DatosApp } from "./datos-app";
import { TRAMPAS } from "./textos";

let iniciada = false;

export function iniciar(DATA: DatosApp): void {
  if (iniciada) return; // React (modo estricto) puede llamar dos veces al efecto
  iniciada = true;
  // ---------- utilidades ----------
  const $ = (s) => document.querySelector(s);
  const CC = DATA.ccaa;
  const IDS = CC.map((c) => c.id);
  const CIUDADES = Object.fromEntries(DATA.ciudades.map((c) => [c.id, c.nombre]));
  const IDS_CIU = DATA.ciudades.map((c) => c.id);
  const NOMBRE = Object.fromEntries([...CC, ...DATA.ciudades].map((c) => [c.id, c.nombre]));
  const ABR = Object.fromEntries([...CC, ...DATA.ciudades].map((c) => [c.id, c.abr]));
  const IND = Object.fromEntries(DATA.inds.map((i) => [i.id, i]));
  const TEMAS = [{ id: "resumen", nombre: "Resumen" }, ...DATA.temas];
  const NOMBRE_TEMA = Object.fromEntries(TEMAS.map((t) => [t.id, t.nombre]));

  const nf = (d) => new Intl.NumberFormat("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: "always" });
  function fmt(v, u) {
    if (v == null || !isFinite(v)) return "—";
    if (u === "pct") return nf(1).format(v) + " %";
    return nf(1).format(v);
  }
  // Diferencias: en puntos para porcentajes; en la misma unidad para lo demás (alumnos por profesor)
  function fmtDif(ind, d) {
    if (d == null || !isFinite(d)) return "—";
    const signo = Math.abs(d) < 0.05 ? "≈ " : d > 0 ? "+" : "−";
    return signo + nf(1).format(Math.abs(d)) + (ind.unidad === "pct" ? " puntos" : "");
  }
  const fmtCorto = (v, u) => fmt(v, u).replace(" %", "%");
  // La cifra con lo que mide: «12,8 % de los jóvenes de 18 a 24 años», «11,1 alumnos por profesor»
  const conQue = (ind, v) => ind.unidad === "ratio" ? `${fmt(v, ind.unidad)} alumnos ${ind.que}` : `${fmt(v, ind.unidad)} ${ind.que}`;
  const unidadTxt = (ind) => ind.unidad === "pct" ? "En %" : "En alumnos por profesor";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const lista = (xs) => xs.length > 1 ? `${xs.slice(0, -1).join(", ")} y ${xs.at(-1)}` : xs[0] || "";

  // ---------- periodos (año o curso) y variantes (sexo o titularidad) ----------
  const periodos = (ind) => ind.periodos;
  const primero = (ind) => ind.periodos[0];
  const ultimo = (ind) => ind.periodos.at(-1);
  const indice = (ind, a) => ind.periodos.indexOf(a);
  const etq = (ind, a) => ind.etiquetas[indice(ind, a)] ?? String(a);
  const esAvance = (ind, a) => ind.avance.includes(indice(ind, a));
  const etqEstado = (ind, a) => etq(ind, a) + (esAvance(ind, a) ? " (avance)" : "");
  const esCurso = (ind) => ind.etiquetas[0].includes("-");
  const varDe = (ind) => ind.variantes.some((v) => v.clave === S.var) ? S.var : ind.variantes[0].clave;
  const varEtq = (ind, k = varDe(ind)) => ind.variantes.find((v) => v.clave === k)?.etiqueta ?? "";
  const esTotal = (ind, k) => /^(total|todos los centros)$/i.test(varEtq(ind, k));
  // «(mujeres)», «(concertada)»; nada si es el total
  const varFrase = (ind, k = varDe(ind)) => esTotal(ind, k) || !varEtq(ind, k) ? "" : ` (${varEtq(ind, k).charAt(0).toLowerCase() + varEtq(ind, k).slice(1)})`;
  const dimVar = (ind) => ind.variantes.some((v) => !v.clave.startsWith("total|")) ? "sexo" : "titularidad";
  const serieDe = (ind, k = varDe(ind)) => ind.serie[k] || {};
  const dato = (ind, id, a, k = varDe(ind)) => serieDe(ind, k)[id]?.[indice(ind, a)] ?? null;
  const espana = (ind, a, k = varDe(ind)) => dato(ind, "ES", a, k);
  const ue = (ind, a, k = varDe(ind)) => ind.ue?.[k]?.[indice(ind, a)] ?? null;
  function valores(ind, a, k = varDe(ind)) { const o = {}; for (const id of IDS) o[id] = dato(ind, id, a, k); return o; }
  function ordenados(o) { return IDS.filter((id) => o[id] != null).sort((a, b) => o[b] - o[a]); }
  // Cautela: muestra pequeña (Ministerio) o baja fiabilidad (Eurostat), solo en la encuesta
  const pequena = (ind, id) => ind.muestraPequena.includes(id);
  const bajaFiab = (ind, id, a, k = varDe(ind)) => (ind.baja[k]?.[id] || []).includes(indice(ind, a));
  const conCautela = (ind, id, a, k = varDe(ind)) => pequena(ind, id) || bajaFiab(ind, id, a, k);
  const marca = (ind, id, a, k = varDe(ind)) => conCautela(ind, id, a, k) ? "†" : "";
  function textoCautela(ind, id, a, k = varDe(ind)) {
    const t = [];
    if (pequena(ind, id)) t.push("Muestra pequeña: el Ministerio pide tomar sus cifras con precaución.");
    if (bajaFiab(ind, id, a, k)) t.push("Eurostat marca este dato como de baja fiabilidad.");
    return t.join(" ");
  }
  const frenteEspana = (ind, v, a, k = varDe(ind)) => {
    const e = espana(ind, a, k);
    if (v == null || e == null) return "";
    const d = v - e;
    if (Math.abs(d) < 0.05) return "igual que España";
    return ind.unidad === "pct" ? `${nf(1).format(Math.abs(d))} puntos ${d > 0 ? "por encima" : "por debajo"} de España` : `${nf(1).format(Math.abs(d))} ${d > 0 ? "más" : "menos"} que España`;
  };
  // Notas de la fuente que citan a una comunidad (y, si se da, a un periodo)
  const notasDe = (ind, id, etiqueta) => ind.notas.filter((n) => n.territorios.includes(id) && (!etiqueta || !n.periodos.length || n.periodos.includes(etiqueta)));

  // ---------- estado ----------
  const S = {
    vista: "datos", tema: "resumen",
    ind: DATA.inds.find((i) => i.resumen)?.id || DATA.inds[0].id, var: "", anio: null, vistaE: "ranking",
    com: "AN", sel: [{ id: "AN", slot: 0 }], vs: "", leyes: false,
    abiertos: {},
  };
  const SLOTS = ["--s1", "--s2", "--s3"];
  const colorSel = (id) => { const s = S.sel.find((x) => x.id === id); return s ? css(SLOTS[s.slot]) : null; };
  function alternarSel(id) {
    const i = S.sel.findIndex((x) => x.id === id);
    if (i >= 0) { S.sel.splice(i, 1); return; }
    if (S.sel.length >= 3) S.sel.shift();
    const libres = [0, 1, 2].filter((s) => !S.sel.some((x) => x.slot === s));
    S.sel.push({ id, slot: libres[0] });
  }
  const indsTema = (t = S.tema) => DATA.inds.filter((i) => t === "resumen" ? i.resumen : i.grupo === t);

  // Explicaciones plegadas: los datos primero; el texto, para quien lo quiera. Recuerdan si estaban abiertas.
  function plegable(clave, resumen, cuerpo) {
    return `<details class="pliegue" data-p="${clave}" ${S.abiertos[clave] ? "open" : ""}><summary>${resumen}</summary><div class="pliegue-c">${cuerpo}</div></details>`;
  }
  document.addEventListener("toggle", (e) => { const d = e.target; if (d.matches && d.matches("details[data-p]")) S.abiertos[d.dataset.p] = d.open; }, true);

  // ---------- origen de cada cifra: fiabilidad, periodo, estado y fuente ----------
  const FIAB = { A: "Estadística oficial periódica", B: "Oficial, pero puntual o con limitaciones", C: "Estudio o estimación" };
  const chipFiab = (f, tag = "a") => `<${tag} class="fiab fiab-${f}" ${tag === "a" ? 'href="#metodo-fiabilidad"' : ""} title="Fiabilidad ${f}: ${FIAB[f]}">${f}</${tag}>`;
  function origen(ind, a) {
    const f = ind.fuentes[0];
    return `${chipFiab(ind.fiabilidad)}<span>${FIAB[ind.fiabilidad]} · ${etq(ind, a)} · ${esAvance(ind, a) ? "avance" : ind.estado} · <a href="${f.url}">${esc(f.corto || f.nombre)}</a></span>`;
  }

  // ---------- paleta del mapa: cinco tramos de 3 o 4 comunidades ----------
  const Q_AZUL = ["#cde2fb", "#86b6ef", "#5598e7", "#1c5cab", "#0d366b"];
  function oscuro() {
    const t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function textoSobre(hex) {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    const L = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    return (1.05 / (L + 0.05)) >= ((L + 0.05) / (0.0144 + 0.05)) ? "#ffffff" : "#142033";
  }
  function escala(vals, ind) {
    const o = ordenados(vals);
    if (!o.length) return { color: () => ({ bg: css("--grey-line"), fg: css("--fg") }), leyenda: "<span>Sin valores para las comunidades.</span>" };
    const cols = oscuro() ? [...Q_AZUL].reverse() : Q_AZUL;
    const asc = o.slice().reverse();
    const k = (id) => Math.min(4, Math.floor(asc.indexOf(id) * 5 / asc.length));
    const caja = (bg) => ({ bg, fg: textoSobre(bg) });
    const et = cols.map((_, c) => {
      const mi = asc.filter((id) => k(id) === c).map((id) => vals[id]);
      return `<b class="num">${nf(1).format(Math.min(...mi))}–${nf(1).format(Math.max(...mi))}</b>${c === 0 ? "las que menos" : c === 4 ? "las que más" : ""}`;
    });
    return {
      color: (id) => caja(cols[k(id)]),
      leyenda: `<div class="clases">${cols.map((c, i) => `<span class="clase"><i style="background:${c}"></i>${et[i]}</span>`).join("")}</div><span class="pie">Cada tono agrupa 3 o 4 comunidades, de menos a más. ${unidadTxt(ind)}.${ind.encuesta ? " † = cifra que hay que tomar con precaución (muestra pequeña)." : ""}</span>`,
    };
  }

  // ---------- tooltip ----------
  const tip = $("#tip");
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    const r = tip.getBoundingClientRect();
    let left = x + 14, top = y + 14;
    if (left + r.width > innerWidth - 8) left = x - r.width - 14;
    left = Math.max(8, Math.min(left, innerWidth - r.width - 8));
    if (top + r.height > innerHeight - 8) top = y - r.height - 14;
    tip.style.left = left + "px"; tip.style.top = top + "px";
  }
  const hideTip = () => { tip.hidden = true; };

  // ---------- mapa (siluetas del IGN ya proyectadas; Canarias en recuadro) ----------
  const GEO = DATA.geo;
  const FUERA = ["CE", "ML", "GI"];
  function tileMap(cont, vals, ind, { onClick, selIds = [], neutro = false, anio = S.anio } = {}) {
    const esca = neutro ? null : escala(vals, ind);
    const surf = css("--surface"), fg = css("--fg"), muted = css("--muted"), acc = css("--accent"), linea = css("--grey-line");
    const m = GEO.marco;
    let sv = `<svg class="geo" viewBox="0 0 ${GEO.w} ${GEO.h}" role="group" aria-label="Mapa de las comunidades autónomas">
      <rect x="${m.x}" y="${m.y}" width="${m.w}" height="${m.h}" rx="10" fill="none" stroke="${linea}" stroke-dasharray="4 4"/>`;
    const falta = (id) => !neutro && vals[id] == null;
    const color = (id) => neutro ? (selIds.includes(id) ? { bg: acc, fg: "#ffffff" } : { bg: linea, fg }) : falta(id) ? { bg: linea, fg } : esca.color(id);
    GEO.regiones.forEach((r) => {
      if (FUERA.includes(r.id)) { sv += `<path ${CIUDADES[r.id] && neutro ? `class="reg" data-id="${r.id}" tabindex="0" role="button" aria-label="${esc(NOMBRE[r.id])}"` : ""} d="${r.d}" fill="${selIds.includes(r.id) ? acc : muted}" stroke="none"/>`; return; }
      const et = neutro ? NOMBRE[r.id] : `${NOMBRE[r.id]}: ${falta(r.id) ? "sin dato" : fmt(vals[r.id], ind.unidad)}`;
      sv += `<path class="reg" data-id="${r.id}" d="${r.d}" fill="${color(r.id).bg}" stroke="${surf}" stroke-width="1" stroke-linejoin="round" tabindex="0" role="button" aria-label="${esc(et)}"/>`;
    });
    GEO.regiones.filter((r) => selIds.includes(r.id) && !FUERA.includes(r.id)).forEach((r) => { sv += `<path d="${r.d}" fill="none" stroke="${fg}" stroke-width="2.6" stroke-linejoin="round" pointer-events="none"/>`; });
    if (!neutro) GEO.regiones.forEach((r) => {
      if (FUERA.includes(r.id)) return;
      const k = color(r.id), grande = r.area > 2500, peq = r.area < 1300;
      const v = falta(r.id) ? "s/d" : fmtCorto(vals[r.id], ind.unidad);
      const halo = `stroke="${k.bg}" stroke-width="3" stroke-linejoin="round" paint-order="stroke"`;
      sv += `<text x="${r.lx}" y="${r.ly + (grande ? -2 : 4)}" text-anchor="middle" font-size="${peq ? 10 : 12}" font-weight="700" fill="${k.fg}" ${halo}>${ABR[r.id]}${marca(ind, r.id, anio)}</text>`;
      if (grande) sv += `<text x="${r.lx}" y="${r.ly + 12}" text-anchor="middle" font-size="11" fill="${k.fg}" class="num" ${halo}>${v}</text>`;
    });
    // Ceuta y Melilla: aparte (círculo y cifra), sin color de la escala
    if (!neutro) GEO.regiones.filter((r) => CIUDADES[r.id]).forEach((r) => {
      const v = dato(ind, r.id, anio); if (v == null) return;
      sv += `<g class="reg ciu" data-id="${r.id}" tabindex="0" role="img" aria-label="${CIUDADES[r.id]}: ${esc(fmt(v, ind.unidad))} (aparte)"><circle cx="${r.lx}" cy="${r.ly}" r="8" fill="${surf}" stroke="${fg}" stroke-width="1.2" stroke-dasharray="2 2"/>
        <text x="${r.lx + 12}" y="${r.ly + 4}" font-size="10.5" fill="${fg}">${CIUDADES[r.id]} ${fmtCorto(v, ind.unidad)}*</text></g>`;
    });
    sv += `<text x="${m.x + 8}" y="${m.y + m.h - 8}" font-size="10" fill="${muted}">Canarias</text></svg><p class="geo-fuente">Mapa: Instituto Geográfico Nacional (es-atlas), CC BY 4.0.${neutro ? "" : " * Ceuta y Melilla, aparte: no cambian los colores de las 17."}</p>`;
    cont.innerHTML = sv;
    cont.querySelectorAll(".reg").forEach((t) => {
      const id = t.dataset.id;
      const ciu = !!CIUDADES[id];
      t.onclick = () => onClick && onClick(id);
      t.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick && onClick(id); } };
      t.onmousemove = (e) => {
        if (neutro) { showTip(`<b>${esc(NOMBRE[id])}</b>`, e.clientX, e.clientY); return; }
        const v = ciu ? dato(ind, id, anio) : vals[id];
        if (v == null) { showTip(`<b>${esc(NOMBRE[id])}</b><br>Sin dato`, e.clientX, e.clientY); return; }
        const nn = notasDe(ind, id, etq(ind, anio)).length;
        showTip(`<b>${esc(NOMBRE[id])}</b>${ciu ? " (ciudad autónoma, aparte)" : ""}<br>${fmt(v, ind.unidad)} en ${etq(ind, anio)}<br>${frenteEspana(ind, v, anio)}${conCautela(ind, id, anio) ? `<br>† ${esc(textoCautela(ind, id, anio))}` : ""}${nn ? `<br>La fuente tiene ${nn === 1 ? "una nota" : `${nn} notas`} sobre esta comunidad` : ""}`, e.clientX, e.clientY);
      };
      t.onmouseleave = hideTip;
      t.onfocus = () => { const r = t.getBoundingClientRect(); t.onmousemove({ clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }); };
      t.onblur = hideTip;
    });
    return esca;
  }

  // ---------- línea de tiempo (un tirador; se crea una vez y luego solo se actualiza) ----------
  let timer = null;
  function barraAnios(cont, ind, anio, onChange) {
    const ps = periodos(ind);
    const clave = `anio-${ind.id}`;
    if (cont.dataset.tipo !== clave) {
      cont.dataset.tipo = clave;
      const pct = (i) => (i / (ps.length - 1)) * 100;
      const marcas = ps.map((a, i) => ({ a, i })).filter(({ i }) => i === 0 || i === ps.length - 1 || (i % 4 === 0 && ps.length - 1 - i >= 3));
      cont.innerHTML = `<button type="button" class="play"></button><span class="anio"></span><span class="prov">avance</span>
        <div class="linea"><input type="range" min="0" max="${ps.length - 1}" step="1" aria-label="${esCurso(ind) ? "Curso" : "Año"}"><div class="marcas" aria-hidden="true">${marcas.map(({ a, i }) => `<span style="left:calc(10px + (100% - 20px) * ${pct(i) / 100})">${esCurso(ind) ? etq(ind, a).replace(/^20/, "") : a}</span>`).join("")}</div></div>
        <span class="ayuda-rango">Mueve el punto para elegir ${esCurso(ind) ? "el curso" : "el año"}. Pulsa ▶ para reproducir la serie.</span>`;
    }
    const inp = cont.querySelector("input"), play = cont.querySelector(".play");
    const i = indice(ind, anio);
    if (+inp.value !== i) inp.value = i;
    inp.setAttribute("aria-valuetext", etq(ind, anio));
    cont.querySelector(".anio").textContent = etq(ind, anio);
    cont.querySelector(".prov").hidden = !esAvance(ind, anio);
    play.textContent = timer ? "❚❚" : "▶";
    play.setAttribute("aria-label", timer ? "Pausar" : "Reproducir la serie");
    inp.oninput = () => { pararPlay(); onChange(ps[+inp.value]); };
    play.onclick = () => {
      if (timer) { pararPlay(); render(); return; }
      let k = i >= ps.length - 1 ? 0 : i;
      onChange(ps[k]);
      timer = setInterval(() => { k++; if (k > ps.length - 1) { pararPlay(); render(); return; } onChange(ps[k]); }, 420);
      render();
    };
  }
  function pararPlay() { if (timer) { clearInterval(timer); timer = null; } }

  // ---------- titulares (solo cifras, sin valorar) ----------
  function titulares(ind, a) {
    const vals = valores(ind, a), o = ordenados(vals), u = ind.unidad;
    const out = [];
    if (!o.length) return out;
    const nom = (id) => `<strong>${esc(NOMBRE[id])}</strong>${marca(ind, id, a)}`;
    const igual = (ref) => o.filter((id) => fmt(vals[id], u) === fmt(vals[ref], u));
    const [ta, tb] = [igual(o[0]), igual(o.at(-1))];
    out.push({ k: "Más alto y más bajo", t: `${lista(ta.map(nom))} ${ta.length > 1 ? "tienen" : "tiene"} la cifra más alta (${fmt(vals[o[0]], u)}) y ${lista(tb.map(nom))}, la más baja (${fmt(vals[o.at(-1)], u)}).` +
      (ta.concat(tb).some((id) => conCautela(ind, id, a)) ? ` <span class="cautela">† Con precaución: muestra pequeña.</span>` : "") });
    const e = espana(ind, a), eu = ue(ind, a);
    if (e != null) {
      const enc = o.filter((id) => vals[id] > e).length;
      out.push({ k: `España en ${etq(ind, a)}${varFrase(ind)}`, t: `<strong>${conQue(ind, e)}</strong>. ${enc} de las 17 comunidades están por encima.` +
        (eu != null ? ` En la UE-27, ${fmt(eu, u)} (Eurostat).` : "") +
        (ind.objetivo ? ` Por debajo del ${nf(0).format(ind.objetivo.valor)} % que la UE se ha fijado como objetivo para 2030: ${o.filter((id) => vals[id] < ind.objetivo.valor).length} de las 17.` : "") });
    }
    if (ind.variantes.length > 1) {
      const partes = ind.variantes.filter((v) => espana(ind, a, v.clave) != null && !(ind.variantes.length > 2 && esTotal(ind, v.clave)));
      out.push({ k: `Por ${dimVar(ind)}, en España`, t: partes.map((v) => `${esc(v.etiqueta)}: <strong>${fmt(espana(ind, a, v.clave), u)}</strong>`).join(". ") + "." });
    }
    const a0 = primero(ind), e0 = espana(ind, a0);
    if (a > a0 && e0 != null && e != null) {
      const rup = ind.rupturas.filter((r) => r.anio > a0 && r.anio <= a && (r.territorio === "ES" || r.territorio === "todas")).map((r) => r.anio);
      out.push({ k: `España desde ${etq(ind, a0)}`, t: `De ${fmt(e0, u)} a ${fmt(e, u)} (${fmtDif(ind, e - e0)}).` +
        (rup.length ? ` Entre medias hay ${rup.length === 1 ? "una ruptura" : "rupturas"} de serie (${lista([...new Set(rup)].map(String))}): la comparación es aproximada.` : "") });
    }
    return out;
  }

  // ---------- DATOS ----------
  function minigrafico(i) {
    const serie = i.periodos.map((p) => dato(i, "ES", p, i.variantes[0].clave));
    const fin = serie.filter((x) => x != null);
    const lo = Math.min(...fin), hi = Math.max(...fin);
    const sx = (k) => 2 + (k / Math.max(1, serie.length - 1)) * 116, sy = (x) => 3 + (1 - (x - lo) / (hi - lo || 1)) * 22;
    const d = serie.map((x, k) => x == null ? "" : `${k && serie[k - 1] != null ? "L" : "M"}${sx(k).toFixed(1)},${sy(x).toFixed(1)}`).join("");
    return `<svg viewBox="0 0 122 30" preserveAspectRatio="none" aria-hidden="true"><path d="${d}" fill="none" stroke="${css("--accent")}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
  }
  function selector(cont) {
    const tarjetas = indsTema().map((i) => {
      const a = ultimo(i), k0 = i.variantes[0].clave, v = dato(i, "ES", a, k0), v0 = dato(i, "ES", primero(i), k0);
      return `<button type="button" class="kpi" data-id="${i.id}" aria-pressed="${i.id === S.ind}">
        <span class="kpi-n">${esc(i.corto)} ${chipFiab(i.fiabilidad, "span")}</span><span class="kpi-v">${fmt(v, i.unidad)}</span>
        <span class="kpi-mini">${minigrafico(i)}</span><span class="kpi-s">${S.tema === "resumen" ? `${esc(NOMBRE_TEMA[i.grupo])} · ` : ""}España, ${etqEstado(i, a)}<br><span class="kpi-c">${fmtDif(i, v - v0)} desde ${etq(i, primero(i))}</span></span></button>`;
    }).join("");
    const actual = IND[S.ind];
    cont.innerHTML = `<div class="seg temas" role="group" aria-label="Tema">${TEMAS.map((t) => `<button type="button" data-g="${t.id}" aria-pressed="${t.id === S.tema}">${esc(t.nombre)}</button>`).join("")}</div>
      <div class="kpis">${tarjetas}</div>` +
      (actual.variantes.length > 1 ? `<div class="real"><div class="seg sm" role="group" aria-label="${dimVar(actual) === "sexo" ? "Sexo" : "Titularidad del centro"}">${actual.variantes.map((v) => `<button type="button" data-v2="${v.clave}" aria-pressed="${varDe(actual) === v.clave}">${esc(v.etiqueta)}</button>`).join("")}</div><span>${actual.reparto ? "Qué parte del alumnado se ve en el mapa y en los gráficos. La vista «Reparto» enseña las tres juntas." : "Mapa, gráficos y tabla, para lo que elijas aquí."}</span></div>` : "");
    cont.querySelectorAll(".seg.temas button").forEach((b) => b.onclick = () => {
      if (b.dataset.g === S.tema) return;
      S.tema = b.dataset.g;
      if (!indsTema().some((i) => i.id === S.ind)) S.ind = indsTema()[0].id;
      render();
    });
    cont.querySelectorAll(".kpi").forEach((b) => b.onclick = () => { S.ind = b.dataset.id; render(); });
    cont.querySelectorAll("button[data-v2]").forEach((b) => b.onclick = () => sinMover(() => { S.var = b.dataset.v2; render(); }));
  }

  function renderDatos() {
    const ind = IND[S.ind];
    if (!periodos(ind).includes(S.anio)) S.anio = ultimo(ind);
    const a = S.anio;
    selector($("#sel-datos"));
    $("#p-intro").textContent = `Datos oficiales del Ministerio de Educación, el INE y Eurostat. Cada cifra lleva su año o curso, su fuente y su fiabilidad. ${DATA.inds.length} indicadores en ${DATA.temas.length} temas; elige uno en las tarjetas.`;
    const vals = valores(ind, a), o = ordenados(vals);
    $("#p-titulo").textContent = `${ind.nombre}${varFrase(ind)} en ${etq(ind, a)}: la cifra más alta, ${NOMBRE[o[0]]}; la más baja, ${NOMBRE[o.at(-1)]}`;
    $("#p-sub").textContent = `${ind.unidad === "pct" ? `Porcentaje ${ind.que}.` : `Alumnos ${ind.que}.`}${ind.encuesta ? " Es una encuesta: las diferencias pequeñas entre comunidades pueden deberse al azar de la muestra." : ""}${esAvance(ind, a) ? " Dato de avance: puede cambiar." : ""} Pulsa una comunidad para elegirla como la tuya.`;
    $("#p-origen").innerHTML = origen(ind, a);
    const esca = tileMap($("#p-mapa"), vals, ind, { selIds: [S.com], onClick: (id) => { S.com = id; render(); } });
    $("#p-leyenda").innerHTML = esca.leyenda;
    barraAnios($("#p-anios"), ind, a, (x) => { S.anio = x; render(); });
    botonPNG($("#p-desc"), "Descargar mapa (PNG)", () => descargarPNG($("#p-mapa svg"), `mapa_${ind.id}_${etq(ind, a)}`, $("#p-titulo").textContent, $("#p-leyenda"), ind));

    // Titulares, con «Tu comunidad» primero (con su propio desplegable)
    const v = dato(ind, S.com, a);
    const ficha = `<a href="#comunidad-${S.com.toLowerCase()}">Ver su ficha</a>`;
    const nn = notasDe(ind, S.com, etq(ind, a));
    const tuya = v == null ? `Sin dato en ${etq(ind, a)}. ${ficha}` : `<strong>${fmt(v, ind.unidad)}</strong>${marca(ind, S.com, a)} en ${etq(ind, a)}: ${frenteEspana(ind, v, a)}.${conCautela(ind, S.com, a) ? ` <span class="cautela">† ${esc(textoCautela(ind, S.com, a))}</span>` : ""}${nn.length ? ` <span class="cautela">Nota de la fuente: ${esc(nn[0].texto)}</span>` : ""} ${ficha}`;
    const opciones = [...IDS, ...IDS_CIU].slice().sort((x, y) => NOMBRE[x].localeCompare(NOMBRE[y], "es")).map((k) => `<option value="${k}" ${k === S.com ? "selected" : ""}>${esc(NOMBRE[k])}${CIUDADES[k] ? " (aparte)" : ""}</option>`).join("");
    $("#p-insights").innerHTML = `<div class="insight tuya"><label class="k" for="p-com">Tu comunidad</label><select id="p-com">${opciones}</select><p>${tuya}</p></div>` +
      titulares(ind, a).map((x) => `<div class="insight"><div class="k">${esc(x.k)}</div><p>${x.t}</p></div>`).join("");
    $("#p-com").onchange = (e) => { S.com = e.target.value; render(); };

    renderDetalle(ind, a);
    $("#d-mide").innerHTML = `<h2>¿Qué mide esto?</h2>${queMide(ind, "datos")}`;
    guardarEnlace();
  }

  // Ficha del indicador: qué mide, de dónde sale y qué no mide (sale de src/data/indicadores/<id>.json)
  function queMide(ind, clave) {
    const f = ind.fuentes.map((x) => `<li><a href="${x.url}">${esc(x.nombre)}</a></li>`).join("");
    const nomT = (t) => t === "todas" ? "todas las series" : t === "UE27" ? "UE-27" : NOMBRE[t] || t;
    const rupt = ind.rupturas.map((r) => `<li><b>${r.anio}</b> (${nomT(r.territorio)}): ${esc(r.texto)}</li>`).join("");
    const notas = ind.notas.map((n) => `<li>${n.territorios.length || n.periodos.length ? `<b>${esc(lista(n.territorios.map(nomT)))}${n.territorios.length && n.periodos.length ? ", " : ""}${esc(lista(n.periodos))}.</b> ` : ""}${esc(n.texto)}</li>`).join("");
    const difs = ind.diferencias;
    return `<dl class="mide">
        <dt>Qué es</dt><dd>${esc(ind.definicion)}</dd>
        <dt>Qué no mide</dt><dd>${esc(ind.no_mide)}</dd>
        <dt>Fiabilidad</dt><dd>${chipFiab(ind.fiabilidad)} ${esc(ind.fiabilidad_txt)}</dd>
        <dt>España</dt><dd>${esc(ind.espana)}</dd>
      </dl>` +
      plegable(`${clave}-calculo`, "Cómo se calcula", `<p><b>Numerador:</b> ${esc(ind.numerador)}</p><p><b>Denominador:</b> ${esc(ind.denominador)}</p>`) +
      (ind.avisos.length || ind.muestraPequena.length ? plegable(`${clave}-avisos`, `Avisos (${ind.avisos.length + (ind.muestraPequena.length ? 1 : 0)})`,
        `<ul>${ind.avisos.map((x) => `<li>${esc(x)}</li>`).join("")}${ind.muestraPequena.length ? `<li>Muestra pequeña según el Ministerio: ${esc(lista(ind.muestraPequena.map((k) => NOMBRE[k])))}. Se marcan con †, igual que los datos que Eurostat considera de baja fiabilidad.</li>` : ""}</ul>`) : "") +
      (ind.notas.length ? plegable(`${clave}-notas`, `Notas de la fuente (${ind.notas.length})`, `<p>Tal cual las publica la fuente, con las comunidades y periodos que las citan.</p><ul>${notas}</ul>`) : "") +
      (ind.rupturas.length ? plegable(`${clave}-rupturas`, `Rupturas de serie (${ind.rupturas.length})`, `<p>Tal como las marca cada fuente, sin interpretarlas. Comparar años a los dos lados de una ruptura es solo aproximado.</p><ul>${rupt}</ul>` +
        (ind.definicionDifiere.length ? `<p>Eurostat marca además los datos de España de ${lista(ind.definicionDifiere.map(String))} con «la definición difiere (ver metadatos)».</p>` : "")) : "") +
      plegable(`${clave}-fuente`, "Fuentes y comprobaciones", `<ul>${f}</ul><p>Comprobado al generar los datos: ${esc(ind.comprobacion)} Datos descargados el ${ind.fechaCaptura.split("-").reverse().join("/")}.</p>` +
        (difs.length ? `<p>Casos en que el dato publicado no coincide con el recálculo (se muestra el publicado; la fuente no lo explica):</p><ul class="difs">${difs.map((d) => `<li>${esc(NOMBRE[d.territorio] || "España")}, ${esc(d.periodo)}${d.variante !== "total|total" ? ` (${esc(varEtq(ind, d.variante).toLowerCase())})` : ""}: publicado ${fmt(d.publicado, ind.unidad)}, recalculado ${fmt(d.calculado, ind.unidad)}</li>`).join("")}</ul>` : "") +
        (ind.objetivo ? `<p>${esc(ind.objetivo.texto)}: <a href="${ind.objetivo.url}">${esc(ind.objetivo.fuente)}</a>. ${esc(ind.objetivo.nota)}</p>` : ""));
  }

  function renderDetalle(ind, a) {
    const vistas = [["ranking", "De más a menos"], ...(ind.reparto ? [["reparto", "Reparto"]] : []), ["evolucion", "Evolución"], ["tabla", "Tabla"]];
    if (!vistas.some(([v]) => v === S.vistaE)) S.vistaE = "ranking";
    $("#e-vistas").innerHTML = vistas.map(([v, t]) => `<button type="button" data-v="${v}" aria-pressed="${v === S.vistaE}">${t}</button>`).join("");
    $("#e-vistas").querySelectorAll("button").forEach((b) => b.onclick = () => sinMover(() => { S.vistaE = b.dataset.v; render(); }));
    // Comunidades destacadas (ranking y evolución): pastillas con su color
    $("#e-selec").innerHTML = S.vistaE === "tabla" || S.vistaE === "reparto" ? "" : `<span>Destacadas:</span>${S.sel.map((s) => `<span class="pill"><i style="background:${css(SLOTS[s.slot])}"></i>${esc(NOMBRE[s.id])}<button type="button" data-q="${s.id}" aria-label="Quitar ${esc(NOMBRE[s.id])}">×</button></span>`).join("")}` +
      (S.sel.length < 3 ? `<select id="e-add" aria-label="Destacar otra comunidad"><option value="">+ Añadir</option>${[...IDS, ...IDS_CIU].filter((k) => !S.sel.some((s) => s.id === k)).sort((x, y) => NOMBRE[x].localeCompare(NOMBRE[y], "es")).map((k) => `<option value="${k}">${esc(NOMBRE[k])}</option>`).join("")}</select>` : "");
    $("#e-selec").querySelectorAll("button[data-q]").forEach((b) => b.onclick = () => { alternarSel(b.dataset.q); render(); });
    if ($("#e-add")) $("#e-add").onchange = (e) => { if (e.target.value) { alternarSel(e.target.value); render(); } };
    $("#e-opciones").innerHTML = "";
    $("#e-nota").innerHTML = "";
    const tit = `${ind.nombre}${varFrase(ind)}`;
    if (S.vistaE === "ranking") {
      $("#e-titulo").textContent = `${tit}, ${etq(ind, a)}: de más a menos`;
      $("#e-sub").textContent = `La línea discontinua es España${ind.ue ? "; la punteada, la UE-27" : ""}.${ind.encuesta ? " No damos puestos del 1 al 17: es una encuesta y muchas diferencias son pequeñas." : ""} Pulsa una comunidad para destacarla.`;
      ranking($("#e-chart"), ind, a);
      botonPNG($("#e-desc"), "Descargar gráfico (PNG)", () => descargarPNG($("#e-chart svg"), `ranking_${ind.id}_${etq(ind, a)}`, $("#e-titulo").textContent, null, ind));
    } else if (S.vistaE === "reparto") {
      $("#e-titulo").textContent = `${ind.nombre}, ${etq(ind, a)}: reparto en cada comunidad`;
      $("#e-sub").textContent = `Cada barra suma 100 %. Ordenadas por el peso de la ${varEtq(ind).toLowerCase()} (cámbialo arriba).`;
      reparto($("#e-chart"), ind, a);
      botonPNG($("#e-desc"), "Descargar gráfico (PNG)", () => descargarPNG($("#e-chart svg"), `reparto_${ind.id}_${etq(ind, a)}`, $("#e-titulo").textContent, null, ind));
    } else if (S.vistaE === "evolucion") {
      $("#e-titulo").textContent = `${tit}, ${etq(ind, primero(ind))} a ${etq(ind, ultimo(ind))}`;
      $("#e-sub").textContent = `En gris, las 17 comunidades; en color, las destacadas. La línea discontinua es España${ind.ue ? " y la punteada, la UE-27" : ""}.${ind.objetivo ? ` La franja marca el ${ind.objetivo.texto.charAt(0).toLowerCase() + ind.objetivo.texto.slice(1)}.` : ""}`;
      $("#e-opciones").innerHTML = `<label class="interruptor"><input type="checkbox" id="e-leyes" ${S.leyes ? "checked" : ""}> Leyes y hechos</label><span class="ayuda">Fecha de cada norma en el BOE, no la de su aplicación en las aulas. Que coincidan en el tiempo no quiere decir que una cosa cause la otra.</span>`;
      $("#e-leyes").onchange = (e) => sinMover(() => { S.leyes = e.target.checked; render(); });
      lineas($("#e-chart"), ind);
      botonPNG($("#e-desc"), "Descargar gráfico (PNG)", () => descargarPNG($("#e-chart svg"), `evolucion_${ind.id}`, $("#e-titulo").textContent, null, ind));
    } else {
      $("#e-titulo").textContent = `${tit}: tabla de ${etq(ind, a)}`;
      $("#e-sub").textContent = `Diferencia con España y cambio desde ${etq(ind, primero(ind))}${ind.unidad === "pct" ? ", en puntos porcentuales" : ""}.`;
      tabla($("#e-chart"), ind, a);
      $("#e-desc").innerHTML = "";
    }
  }

  // Barras de más a menos, con España (discontinua), UE-27 (punteada) y el objetivo; Ceuta y Melilla aparte.
  function ranking(cont, ind, a) {
    const vals = valores(ind, a), o = ordenados(vals);
    const ciu = IDS_CIU.filter((k) => dato(ind, k, a) != null);
    const W = Math.max(320, cont.clientWidth || 800), fila = 26, top = 8, extra = ciu.length ? 30 + ciu.length * fila : 0;
    const H = top + o.length * fila + 40 + extra;
    const lab = W < 520 ? 96 : 150, der = 64;
    const todos = [...o.map((id) => vals[id]), ...ciu.map((k) => dato(ind, k, a))];
    const hi = Math.max(...todos, espana(ind, a) ?? 0, ue(ind, a) ?? 0);
    const x = (v) => lab + (v / (hi || 1)) * (W - lab - der);
    const fg = css("--fg"), muted = css("--muted"), base = css("--grey-line"), line = css("--line");
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(ind.nombre)} por comunidad, de más a menos">`;
    if (ind.objetivo) s += `<rect x="${x(0)}" y="${top - 4}" width="${x(ind.objetivo.valor) - x(0)}" height="${o.length * fila + 8}" fill="${css("--ok-bg")}"/>`;
    o.forEach((id, i) => {
      const y = top + i * fila, c = colorSel(id), v = vals[id];
      s += `<g class="barra" data-id="${id}" style="cursor:pointer" tabindex="0" role="button" aria-label="${esc(NOMBRE[id])}: ${esc(fmt(v, ind.unidad))}, ${esc(frenteEspana(ind, v, a))}">
        <rect x="0" y="${y}" width="${W}" height="${fila}" fill="transparent"/>
        <text x="${lab - 8}" y="${y + fila / 2 + 4}" text-anchor="end" font-size="12.5" fill="${c ? fg : muted}" font-weight="${c ? 700 : 400}">${esc(NOMBRE[id])}${marca(ind, id, a)}</text>
        <rect x="${x(0)}" y="${y + 5}" width="${Math.max(x(v) - x(0), 1)}" height="${fila - 10}" rx="3" fill="${c || base}" ${conCautela(ind, id, a) ? `fill-opacity="0.6"` : ""}/>
        <text x="${x(v) + 6}" y="${y + fila / 2 + 4}" font-size="12" fill="${fg}" class="num">${fmt(v, ind.unidad)}</text></g>`;
    });
    const y17 = top + o.length * fila;
    const ref = (v, txt, dash, dy) => v == null ? "" : `<line x1="${x(v)}" x2="${x(v)}" y1="${top - 4}" y2="${y17 + 4}" stroke="${fg}" stroke-dasharray="${dash}" stroke-width="1.3"/>
      <text x="${x(v)}" y="${y17 + dy}" text-anchor="middle" font-size="11.5" fill="${muted}">${txt}: ${fmt(v, ind.unidad)}</text>`;
    const e = espana(ind, a), u = ue(ind, a);
    const juntos = e != null && u != null && Math.abs(x(e) - x(u)) < 110;
    s += ref(e, "España", "5 3", 18) + ref(u, "UE-27", "1.5 2.5", juntos ? 34 : 18);
    s += `<line x1="${x(0)}" x2="${x(0)}" y1="${top}" y2="${y17}" stroke="${line}"/>`;
    if (ciu.length) {
      const y0 = y17 + 46;
      s += `<line x1="0" x2="${W}" y1="${y0 - 4}" y2="${y0 - 4}" stroke="${line}"/><text x="0" y="${y0 + 10}" font-size="11" fill="${muted}">Aparte (gestión directa del Ministerio${ind.encuesta ? " y muestra muy pequeña" : ""}):</text>`;
      ciu.forEach((k, i) => {
        const y = y0 + 14 + i * fila, v = dato(ind, k, a);
        s += `<g><text x="${lab - 8}" y="${y + fila / 2 + 4}" text-anchor="end" font-size="12.5" fill="${muted}" font-style="italic">${CIUDADES[k]}*${marca(ind, k, a)}</text>
          <rect x="${x(0)}" y="${y + 5}" width="${Math.max(x(v) - x(0), 1)}" height="${fila - 10}" rx="3" fill="none" stroke="${muted}" stroke-dasharray="3 2"/>
          <text x="${x(v) + 6}" y="${y + fila / 2 + 4}" font-size="12" fill="${fg}" class="num">${fmt(v, ind.unidad)}</text></g>`;
      });
    }
    s += `</svg>`;
    cont.innerHTML = s + (ind.objetivo ? `<p class="nota"><span class="muestra-ok"></span> ${esc(ind.objetivo.texto)}.${ind.encuesta ? " † Con precaución: muestra pequeña o dato de baja fiabilidad según Eurostat (barra más clara)." : ""}</p>` : "");
    cont.querySelectorAll(".barra").forEach((g) => {
      const id = g.dataset.id;
      g.onclick = () => { alternarSel(id); render(); };
      g.onkeydown = (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); alternarSel(id); render(); } };
      g.onmousemove = (ev) => showTip(`<b>${esc(NOMBRE[id])}</b><br>${fmt(vals[id], ind.unidad)}<br>${frenteEspana(ind, vals[id], a)}${conCautela(ind, id, a) ? `<br>† ${esc(textoCautela(ind, id, a))}` : ""}`, ev.clientX, ev.clientY);
      g.onmouseleave = hideTip;
    });
  }

  // Reparto: barras al 100 % (pública, concertada, privada no concertada) por comunidad, ordenadas por la parte elegida
  function reparto(cont, ind, a) {
    // Siempre en el mismo orden y color (pública, concertada, privada), elija lo que se elija para ordenar las filas
    const ORDEN = ["publica", "concertada", "privada_no_concertada"];
    const k = varDe(ind), vars = ind.variantes.slice().sort((p, q) => ORDEN.indexOf(p.clave.split("|")[1]) - ORDEN.indexOf(q.clave.split("|")[1]));
    const cols = [css("--s1"), css("--s2"), css("--s3")];
    const ids = ordenados(valores(ind, a, k));
    const ciu = IDS_CIU.filter((c) => dato(ind, c, a, k) != null);
    const filas = [...ids, "ES", ...ciu];
    const W = Math.max(320, cont.clientWidth || 800), fila = 26, top = 30, lab = W < 520 ? 96 : 150, der = 8;
    const H = top + filas.length * fila + 30;
    const x = (p) => lab + (p / 100) * (W - lab - der);
    const fg = css("--fg"), muted = css("--muted"), surf = css("--surface");
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Reparto del alumnado por titularidad en cada comunidad">`;
    let lx = lab;
    vars.forEach((v, i) => { s += `<rect x="${lx}" y="6" width="12" height="12" rx="2" fill="${cols[i]}"/><text x="${lx + 16}" y="16" font-size="12" fill="${fg}">${esc(v.etiqueta)}</text>`; lx += v.etiqueta.length * 7 + 34; });
    filas.forEach((id, n) => {
      const y = top + n * fila + (n >= ids.length ? 8 : 0) + (CIUDADES[id] ? 8 : 0);
      let acc = 0;
      s += `<g class="rep" data-id="${id}"><text x="${lab - 8}" y="${y + fila / 2 + 4}" text-anchor="end" font-size="12.5" fill="${id === S.com || id === "ES" ? fg : muted}" font-weight="${id === "ES" || id === S.com ? 700 : 400}" ${CIUDADES[id] ? 'font-style="italic"' : ""}>${esc(id === "ES" ? "España" : NOMBRE[id])}${CIUDADES[id] ? "*" : ""}</text>`;
      vars.forEach((v, i) => {
        const p = dato(ind, id, a, v.clave) ?? 0;
        s += `<rect x="${x(acc)}" y="${y + 4}" width="${Math.max(0, x(acc + p) - x(acc))}" height="${fila - 8}" fill="${cols[i]}" stroke="${surf}" stroke-width="1"/>`;
        if (x(acc + p) - x(acc) > 30) s += `<text x="${x(acc) + 4}" y="${y + fila / 2 + 4}" font-size="11" fill="${textoSobre(cols[i])}" class="num">${nf(0).format(p)}</text>`;
        acc += p;
      });
      s += `</g>`;
    });
    s += `</svg>`;
    cont.innerHTML = s + `<p class="nota">Porcentajes redondeados dentro de las barras; el detalle, al pasar el ratón o en la tabla. * Ceuta y Melilla, aparte.</p>`;
    cont.querySelectorAll(".rep").forEach((g) => {
      const id = g.dataset.id;
      g.onmousemove = (ev) => showTip(`<b>${esc(id === "ES" ? "España" : NOMBRE[id])}</b>, ${etq(ind, a)}<br>${vars.map((v, i) => `<span style="color:${cols[i]}">■</span> ${esc(v.etiqueta)}: ${fmt(dato(ind, id, a, v.clave), ind.unidad)}`).join("<br>")}`, ev.clientX, ev.clientY);
      g.onmouseleave = hideTip;
    });
  }

  function ticks(min, max, n = 5) {
    const paso0 = (max - min) / n, mag = Math.pow(10, Math.floor(Math.log10(paso0)));
    const paso = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((p) => p >= paso0);
    const out = []; for (let v = Math.ceil(min / paso) * paso; v <= max + 1e-9; v += paso) out.push(+v.toFixed(6));
    return out;
  }
  function aniosEje(ancho, anios, enCursos) {
    const anchoEtiqueta = 11 * (enCursos ? 4.2 : 2.6) + 10, a0 = anios[0], aN = anios.at(-1), porAnio = ancho / Math.max(1, aN - a0);
    const paso = [2, 4, 5, 10].find((p) => p * porAnio >= anchoEtiqueta) || 10;
    return [...anios.filter((a) => (a - a0) % paso === 0 && (aN - a) * porAnio >= anchoEtiqueta), aN];
  }

  // Evolución: 17 líneas grises, destacadas en color, España discontinua, UE-27 punteada, franja del objetivo,
  // rupturas de serie (marcas abajo), tramo de avance y, si se pide, leyes y hechos (líneas verticales).
  function lineas(cont, ind) {
    const fechas = periodos(ind), inicio = primero(ind), fin = ultimo(ind), k = varDe(ind);
    const W = Math.max(320, cont.clientWidth || 800), H = W < 520 ? 320 : 400;
    const L = W < 520 ? 44 : 52, R = W < 520 ? 70 : 118;
    const hitos = S.leyes ? DATA.hitos.filter((h) => h.anio >= inicio && h.anio <= fin + 1) : [];
    const x = (a) => L + ((a - inicio) / Math.max(1, fin - inicio)) * (W - L - R);
    const estrecho = W < 620;
    const finFila = [];
    // En cursos, cada punto está en el año de inicio (2024-25 en 2024): una ley de marzo de 2025 cae dentro de ese curso
    const posHitos = hitos.map((h, i) => {
      const f = new Date(h.fecha), xa = x(h.anio + (f - new Date(h.anio, 0, 1)) / 31557600000 - (esCurso(ind) ? 0.67 : 0));
      const txt = estrecho ? String(i + 1) : h.corto, ancho = txt.length * 6.2 + 8;
      let kk = 0; while (finFila[kk] != null && xa < finFila[kk]) kk++;
      finFila[kk] = xa + ancho;
      return { xa, k: kk, ancho, txt };
    }).filter((p) => p.xa >= L - 1 && p.xa <= W - R + 1);
    const T = 14 + finFila.length * 13, B = 46;
    const sr = serieDe(ind);
    const todos = [...IDS, "ES"].flatMap((id) => sr[id] || []).concat(ind.ue?.[k] || []).filter((v) => v != null);
    const ymin = 0;
    let ymax = Math.max(...todos) * 1.05;
    const tk = ticks(ymin, ymax); ymax = Math.max(ymax, tk.at(-1));
    const y = (v) => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B);
    const fg = css("--fg"), muted = css("--muted"), line = css("--line"), grey = css("--grey-line");
    const path = (serie = []) => serie.map((v, i) => v == null ? "" : `${!i || serie[i - 1] == null ? "M" : "L"}${x(fechas[i]).toFixed(1)},${y(v).toFixed(1)}`).join("");
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Evolución de ${esc(ind.nombre)}">`;
    if (ind.objetivo) s += `<rect x="${L}" y="${y(ind.objetivo.valor)}" width="${W - L - R}" height="${y(0) - y(ind.objetivo.valor)}" fill="${css("--ok-bg")}"/>
      <text x="${L + 6}" y="${y(0) - 6}" font-size="10.5" fill="${css("--ok")}">Objetivo UE 2030: menos del ${nf(0).format(ind.objetivo.valor)} %</text>`;
    if (ind.avance.length) {
      const i0 = ind.avance[0], a0 = fechas[i0], medio = i0 > 0 ? (x(a0) - x(fechas[i0 - 1])) / 2 : 0;
      s += `<rect x="${x(a0) - medio}" y="${T}" width="${x(fin) - x(a0) + medio}" height="${H - T - B}" fill="${css("--note-bg")}"/><text x="${x(fin)}" y="${T + 12}" text-anchor="end" font-size="10.5" fill="${css("--note")}">avance</text>`;
    }
    tk.forEach((v) => { s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="${line}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="${muted}">${fmtCorto(v, ind.unidad)}</text>`; });
    aniosEje(W - L - R, fechas, esCurso(ind)).forEach((a) => { s += `<text x="${x(a)}" y="${H - B + 16}" text-anchor="middle" font-size="11" fill="${muted}">${etq(ind, a)}</text>`; });
    const anioRup = [...new Set(ind.rupturas.filter((r) => r.territorio !== "UE27").map((r) => r.anio))];
    anioRup.forEach((a) => { s += `<path d="M${x(a) - 4},${H - B + 24} l4,6 l4,-6" fill="none" stroke="${muted}" stroke-width="1.4"/>`; });
    if (anioRup.length) s += `<text x="${L}" y="${H - 6}" font-size="10.5" fill="${muted}">⌄ ruptura de serie (${lista(anioRup.map(String))})</text>`;
    posHitos.forEach(({ xa, k: kk, ancho, txt }) => {
      const izq = xa + ancho > W - 4;
      s += `<line x1="${xa}" x2="${xa}" y1="${12 + kk * 13 + 3}" y2="${H - B}" stroke="${css("--note")}" stroke-dasharray="2 3"/>
        <text x="${izq ? xa - 3 : xa + 3}" y="${12 + kk * 13}" text-anchor="${izq ? "end" : "start"}" font-size="10.5" fill="${css("--note")}" font-weight="600">${esc(txt)}</text>`;
    });
    IDS.filter((id) => !colorSel(id)).forEach((id) => { s += `<path d="${path(sr[id])}" fill="none" stroke="${grey}" stroke-width="1.1"/>`; });
    const etiquetas = [];
    if (ind.ue?.[k]) { s += `<path d="${path(ind.ue[k])}" fill="none" stroke="${fg}" stroke-width="1.5" stroke-dasharray="1.5 2.5"/>`; etiquetas.push({ txt: "UE-27", v: ind.ue[k].at(-1), c: muted, b: 400 }); }
    if (sr.ES) { s += `<path d="${path(sr.ES)}" fill="none" stroke="${fg}" stroke-width="1.6" stroke-dasharray="5 3"/>`; etiquetas.push({ txt: "España", v: sr.ES.at(-1), c: muted, b: 400 }); }
    S.sel.forEach((sl) => {
      const c = css(SLOTS[sl.slot]), serie = sr[sl.id] || [];
      s += `<path d="${path(serie)}" fill="none" stroke="${c}" stroke-width="2.5" stroke-linejoin="round"/>`;
      serie.forEach((v, i) => { if (v != null && bajaFiab(ind, sl.id, fechas[i])) s += `<circle cx="${x(fechas[i])}" cy="${y(v)}" r="3" fill="${css("--surface")}" stroke="${c}" stroke-width="1.5"/>`; });
      const v = serie.at(-1);
      if (v != null) { s += `<circle cx="${x(fin)}" cy="${y(v)}" r="4" fill="${c}" stroke="${css("--surface")}" stroke-width="2"/>`; etiquetas.push({ txt: NOMBRE[sl.id] + marca(ind, sl.id, fin), v, c: fg, b: 700, abr: ABR[sl.id] }); }
    });
    etiquetas.filter((e) => e.v != null).sort((p, q) => y(p.v) - y(q.v)).reduce((ult, e) => {
      const yy = Math.max(y(e.v) + 4, ult + 14);
      s += `<text x="${x(fin) + 8}" y="${yy}" font-size="12" font-weight="${e.b}" fill="${e.c}">${esc(W < 520 && e.abr ? e.abr : e.txt)}</text>`;
      return yy;
    }, -Infinity);
    s += `<line id="cruz" x1="0" x2="0" y1="${T}" y2="${H - B}" stroke="${muted}" visibility="hidden"/><rect id="zona" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/></svg>`;
    const huecos = S.sel.some((sl) => (ind.baja[k]?.[sl.id] || []).length);
    const notasSel = S.sel.flatMap((sl) => notasDe(ind, sl.id).map((n) => ({ id: sl.id, n })));
    cont.innerHTML = s + `<div class="notas-oficiales">${huecos ? `<p>Punto hueco: dato de baja fiabilidad según Eurostat.</p>` : ""}` +
      (ind.rupturas.length ? plegable("evo-rupturas", "Qué son las rupturas de serie", `<p>Años en que la fuente avisa de que la serie cambia (método de la encuesta, definición…). Comparar a los dos lados es solo aproximado.</p><ul>${ind.rupturas.map((r) => `<li><b>${r.anio}</b> (${r.territorio === "todas" ? "todas" : r.territorio === "UE27" ? "UE-27" : NOMBRE[r.territorio] || r.territorio}): ${esc(r.texto)}</li>`).join("")}</ul>`) : "") +
      (notasSel.length ? plegable("evo-notas", `Notas de la fuente sobre ${esc(lista([...new Set(notasSel.map((q) => NOMBRE[q.id]))]))} (${notasSel.length})`, `<ul>${notasSel.map(({ id, n }) => `<li><b>${esc(NOMBRE[id])}${n.periodos.length ? `, ${esc(lista(n.periodos))}` : ""}.</b> ${esc(n.texto)}</li>`).join("")}</ul>`) : "") +
      (posHitos.length ? plegable("evo-leyes", "Leyes y hechos marcados", `<ul>${hitos.map((h, i) => `<li><b>${estrecho ? `${i + 1}. ` : ""}${esc(h.corto)}</b> (${h.fecha.split("-").reverse().join("/")}): <a href="${h.url}">${esc(h.titulo)}</a></li>`).join("")}</ul>`) : "") + `</div>`;
    const svg = cont.querySelector("svg"), cruz = svg.querySelector("#cruz");
    svg.querySelector("#zona").onmousemove = (e) => {
      const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
      const an = inicio + ((px - L) / (W - L - R)) * (fin - inicio);
      const i = fechas.reduce((b, f, j) => Math.abs(f - an) < Math.abs(fechas[b] - an) ? j : b, 0);
      const a = fechas[i];
      cruz.setAttribute("x1", x(a)); cruz.setAttribute("x2", x(a)); cruz.setAttribute("visibility", "visible");
      const filasTip = S.sel.map((sl) => `<span style="color:${css(SLOTS[sl.slot])}">●</span> ${esc(NOMBRE[sl.id])}: ${fmt(sr[sl.id]?.[i], ind.unidad)}${marca(ind, sl.id, a)}`);
      if (sr.ES) filasTip.push(`España: ${fmt(sr.ES[i], ind.unidad)}`);
      if (ind.ue?.[k]) filasTip.push(`UE-27: ${fmt(ind.ue[k][i], ind.unidad)}`);
      const rup = ind.rupturas.filter((x2) => x2.anio === a && x2.territorio !== "UE27");
      showTip(`<b>${etqEstado(ind, a)}</b><br>${filasTip.join("<br>")}${rup.length ? `<div class="tip-marcas">Ruptura de serie este año</div>` : ""}`, e.clientX, e.clientY);
    };
    svg.querySelector("#zona").onclick = svg.querySelector("#zona").onmousemove;
    svg.querySelector("#zona").onmouseleave = () => { cruz.setAttribute("visibility", "hidden"); hideTip(); };
  }

  function tabla(cont, ind, a) {
    const u = ind.unidad, a0 = primero(ind);
    const vals = valores(ind, a), o = ordenados(vals), e = espana(ind, a);
    const cambio = (id) => { const v0 = dato(ind, id, a0), v1 = dato(ind, id, a); return v0 == null || v1 == null || a === a0 ? "—" : fmtDif(ind, v1 - v0); };
    const fila = (id, cls = "") => {
      const v = dato(ind, id, a);
      return `<tr class="${cls}${id === S.com ? " tuya" : ""}"><td>${esc(NOMBRE[id] || "España")}${marca(ind, id, a)}</td><td>${fmt(v, u)}</td><td>${id === "ES" ? "" : v == null || e == null ? "—" : fmtDif(ind, v - e)}</td><td>${cambio(id)}</td></tr>`;
    };
    const cab = `<tr><th>Territorio</th><th>${etq(ind, a)}</th><th>Frente a España</th><th>Desde ${etq(ind, a0)}</th></tr>`;
    const eu = ue(ind, a), eu0 = ind.ue?.[varDe(ind)]?.[0] ?? null;
    const ciu = IDS_CIU.filter((k) => dato(ind, k, a) != null);
    cont.innerHTML = `<div class="tabla-wrap"><table class="tabla t-sin-num"><thead>${cab}</thead><tbody>${o.map((id) => fila(id)).join("")}
      <tr class="sep"><td colspan="4">Referencias</td></tr>${fila("ES", "ref")}${eu != null ? `<tr class="ref"><td>UE-27 (Eurostat)</td><td>${fmt(eu, u)}</td><td>${e == null ? "—" : fmtDif(ind, eu - e)}</td><td>${eu0 == null || a === a0 ? "—" : fmtDif(ind, eu - eu0)}</td></tr>` : ""}
      ${ciu.length ? `<tr class="sep"><td colspan="4">Aparte: gestión directa del Ministerio</td></tr>${ciu.map((k) => fila(k, "ciudad")).join("")}` : ""}</tbody></table></div>
      <p class="nota">${ind.encuesta ? "† Con precaución: muestra pequeña (Ministerio) o dato de baja fiabilidad (Eurostat). " : ""}${ind.rupturas.length ? `Entre ${etq(ind, a0)} y ${etq(ind, a)} puede haber rupturas de serie: ver «¿Qué mide esto?».` : ""}${esAvance(ind, a) ? " Dato de avance." : ""}</p>
      <div class="cta" style="margin-top:14px"><button type="button" class="btn" id="csv">Descargar CSV (${etq(ind, primero(ind))} a ${etq(ind, ultimo(ind))}${ind.variantes.length > 1 ? `, por ${dimVar(ind)}` : ""})</button></div>`;
    $("#csv").onclick = () => descargarCSV(ind);
  }
  function descargarCSV(ind) {
    const n = (v) => v == null ? "" : String(+v.toFixed(4)).replace(".", ",");
    const filas = [["indicador", "territorio", "periodo", dimVar(ind), "valor", "unidad", "estado", "fiabilidad", "precaucion", "fuente"]];
    const fuente = (id) => id === "UE27" ? ind.fuentes.find((f) => f.id === "eurostat")?.url : ind.fuentes[0].url;
    const unidad = ind.unidad === "pct" ? "%" : "alumnos por profesor";
    for (const v of ind.variantes) {
      for (const id of ["ES", ...IDS, ...IDS_CIU]) ind.periodos.forEach((a, i) => {
        const x = dato(ind, id, a, v.clave);
        if (x != null) filas.push([ind.nombre, NOMBRE[id] || "España", ind.etiquetas[i], v.etiqueta, n(x), unidad, esAvance(ind, a) ? "avance" : ind.estado, ind.fiabilidad, textoCautela(ind, id, a, v.clave), fuente(id)]);
      });
      if (ind.ue?.[v.clave]) ind.periodos.forEach((a, i) => { const x = ind.ue[v.clave][i]; if (x != null) filas.push([ind.nombre, "UE-27", ind.etiquetas[i], v.etiqueta, n(x), unidad, ind.estado, ind.fiabilidad, "", fuente("UE27")]); });
    }
    const csv = "﻿" + filas.map((f) => f.map((c) => /[;"\n]/.test(String(c)) ? `"${String(c).replace(/"/g, '""')}"` : c).join(";")).join("\r\n");
    const el = document.createElement("a");
    el.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    el.download = `${ind.id}.csv`; document.body.appendChild(el); el.click(); el.remove();
  }

  // Imagen PNG de un gráfico: título, el propio SVG, la leyenda (si la hay) y la fuente.
  function descargarPNG(svgEl, nombre, titulo, leyendaEl, ind) {
    const vb = svgEl.viewBox.baseVal, W = vb.width, H = vb.height;
    const ancho = Math.max(W, 720), k = Math.min(1, (ancho - 48) / W), w = W * k, h = H * k;
    const fondo = css("--surface"), fg = css("--fg"), muted = css("--muted");
    const palabras = titulo.split(" "), lineasT = [""];
    palabras.forEach((pa) => { const l = lineasT.at(-1); if ((l + " " + pa).length > ancho / 11 && l) lineasT.push(pa); else lineasT[lineasT.length - 1] = (l ? l + " " : "") + pa; });
    const cab = 24 + lineasT.length * 26 + 10;
    let leg = "", legH = 0;
    if (leyendaEl) {
      const items = [...leyendaEl.querySelectorAll(".clase")].map((c) => ({ color: c.querySelector("i").style.background, txt: (c.querySelector("b") || c).textContent.trim() }));
      const anchoItem = (ancho - 48) / Math.max(items.length, 1);
      items.forEach((it, i) => { leg += `<rect x="${24 + i * anchoItem}" y="${cab + h + 12}" width="${anchoItem - 4}" height="10" rx="3" fill="${it.color}"/><text x="${24 + i * anchoItem}" y="${cab + h + 38}" font-size="12" fill="${fg}">${esc(it.txt)}</text>`; });
      legH = items.length ? 48 : 0;
    }
    const total = cab + h + legH + 56;
    const f = ind.fuentes[0].corto || ind.fuentes[0].nombre;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${ancho}" height="${total}" font-family="Inter, Arial, sans-serif">
      <rect width="100%" height="100%" fill="${fondo}"/>
      ${lineasT.map((l, i) => `<text x="24" y="${34 + i * 26}" font-size="20" font-weight="700" fill="${fg}">${esc(l)}</text>`).join("")}
      <svg x="${(ancho - w) / 2}" y="${cab}" width="${w}" height="${h}" viewBox="0 0 ${W} ${H}">${svgEl.innerHTML}</svg>${leg}
      <text x="24" y="${total - 30}" font-size="12" fill="${muted}">Fuente: ${esc(f)} · fiabilidad ${ind.fiabilidad} (${esc(FIAB[ind.fiabilidad].toLowerCase())}) · ${ind.estado}</text>
      <text x="24" y="${total - 12}" font-size="12" fill="${muted}">educacion-ccaa.vercel.app</text></svg>`;
    const img = new Image();
    img.onload = () => {
      const cv = document.createElement("canvas"); cv.width = ancho * 2; cv.height = total * 2;
      const cx = cv.getContext("2d"); cx.scale(2, 2); cx.drawImage(img, 0, 0);
      cv.toBlob((blob) => { const el = document.createElement("a"); el.href = URL.createObjectURL(blob); el.download = `${nombre.replace(/[^a-z0-9_-]+/gi, "_")}.png`; document.body.appendChild(el); el.click(); el.remove(); }, "image/png");
    };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }
  function botonPNG(cont, texto, accion) {
    cont.innerHTML = `<button type="button" class="btn sm">${texto}</button>`;
    cont.querySelector("button").onclick = accion;
  }
  // Cambia algo sin mover la pantalla: el bloque que estabas mirando se queda en su sitio.
  function sinMover(accion) {
    const bajo = document.elementFromPoint(innerWidth / 2, Math.min(innerHeight / 2, 160));
    const ancla = bajo && bajo.closest(".panel, .intro");
    const antes = ancla ? ancla.getBoundingClientRect().top : null;
    accion();
    if (ancla && antes != null) scrollBy(0, ancla.getBoundingClientRect().top - antes);
  }

  // ---------- enlace compartible: el estado de Datos va en la dirección ----------
  // #datos?tema=…&dato=…&periodo=2024-25&sexo=m&tit=publica&ccaa=md&graf=evolucion&leyes=si&sel=an,md
  function guardarEnlace() {
    const ind = IND[S.ind], p = new URLSearchParams();
    if (S.tema !== "resumen") p.set("tema", S.tema);
    p.set("dato", S.ind);
    if (S.anio !== ultimo(ind)) p.set("periodo", etq(ind, S.anio));
    // Solo si no es la variante por defecto del indicador
    const [sx, tt] = varDe(ind).split("|");
    if (varDe(ind) !== ind.variantes[0].clave) { if (sx !== "total") p.set("sexo", sx); p.set("tit", tt); }
    if (S.com !== "AN") p.set("ccaa", S.com.toLowerCase());
    if (S.vistaE !== "ranking") p.set("graf", S.vistaE);
    if (S.leyes) p.set("leyes", "si");
    const sel = S.sel.map((s) => s.id.toLowerCase()).join(",");
    if (sel !== "an") p.set("sel", sel);
    const hash = "#datos?" + p.toString();
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }
  function leerEnlace(qs) {
    const p = new URLSearchParams(qs);
    if (IND[p.get("dato")]) S.ind = p.get("dato");
    const ind = IND[S.ind];
    S.tema = TEMAS.some((t) => t.id === p.get("tema")) ? p.get("tema") : ind.resumen ? "resumen" : ind.grupo;
    if (!indsTema().some((i) => i.id === S.ind)) S.tema = ind.grupo;
    const i = ind.etiquetas.indexOf(p.get("periodo") || p.get("anio") || ""); if (i >= 0) S.anio = ind.periodos[i];
    S.var = `${["h", "m"].includes(p.get("sexo")) ? p.get("sexo") : "total"}|${p.get("tit") || "total"}`;
    if (!ind.variantes.some((v) => v.clave === S.var)) S.var = "";
    const c = (p.get("ccaa") || "").toUpperCase(); if (NOMBRE[c]) S.com = c;
    if (["ranking", "reparto", "evolucion", "tabla"].includes(p.get("graf"))) S.vistaE = p.get("graf");
    S.leyes = p.get("leyes") === "si";
    if (p.has("sel")) S.sel = p.get("sel").toUpperCase().split(",").filter((k) => NOMBRE[k]).slice(0, 3).map((id, slot) => ({ id, slot }));
  }

  // ---------- TU COMUNIDAD ----------
  // Una fila por dato: valor, diferencia con España, puntos de las 17 (la raya es España) y evolución.
  function filaInd(ind, id, vs, k) {
    const a = ultimo(ind);
    const titulo = esTotal(ind, k) || ind.variantes.length === 1 ? ind.corto : ind.reparto ? `En la ${varEtq(ind, k).toLowerCase()}` : `${ind.corto}: ${varEtq(ind, k).toLowerCase()}`;
    const vals = valores(ind, a, k), o = ordenados(vals), v = dato(ind, id, a, k), e = espana(ind, a, k);
    const W = 300, H = 34, P = 8;
    const pts = [...o.map((q) => vals[q]), e, v, vs ? dato(ind, vs, a, k) : null].filter((q) => q != null);
    const min = Math.min(...pts), max = Math.max(...pts);
    const x = (val) => P + ((val - min) / (max - min || 1)) * (W - 2 * P);
    const grey = css("--grey-line"), fg = css("--fg"), acc = css("--accent"), surf = css("--surface"), muted = css("--muted");
    let strip = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"><line x1="${P}" x2="${W - P}" y1="17" y2="17" stroke="${css("--line")}" stroke-width="2"/>`;
    o.filter((q) => q !== id && q !== vs).forEach((q) => { strip += `<circle cx="${x(vals[q])}" cy="17" r="4.5" fill="${grey}"><title>${esc(NOMBRE[q])}: ${fmt(vals[q], ind.unidad)}</title></circle>`; });
    if (e != null) strip += `<line x1="${x(e)}" x2="${x(e)}" y1="5" y2="29" stroke="${fg}" stroke-width="1.6"/>`;
    const vv = vs ? dato(ind, vs, a, k) : null;
    if (vv != null) strip += `<circle cx="${x(vv)}" cy="17" r="6" fill="${css("--s2")}" stroke="${surf}" stroke-width="2"><title>${esc(NOMBRE[vs])}: ${fmt(vv, ind.unidad)}</title></circle>`;
    if (v != null) strip += `<circle cx="${x(v)}" cy="17" r="7.5" fill="${acc}" stroke="${surf}" stroke-width="2.5"/>`;
    strip += `<text x="${P}" y="${H}" font-size="9" fill="${muted}">menos</text><text x="${W - P}" y="${H}" font-size="9" fill="${muted}" text-anchor="end">más</text></svg>`;
    const sr = serieDe(ind, k), serie = sr[id] || [], esp = sr.ES || [], otra = vs ? sr[vs] : null;
    const todos = [...serie, ...esp, ...(otra || [])].filter((z) => z != null);
    const smin = Math.min(...todos), smax = Math.max(...todos), sw = 120, sh = 34, ki = indice(ind, a);
    const sx = (i) => 2 + (i / Math.max(1, ind.periodos.length - 1)) * (sw - 8), sy = (z) => 4 + (1 - (z - smin) / (smax - smin || 1)) * (sh - 8);
    const path = (s2) => s2.map((z, i) => z == null ? "" : `${i && s2[i - 1] != null ? "L" : "M"}${sx(i).toFixed(1)},${sy(z).toFixed(1)}`).join("");
    const spark = `<svg viewBox="0 0 ${sw} ${sh}" aria-label="Evolución ${etq(ind, primero(ind))} a ${etq(ind, a)}"><path d="${path(esp)}" fill="none" stroke="${fg}" stroke-width="1.1" stroke-dasharray="3 2"/>${otra ? `<path d="${path(otra)}" fill="none" stroke="${css("--s2")}" stroke-width="1.5"/>` : ""}<path d="${path(serie)}" fill="none" stroke="${acc}" stroke-width="1.8"/>${v != null ? `<circle cx="${sx(ki)}" cy="${sy(v)}" r="3.5" fill="${acc}" stroke="${surf}" stroke-width="1.5"/>` : ""}</svg><div class="pos">${etq(ind, primero(ind))} a ${etq(ind, a)} · discontinua: España</div>`;
    const nn = notasDe(ind, id, etq(ind, a));
    return `<div class="ind">
      <div><div class="n">${esc(titulo)}${marca(ind, id, a, k)}</div><div class="pos">${chipFiab(ind.fiabilidad, "span")} ${etqEstado(ind, a)} · España: ${fmt(e, ind.unidad)}${conCautela(ind, id, a, k) ? `<br>† ${esc(textoCautela(ind, id, a, k))}` : ""}${nn.length ? `<br>Nota de la fuente: ${esc(nn[0].texto)}` : ""}</div></div>
      <div><div class="val">${fmt(v, ind.unidad)}</div><div class="delta">${frenteEspana(ind, v, a, k)}</div>${vs ? `<div class="vs">${esc(NOMBRE[vs])}: ${fmt(vv, ind.unidad)}${marca(ind, vs, a, k)}</div>` : ""}</div>
      <div class="strip">${strip}</div>
      <div class="spark">${spark}</div>
    </div>`;
  }

  function renderComunidad() {
    const id = S.com, ciu = !!CIUDADES[id];
    const p = new URLSearchParams();
    if (S.vs) p.set("vs", S.vs.toLowerCase());
    const hash = "#comunidad-" + id.toLowerCase() + (p.toString() ? "?" + p.toString() : "");
    if (location.hash !== hash) history.replaceState(null, "", hash);
    const opciones = (sel, excluir) => [...IDS, ...IDS_CIU].filter((k) => k !== excluir).sort((x, y) => NOMBRE[x].localeCompare(NOMBRE[y], "es")).map((k) => `<option value="${k}" ${k === sel ? "selected" : ""}>${esc(NOMBRE[k])}${CIUDADES[k] ? " (ciudad autónoma)" : ""}</option>`).join("");
    $("#c-sel").innerHTML = opciones(id);
    $("#c-sel").onchange = (e) => { S.com = e.target.value; render(); };
    tileMap($("#c-mapa"), Object.fromEntries(IDS.map((k) => [k, 1])), DATA.inds[0], { neutro: true, selIds: [id], onClick: (k) => { S.com = k; render(); } });
    $("#c-nombre").textContent = NOMBRE[id];
    if (S.vs === id) S.vs = "";
    $("#c-vs").innerHTML = `<option value="">Nadie</option>` + opciones(S.vs, id);
    $("#c-vs").onchange = (e) => { S.vs = e.target.value; render(); };
    $("#c-leyenda-vs").innerHTML = S.vs ? `<span><i style="background:${css("--accent")}"></i>${esc(NOMBRE[id])}</span><span><i style="background:${css("--s2")}"></i>${esc(NOMBRE[S.vs])}</span>` : "";
    // Resumen: los datos clave, cada uno con su periodo y su diferencia con España
    const claves = DATA.inds.filter((i) => i.resumen).map((i) => {
      const a = ultimo(i), k = i.variantes[0].clave, v = dato(i, id, a, k);
      return v == null ? "" : `<li>${esc(i.corto)}: <strong>${fmt(v, i.unidad)}</strong>${marca(i, id, a, k)} en ${etq(i, a)} (${frenteEspana(i, v, a, k)}).</li>`;
    }).join("");
    $("#c-resumen").innerHTML = `<ul class="claves">${claves}</ul>` +
      (ciu ? `<span class="cautela">Ciudad autónoma: su educación la gestiona directamente el Ministerio y su muestra en las encuestas es muy pequeña. Se muestra aparte, sin compararla con las 17.</span>` : "");
    const temas = DATA.temas.map((t) => {
      const inds = DATA.inds.filter((i) => i.grupo === t.id);
      const filas = inds.flatMap((i) => (i.filas_ficha || [i.variantes[0].clave]).map((k) => filaInd(i, id, S.vs, k))).join("");
      return `<div class="bloque"><h2>${esc(t.nombre)}</h2>
        <p class="sub">El último dato de cada indicador. Cada punto gris es otra comunidad; la raya, España. A la derecha, la evolución.</p>
        <div class="filas">${filas}</div>
        <div class="notas-min">${plegable(`ficha-${t.id}`, "¿Qué mide esto?", inds.map((i) => `<h3>${esc(i.nombre)}</h3>${queMide(i, `ficha-${i.id}`)}`).join(""))}</div></div>`;
    }).join("");
    $("#c-bloques").innerHTML = temas + `<div class="bloque"><h2>Lo que todavía no está</h2><p class="sub">Iremos añadiendo financiación (gasto público y conciertos), alumnos por clase, resultados (PISA y otras evaluaciones, con su margen de error) y equidad, siempre con datos oficiales y su fuente. Si un dato no existe, lo diremos.</p></div>`;
  }

  // ---------- CÓMO LEER LOS DATOS ----------
  function renderMetodo() {
    if ($("#m-cuerpo").dataset.listo) return;
    const trampas = TRAMPAS.map((t, i) => `<article class="trampa" id="metodo-trampa-${i + 1}"><h3>${i + 1}. ${esc(t.titulo)}</h3>
      <dl><dt>De dónde sale</dt><dd>${t.origen}</dd><dt>Qué denominador usa</dt><dd>${t.denominador}</dd><dt>Qué no mide</dt><dd>${t.noMide}</dd></dl>${t.enWeb ? `<p class="en-web">${t.enWeb}</p>` : ""}</article>`).join("");
    const inds = DATA.temas.map((t) => `<h3 class="tema-m">${esc(t.nombre)}</h3>` + DATA.inds.filter((i) => i.grupo === t.id).map((i) => plegable(`metodo-${i.id}`, esc(i.nombre), queMide(i, `metodo-${i.id}`))).join("")).join("");
    $("#m-cuerpo").innerHTML = `<h1>Cómo leer los datos</h1>
      <p>Esta web reúne datos oficiales sobre la educación en cada comunidad autónoma. No valoramos ni explicamos las diferencias: damos la cifra, de dónde sale, de qué año o curso es y cuánto podemos fiarnos de ella.</p>
      <nav class="indice" aria-label="En esta página"><a href="#metodo-fiabilidad">Fiabilidad A, B y C</a><a href="#metodo-espana">España y las medias</a><a href="#metodo-ciudades">Ceuta y Melilla</a><a href="#metodo-trampas">Siete trampas</a><a href="#metodo-indicadores">Cada indicador</a><a href="#metodo-leyes">Leyes y hechos</a><a href="#metodo-error">¿Un error?</a></nav>
      <h2 id="metodo-fiabilidad">Fiabilidad A, B y C</h2>
      <p>Cada cifra lleva una letra:</p>
      <dl><dt>${chipFiab("A")} Estadística oficial periódica</dt><dd>Publicada por un organismo oficial (Ministerio, INE, Eurostat…) cada año o cada curso, con un método estable.</dd>
        <dt>${chipFiab("B")} Oficial, pero puntual o con limitaciones</dt><dd>Oficial, pero de un solo año, con cambios de método o con una cobertura incompleta.</dd>
        <dt>${chipFiab("C")} Estudio o estimación</dt><dd>Cifras de estudios o informes que no son estadística oficial. Irán en un bloque aparte: «Estudios, no estadística oficial».</dd></dl>
      <p>Además se indica el <b>estado</b> del dato: previsión, avance, provisional o definitivo, como lo publique la fuente. Y el periodo: año natural (la Encuesta de Población Activa) o curso escolar (la estadística del Ministerio), por ejemplo 2024-25.</p>
      <h2 id="metodo-espana">España y las medias</h2>
      <p>«España» es siempre la cifra oficial del conjunto del país, tal como la publica la fuente. No es la media de las 17 comunidades: las que tienen más alumnado pesan más, como en la realidad. Por eso puede no coincidir con lo que saldría al promediar las cifras de las comunidades.</p>
      <p>Cuando una cifra sale de una encuesta (como la EPA), no damos puestos del 1 al 17: con el margen de error de la muestra, muchas diferencias entre comunidades son pequeñas. Decimos si está por encima o por debajo de España y cuánto.</p>
      <h2 id="metodo-ciudades">Ceuta y Melilla</h2>
      <p>Ceuta y Melilla no tienen transferida la educación no universitaria: sus centros dependen directamente del Ministerio de Educación. Además, en las encuestas tienen muestras muy pequeñas. Por eso se muestran aparte, con su propia ficha, pero no cambian los colores del mapa ni se comparan con las 17.</p>
      <h2 id="metodo-trampas">Siete trampas al leer datos de educación</h2>
      <p>Para cada una: de dónde sale el dato, qué denominador usa y qué no mide. Algunas se refieren a datos que todavía no están en la web; las dejamos explicadas desde ya.</p>
      <div class="trampas">${trampas}</div>
      <h2 id="metodo-indicadores">Cada indicador</h2>
      <p>Qué mide, cómo se calcula, qué no mide, las notas de la fuente y lo que comprobamos al descargar los datos.</p>${inds}
      <h2 id="metodo-leyes">Leyes y hechos</h2>
      <p>En los gráficos de evolución se pueden marcar estas normas (interruptor «Leyes y hechos», apagado al principio). Es la fecha de la norma en el BOE, no la de su aplicación en las aulas, que suele ser gradual. Que un cambio en una serie coincida con una ley no quiere decir que la ley lo cause.</p>
      <ul>${DATA.hitos.map((h) => `<li><b>${esc(h.corto)}</b> (${h.fecha.split("-").reverse().join("/")}): <a href="${h.url}">${esc(h.titulo)}</a></li>`).join("")}</ul>
      <h2 id="metodo-error">¿Has visto un error?</h2>
      <p>Cada cifra se puede comprobar en las fuentes enlazadas, descargar en CSV desde la tabla o revisar en el código, en GitHub. Los ficheros originales están apuntados con su dirección de descarga, su fecha y su huella digital (sha256).</p>`;
    $("#m-cuerpo").dataset.listo = "1";
    $("#m-cuerpo").querySelectorAll(".indice a").forEach((el) => el.onclick = (ev) => { ev.preventDefault(); document.getElementById(el.getAttribute("href").slice(1)).scrollIntoView({ behavior: "smooth" }); });
  }

  // ---------- fuentes del pie (de las fichas de los indicadores) ----------
  {
    const vistas = new Set();
    const items = DATA.inds.flatMap((i) => i.fuentes).filter((f) => !vistas.has(f.url) && vistas.add(f.url)).map((f) => `<li><a href="${f.url}">${esc(f.nombre)}</a></li>`);
    items.push(`<li>Leyes: <a href="https://www.boe.es/">Boletín Oficial del Estado</a> (ficha de cada norma).</li>`);
    items.push(`<li>Mapa: Instituto Geográfico Nacional, vía <a href="https://github.com/martgnz/es-atlas">es-atlas</a> (CC BY 4.0).</li>`);
    $("#f-lista").innerHTML = items.join("");
  }

  // ---------- compartir ----------
  $("#compartir").onclick = async () => {
    const url = location.href;
    try {
      if (navigator.share) { await navigator.share({ title: document.title, url }); return; }
      await navigator.clipboard.writeText(url);
      $("#compartir").textContent = "Enlace copiado"; $("#compartido").textContent = "Enlace copiado";
      setTimeout(() => { $("#compartir").textContent = "Compartir"; }, 2000);
    } catch { /* cancelado */ }
  };

  // ---------- navegación ----------
  function selectorFoco() {
    const f = document.activeElement;
    if (!f || f === document.body) return null;
    if (f.id) return "#" + f.id;
    const caja = f.closest("[id]"); if (!caja) return null;
    for (const a of ["id", "v", "g", "v2", "q"]) if (f.dataset[a]) return `#${caja.id} [data-${a}="${f.dataset[a]}"]`;
    return null;
  }
  let anunciado = "";
  function render() {
    const foco = selectorFoco();
    hideTip();
    document.querySelectorAll(".nav a").forEach((el) => el.toggleAttribute("aria-current", false));
    const act = document.querySelector(`.nav a[data-vista="${S.vista}"]`); if (act) act.setAttribute("aria-current", "page");
    ["datos", "comunidad", "metodo"].forEach((v) => { $("#v-" + v).hidden = v !== S.vista; });
    if (S.vista === "datos") renderDatos();
    if (S.vista === "comunidad") renderComunidad();
    if (S.vista === "metodo") renderMetodo();
    if (foco) { try { const el = document.querySelector(foco); if (el && el !== document.activeElement) el.focus({ preventScroll: true }); } catch { /* selector no válido */ } }
    const t = S.vista === "datos" ? $("#p-titulo").textContent : S.vista === "comunidad" ? `Ficha de ${NOMBRE[S.com]}` : "Cómo leer los datos";
    if (t !== anunciado) { anunciado = t; $("#anuncio").textContent = t; }
  }
  function leerHash() {
    const [h, qs] = location.hash.replace("#", "").split("?");
    const m = h.match(/^comunidad-([a-z]{2})$/);
    if (m && NOMBRE[m[1].toUpperCase()]) {
      S.com = m[1].toUpperCase(); S.vista = "comunidad";
      const q = new URLSearchParams(qs || "");
      const vs = (q.get("vs") || "").toUpperCase(); S.vs = NOMBRE[vs] ? vs : "";
    } else if (h === "comunidad") S.vista = "comunidad";
    else if (h === "metodo") S.vista = "metodo";
    else if (h.startsWith("metodo-")) { S.vista = "metodo"; render(); const el = document.getElementById(h); if (el) el.scrollIntoView(); return; }
    else { S.vista = "datos"; if (qs) leerEnlace(qs); }
    pararPlay(); render(); window.scrollTo(0, 0);
  }
  addEventListener("hashchange", leerHash);
  let rz, anchoPrevio = innerWidth;
  addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { if (innerWidth !== anchoPrevio) { anchoPrevio = innerWidth; render(); } }, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  leerHash();
}
