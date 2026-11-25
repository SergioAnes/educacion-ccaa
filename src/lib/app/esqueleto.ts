// Estructura HTML fija de la página; las vistas se rellenan desde ui.ts.
// Es contenido propio (sin datos de usuario), así que se inserta tal cual.
export const ESQUELETO = `<div class="wrap">
  <noscript><p class="aviso">Esta web necesita JavaScript para mostrar los mapas y gráficos.</p></noscript>
  <header class="top">
    <div class="brand">
      <div class="brand-linea">
        <span>Educación por comunidades</span>
        <a class="contacto-x" href="https://x.com/SergioA_Galan" target="_blank" rel="noopener noreferrer" aria-label="Contacto en X con @SergioA_Galan (abre en otra pestaña)">Contacto en X<span class="solo-escritorio"> · @SergioA_Galan</span></a>
      </div>
      <small>Datos oficiales del sistema educativo de las 17 comunidades, con Ceuta y Melilla aparte</small>
    </div>
    <div class="top-der">
      <nav class="nav" aria-label="Secciones">
        <a href="#datos" data-vista="datos">Datos</a>
        <a href="#comunidad" data-vista="comunidad">Tu comunidad</a>
        <a href="#metodo" data-vista="metodo">Cómo leer los datos</a>
      </nav>
      <button type="button" class="btn sm compartir" id="compartir">Compartir</button>
    </div>
  </header>
  <p class="sr" aria-live="polite" id="compartido"></p>

  <section id="v-datos" hidden>
    <div class="intro">
      <div class="intro-cab">
        <div>
          <h1>¿Cómo está la educación en tu comunidad?</h1>
          <p id="p-intro"></p>
        </div>
      </div>
      <div class="selector" id="sel-datos"></div>
    </div>
    <div class="portada-grid">
      <div class="panel">
        <h2 id="p-titulo"></h2>
        <p class="sub" id="p-sub"></p>
        <div class="origen" id="p-origen"></div>
        <div class="tilemap" id="p-mapa"></div>
        <div class="leyenda" id="p-leyenda"></div>
        <div class="tiempo"><div class="anios" id="p-anios"></div></div>
        <div class="descargas" id="p-desc"></div>
      </div>
      <div class="insights" id="p-insights"></div>
    </div>
    <div class="panel detalle">
      <div class="fila">
        <div class="seg" id="e-vistas" role="group" aria-label="Tipo de gráfico">
          <button type="button" data-v="ranking">De más a menos</button>
          <button type="button" data-v="evolucion">Evolución</button>
          <button type="button" data-v="tabla">Tabla</button>
        </div>
        <div class="selec" id="e-selec"></div>
      </div>
      <h2 id="e-titulo"></h2>
      <p class="sub" id="e-sub"></p>
      <div class="fila" id="e-opciones"></div>
      <div class="chart" id="e-chart"></div>
      <div class="descargas" id="e-desc"></div>
      <div class="nota" id="e-nota"></div>
    </div>
    <div class="panel que-mide" id="d-mide"></div>
    <p class="siguiente"><a href="#comunidad">Siguiente: Tu comunidad →</a></p>
  </section>

  <section id="v-comunidad" hidden>
    <div class="ficha-cab">
      <div>
        <label for="c-sel" class="ayuda">Elige tu comunidad</label><br>
        <select id="c-sel"></select>
        <h1 id="c-nombre" style="margin-top:12px"></h1>
        <p class="resumen" id="c-resumen"></p>
        <div class="comparar"><label for="c-vs">Comparar con</label><select id="c-vs"></select><span class="leyenda-vs" id="c-leyenda-vs"></span></div>
      </div>
      <div>
        <p class="ayuda">O púlsala en el mapa</p>
        <div class="tilemap" id="c-mapa"></div>
      </div>
    </div>
    <div id="c-bloques"></div>
    <p class="siguiente"><a href="#metodo">Siguiente: Cómo leer los datos →</a></p>
  </section>

  <section id="v-metodo" hidden>
    <div class="metodo" id="m-cuerpo"></div>
    <p class="siguiente"><a href="#datos">Siguiente: volver a los datos →</a></p>
  </section>

  <footer class="pie-fuentes">
    <h2>Fuentes</h2>
    <ul id="f-lista"></ul>
    <p>España es siempre el dato oficial del conjunto del país, no la media de las comunidades. Más detalles en <a href="#metodo">Cómo leer los datos</a>.
    Código y datos: <a href="https://github.com/SergioAnes/educacion-ccaa">GitHub</a>. Proyecto hermano de <a href="https://sanidad-ccaa.vercel.app/">Sanidad por comunidades</a> y <a href="https://presupuestos-ccaa.vercel.app/">Presupuestos por comunidades</a>.
    Contamos las visitas de forma anónima y sin cookies (Vercel Web Analytics).</p>
  </footer>
</div>
<div class="tip" id="tip" hidden></div>
<p class="sr" aria-live="polite" id="anuncio"></p>`;
