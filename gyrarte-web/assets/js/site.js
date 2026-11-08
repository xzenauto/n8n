/* GYRARTE — lógica pública del sitio */
(function () {
  "use strict";
  const C = window.GYRARTE;
  const MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];
  const mesesLargo = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: C.moneda });

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---------- Menú móvil ---------- */
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  /* ---------- Fechas ---------- */
  function hoyMx() {
    // fecha de hoy (AAAA-MM-DD) en la zona horaria de México
    return new Intl.DateTimeFormat("en-CA", { timeZone: C.zonaHoraria }).format(new Date());
  }
  function partes(ymd) {
    const [y, m, d] = ymd.split("-").map(Number);
    return { y, m: m - 1, d };
  }

  /* ---------- Cargar conciertos desde Supabase ---------- */
  async function cargarEventos() {
    const url = `${C.supabaseUrl}/rest/v1/gyrarte_eventos?select=*&publicado=eq.true&order=fecha.asc,hora.asc.nullslast`;
    const r = await fetch(url, { headers: { apikey: C.supabaseKey, Authorization: `Bearer ${C.supabaseKey}` } });
    if (!r.ok) throw new Error("No se pudieron cargar los conciertos");
    return r.json();
  }

  function waLink(ev) {
    const n = String(ev.wa_number || C.defaultWa).replace(/\D/g, "");
    const { d, m } = partes(ev.fecha);
    const txt = `Hola, quiero informes para esta fecha:\n${ev.artista}\n* Fecha: ${d} de ${mesesLargo[m]}\n* Ciudad: ${ev.ciudad}\n* Lugar: ${ev.lugar}`;
    return `https://wa.me/${n}?text=${encodeURIComponent(txt)}`;
  }

  function accion(ev, pasado) {
    if (pasado) return `<span class="gy-pill gy-pill--past">Finalizado</span>`;
    if (ev.estado === "agotado") return `<span class="gy-pill gy-pill--sold">Sold out</span>`;
    if (ev.estado === "proximamente") return `<span class="gy-pill gy-pill--soon">Boletos próximamente</span>`;
    if (ev.estado === "venta" && ev.buy_url) {
      return `<a class="btn btn--accent" href="${esc(ev.buy_url)}" target="_blank" rel="noopener">Comprar boletos</a>`;
    }
    if (ev.estado === "venta" && Number(ev.precio) > 0 && C.checkoutUrl) {
      return `<button class="btn btn--accent" type="button" data-comprar="${esc(ev.id)}">Comprar boletos</button>
              <div class="gy-note">Pago seguro con Mercado Pago</div>`;
    }
    return `<a class="btn btn--wa" href="${waLink(ev)}" target="_blank" rel="noopener">WhatsApp informes</a>
            <div class="gy-note">Reserva por WhatsApp</div>`;
  }

  function tarjeta(ev, pasado) {
    const { d, m } = partes(ev.fecha);
    const precio = ev.estado === "venta" && Number(ev.precio) > 0 && !pasado
      ? `<span class="gy-badge gy-badge--precio">${money.format(ev.precio)}</span>` : "";
    const tipo = ev.tipo.charAt(0).toUpperCase() + ev.tipo.slice(1);
    return `
      <article class="gy-event${pasado ? " is-past" : ""}">
        <div class="gy-date"><div class="day">${d}</div><div class="mon">${MESES[m]}</div></div>
        <div class="gy-info">
          <p class="name">${esc(ev.artista)} — ${esc(ev.titulo)}</p>
          <p class="meta">${esc(ev.ciudad)} · ${esc(ev.lugar)}${ev.hora ? " · " + esc(ev.hora) + " h" : ""}</p>
          <div class="gy-badges"><span class="gy-badge gy-badge--${esc(ev.tipo)}">${tipo}</span>${precio}</div>
        </div>
        <div class="gy-buy">${accion(ev, pasado)}</div>
      </article>`;
  }

  let EVENTOS = [];
  async function pintarEventos() {
    const cont = document.getElementById("gyEvents");
    if (!cont) return;
    const limite = Number(cont.dataset.limite || 0);
    const mostrarPasados = cont.dataset.pasados === "si";
    cont.innerHTML = `<div class="gy-empty">Cargando conciertos…</div>`;
    try {
      EVENTOS = await cargarEventos();
    } catch (e) {
      cont.innerHTML = `<div class="gy-empty">No pudimos cargar los conciertos. Escríbenos por <a href="https://wa.me/${C.defaultWa}">WhatsApp</a>.</div>`;
      return;
    }
    const hoy = hoyMx();
    let proximos = EVENTOS.filter((e) => e.fecha >= hoy);
    const pasados = EVENTOS.filter((e) => e.fecha < hoy).reverse();
    if (limite) proximos = proximos.slice(0, limite);

    let html = proximos.length
      ? proximos.map((e) => tarjeta(e, false)).join("")
      : `<div class="gy-empty">Muy pronto anunciaremos nuevas fechas. Síguenos en <a href="https://www.instagram.com/gyrarte/" target="_blank" rel="noopener">Instagram</a> para enterarte primero.</div>`;
    if (mostrarPasados && pasados.length) {
      html += `<h3 class="gy-past-title">Fechas pasadas</h3>` + pasados.slice(0, 8).map((e) => tarjeta(e, true)).join("");
    }
    cont.innerHTML = html;
  }

  /* ---------- Modal de compra ---------- */
  const modal = document.getElementById("buyModal");
  let evActual = null, cantidad = 1;

  function actualizarTotal() {
    modal.querySelector("output[name=qty]").value = cantidad;
    modal.querySelector("[data-total]").textContent = money.format(cantidad * Number(evActual.precio));
  }
  function abrir(ev) {
    evActual = ev; cantidad = 1;
    const { d, m } = partes(ev.fecha);
    modal.querySelector("[data-titulo]").textContent = `${ev.artista} — ${ev.titulo}`;
    modal.querySelector("[data-detalle]").textContent = `${d} de ${mesesLargo[m]} · ${ev.ciudad} · ${ev.lugar}`;
    modal.querySelector("[data-unit]").textContent = `${money.format(ev.precio)} por boleto`;
    modal.querySelector(".form-error").textContent = "";
    actualizarTotal();
    modal.classList.add("open");
    modal.querySelector("input[name=nombre]").focus();
  }
  function cerrar() { modal.classList.remove("open"); }

  if (modal) {
    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-comprar]");
      if (b) { const ev = EVENTOS.find((x) => x.id === b.dataset.comprar); if (ev) abrir(ev); }
    });
    modal.addEventListener("click", (e) => { if (e.target === modal || e.target.closest(".modal-close")) cerrar(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });
    modal.querySelector("[data-menos]").addEventListener("click", () => { if (cantidad > 1) { cantidad--; actualizarTotal(); } });
    modal.querySelector("[data-mas]").addEventListener("click", () => { if (cantidad < C.maxPorCompra) { cantidad++; actualizarTotal(); } });

    modal.querySelector("form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target, err = f.querySelector(".form-error"), btn = f.querySelector("button[type=submit]");
      const datos = Object.fromEntries(new FormData(f));
      if (!f.checkValidity()) { f.reportValidity(); return; }
      btn.disabled = true; btn.textContent = "Conectando con Mercado Pago…"; err.textContent = "";
      try {
        const r = await fetch(C.checkoutUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ eventoId: evActual.id, cantidad, nombre: datos.nombre, email: datos.email, telefono: datos.telefono }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok || !j.url) throw new Error(j.error || "No se pudo iniciar el pago");
        window.location.href = j.url;
      } catch (ex) {
        err.textContent = ex.message + ". Inténtalo de nuevo o escríbenos por WhatsApp.";
        btn.disabled = false; btn.textContent = "Pagar con Mercado Pago";
      }
    });
  }

  /* ---------- Formularios de contacto / newsletter ---------- */
  document.querySelectorAll("form[data-lead]").forEach((f) => {
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = f.querySelector("button[type=submit]"), msg = f.querySelector("[data-msg]");
      const datos = Object.fromEntries(new FormData(f));
      if (datos.website) return; // trampa anti-spam
      if (!C.contactoUrl) { // sin n8n: enviamos el mensaje por WhatsApp
        const txt = f.dataset.lead === "newsletter"
          ? `Hola, quiero recibir novedades de Gyrarte.\nNombre: ${datos.nombre || ""}\nCorreo: ${datos.email || ""}`
          : `Hola, les escribo desde gyrarte.com\nNombre: ${datos.nombre || ""}\nCorreo: ${datos.email || ""}\nTeléfono: ${datos.telefono || ""}\n\n${datos.mensaje || ""}`;
        window.open(`https://wa.me/${C.defaultWa}?text=${encodeURIComponent(txt)}`, "_blank", "noopener");
        msg.className = "form-ok"; msg.textContent = "Te abrimos WhatsApp para enviar tu mensaje.";
        return;
      }
      btn.disabled = true;
      try {
        const r = await fetch(C.contactoUrl, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...datos, origen: f.dataset.lead, pagina: location.pathname }),
        });
        if (!r.ok) throw new Error();
        f.reset();
        msg.className = "form-ok"; msg.textContent = "¡Gracias! Recibimos tus datos.";
      } catch {
        msg.className = "form-error"; msg.textContent = "No se pudo enviar. Escríbenos a gyrarte@gmail.com";
      }
      btn.disabled = false;
    });
  });

  pintarEventos();
})();
