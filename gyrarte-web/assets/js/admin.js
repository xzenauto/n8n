/* GYRARTE — panel de administración */
(function () {
  "use strict";
  const C = window.GYRARTE;
  const sb = window.supabase.createClient(C.supabaseUrl, C.supabaseKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  const $ = (s) => document.querySelector(s);
  const money = new Intl.NumberFormat("es-MX", { style: "currency", currency: C.moneda });
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ESTADOS = { venta: "Venta online", whatsapp: "WhatsApp", proximamente: "Próximamente", agotado: "Agotado" };
  let eventos = [];

  function vista(id) {
    ["vLogin", "vPanel", "vNoAdmin", "vNewPass"].forEach((v) => ($("#" + v).hidden = v !== id));
  }
  function toast(t) {
    const el = $("#toast"); el.textContent = t; el.style.display = "block";
    clearTimeout(toast._t); toast._t = setTimeout(() => (el.style.display = "none"), 2800);
  }
  function slug(s) {
    return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
  }
  function fechaCorta(ymd) {
    const [y, m, d] = ymd.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
  }

  /* ---------- Sesión ---------- */
  async function arrancar(session) {
    if (!session) return vista("vLogin");
    const { data, error } = await sb.from("gyrarte_admins").select("user_id").eq("user_id", session.user.id).maybeSingle();
    if (error || !data) return vista("vNoAdmin");
    $("#who").textContent = session.user.email;
    vista("vPanel");
    cargarEventos();
  }

  sb.auth.onAuthStateChange((evento, session) => {
    if (evento === "PASSWORD_RECOVERY") return vista("vNewPass");
    if (evento === "SIGNED_OUT") return vista("vLogin");
  });
  sb.auth.getSession().then(({ data }) => {
    if (location.hash.includes("type=recovery")) return; // lo maneja PASSWORD_RECOVERY
    arrancar(data.session);
  });

  $("#fLogin").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, err = f.querySelector(".form-error"), btn = f.querySelector("button[type=submit]");
    btn.disabled = true; err.textContent = "";
    const { data, error } = await sb.auth.signInWithPassword({ email: f.email.value.trim(), password: f.password.value });
    btn.disabled = false;
    if (error) { err.textContent = "Correo o contraseña incorrectos."; return; }
    f.reset();
    arrancar(data.session);
  });

  $("#bReset").addEventListener("click", async () => {
    const email = $("#l-email").value.trim();
    const err = $("#fLogin .form-error");
    if (!email) { err.textContent = "Escribe tu correo arriba y vuelve a pulsar."; return; }
    await sb.auth.resetPasswordForEmail(email, { redirectTo: location.origin + "/admin/" });
    err.textContent = "";
    toast("Si el correo existe, te llegó un enlace para cambiar la contraseña.");
  });

  $("#fNewPass").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, err = f.querySelector(".form-error");
    const { error } = await sb.auth.updateUser({ password: f.password.value });
    if (error) { err.textContent = error.message; return; }
    history.replaceState(null, "", location.pathname);
    toast("Contraseña actualizada");
    const { data } = await sb.auth.getSession();
    arrancar(data.session);
  });

  const salir = async () => { await sb.auth.signOut(); vista("vLogin"); };
  $("#bLogout").addEventListener("click", salir);
  $("#bLogout2").addEventListener("click", salir);

  /* ---------- Pestañas ---------- */
  function tab(id) {
    document.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === id)));
    ["tEventos", "tNuevo", "tVentas"].forEach((t) => ($("#" + t).hidden = t !== id));
    if (id === "tVentas") cargarVentas();
  }
  document.querySelectorAll("[data-tab]").forEach((b) =>
    b.addEventListener("click", () => { if (b.dataset.tab === "tNuevo") limpiarForm(); tab(b.dataset.tab); })
  );

  /* ---------- Conciertos ---------- */
  async function cargarEventos() {
    const { data, error } = await sb.from("gyrarte_eventos").select("*").order("fecha", { ascending: false });
    const tb = $("#lista");
    if (error) { tb.innerHTML = `<tr><td colspan="6">Error: ${esc(error.message)}</td></tr>`; return; }
    eventos = data;
    if (!data.length) { tb.innerHTML = `<tr><td colspan="6">Aún no hay conciertos. Usa “+ Nuevo concierto”.</td></tr>`; return; }
    const hoy = new Date().toISOString().slice(0, 10);
    tb.innerHTML = data.map((ev) => `
      <tr style="${ev.fecha < hoy ? "opacity:.55" : ""}">
        <td>${fechaCorta(ev.fecha)}${ev.hora ? "<br><small>" + esc(ev.hora) + "</small>" : ""}</td>
        <td><strong>${esc(ev.artista)}</strong><br><small style="color:var(--muted)">${esc(ev.titulo)}</small></td>
        <td>${esc(ev.ciudad)}<br><small style="color:var(--muted)">${esc(ev.lugar)}</small></td>
        <td>${Number(ev.precio) > 0 ? money.format(ev.precio) : "—"}</td>
        <td><span class="tag tag--${ev.estado}">${ESTADOS[ev.estado]}</span>${ev.publicado ? "" : ' <span class="tag tag--oculto">Oculto</span>'}</td>
        <td><div class="row-actions">
          <button class="btn btn--dark sm" data-editar="${esc(ev.id)}">Editar</button>
          <button class="btn btn--ghost sm" data-publicar="${esc(ev.id)}">${ev.publicado ? "Ocultar" : "Publicar"}</button>
          <button class="btn btn--ghost sm" data-borrar="${esc(ev.id)}" style="border-color:rgba(255,80,80,.6)">Borrar</button>
        </div></td>
      </tr>`).join("");
  }

  $("#lista").addEventListener("click", async (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.editar) {
      const ev = eventos.find((x) => x.id === b.dataset.editar);
      llenarForm(ev); tab("tNuevo");
    } else if (b.dataset.publicar) {
      const ev = eventos.find((x) => x.id === b.dataset.publicar);
      const { error } = await sb.from("gyrarte_eventos").update({ publicado: !ev.publicado }).eq("id", ev.id);
      if (error) return toast("Error: " + error.message);
      toast(ev.publicado ? "Concierto oculto" : "Concierto publicado"); cargarEventos();
    } else if (b.dataset.borrar) {
      const ev = eventos.find((x) => x.id === b.dataset.borrar);
      if (!confirm(`¿Borrar "${ev.artista}" del ${fechaCorta(ev.fecha)}?\nSi ya tiene ventas, mejor ocúltalo.`)) return;
      const { error } = await sb.from("gyrarte_eventos").delete().eq("id", ev.id);
      if (error) return toast("Error: " + error.message);
      toast("Concierto borrado"); cargarEventos();
    }
  });

  const form = $("#fEvento");
  function limpiarForm() {
    form.reset(); form.id.value = "";
    $("#formTitulo").textContent = "Nuevo concierto";
    $("#tabNuevo").textContent = "+ Nuevo concierto";
    form.querySelector(".form-error").textContent = "";
  }
  function llenarForm(ev) {
    limpiarForm();
    ["id", "artista", "titulo", "fecha", "hora", "tipo", "ciudad", "lugar", "estado", "precio", "cupo", "wa_number", "buy_url"]
      .forEach((k) => (form[k].value = ev[k] ?? ""));
    form.precio.value = Number(ev.precio);
    form.publicado.checked = ev.publicado;
    $("#formTitulo").textContent = "Editar concierto";
    $("#tabNuevo").textContent = "Editando…";
  }
  $("#bCancelar").addEventListener("click", () => { limpiarForm(); tab("tEventos"); });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const err = form.querySelector(".form-error"), btn = form.querySelector("button[type=submit]");
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const precio = Number(form.precio.value || 0);
    if (form.estado.value === "venta" && precio <= 0 && !form.buy_url.value) {
      err.textContent = "Para venta online pon un precio mayor a 0."; return;
    }
    const reg = {
      artista: form.artista.value.trim(),
      titulo: form.titulo.value.trim() || "En vivo",
      fecha: form.fecha.value,
      hora: form.hora.value || null,
      tipo: form.tipo.value,
      ciudad: form.ciudad.value.trim(),
      lugar: form.lugar.value.trim(),
      estado: form.estado.value,
      precio,
      cupo: form.cupo.value === "" ? null : Number(form.cupo.value),
      wa_number: form.wa_number.value.replace(/\D/g, "") || null,
      buy_url: form.buy_url.value.trim() || null,
      publicado: form.publicado.checked,
    };
    btn.disabled = true; err.textContent = "";
    let res;
    if (form.id.value) {
      res = await sb.from("gyrarte_eventos").update(reg).eq("id", form.id.value);
    } else {
      reg.id = `${slug(reg.artista)}-${slug(reg.ciudad)}-${reg.fecha}`;
      res = await sb.from("gyrarte_eventos").insert(reg);
      if (res.error && res.error.code === "23505") { // id repetido (mismo artista/ciudad/fecha)
        reg.id += "-" + Math.random().toString(36).slice(2, 6);
        res = await sb.from("gyrarte_eventos").insert(reg);
      }
    }
    btn.disabled = false;
    if (res.error) { err.textContent = "No se pudo guardar: " + res.error.message; return; }
    toast(form.id.value ? "Cambios guardados" : "¡Concierto publicado!");
    limpiarForm(); tab("tEventos"); cargarEventos();
  });

  /* ---------- Ventas ---------- */
  async function cargarVentas() {
    const tb = $("#ventas");
    const { data, error } = await sb.from("gyrarte_ventas").select("*").order("created_at", { ascending: false }).limit(500);
    if (error) { tb.innerHTML = `<tr><td colspan="6">Error: ${esc(error.message)}</td></tr>`; return; }
    const ok = data.filter((v) => v.estado === "approved");
    $("#sBoletos").textContent = ok.reduce((a, v) => a + v.cantidad, 0);
    $("#sMonto").textContent = money.format(ok.reduce((a, v) => a + Number(v.monto), 0));
    $("#sCompras").textContent = ok.length;
    if (!data.length) { tb.innerHTML = `<tr><td colspan="6">Todavía no hay ventas.</td></tr>`; return; }
    const nombreEv = (id) => { const ev = eventos.find((x) => x.id === id); return ev ? `${ev.artista} · ${ev.ciudad} · ${fechaCorta(ev.fecha)}` : id || "—"; };
    const est = { approved: "Aprobado", pending: "Pendiente", in_process: "En proceso", rejected: "Rechazado", refunded: "Reembolsado", cancelled: "Cancelado" };
    tb.innerHTML = data.map((v) => `
      <tr>
        <td>${new Date(v.created_at).toLocaleString("es-MX", { dateStyle: "short", timeStyle: "short" })}</td>
        <td>${esc(nombreEv(v.evento_id))}</td>
        <td>${esc(v.comprador_nombre)}<br><small style="color:var(--muted)">${esc(v.comprador_email)} ${esc(v.comprador_tel)}</small></td>
        <td>${v.cantidad}</td>
        <td>${money.format(v.monto)}</td>
        <td><span class="tag">${esc(est[v.estado] || v.estado)}</span></td>
      </tr>`).join("");
  }
})();
