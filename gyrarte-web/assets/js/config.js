/* =========================================================
   GYRARTE — configuración del sitio
   Los conciertos YA NO se editan aquí: se dan de alta en
   el panel de administración (/admin) y se guardan en Supabase.
   ========================================================= */
window.GYRARTE = {
  // Supabase (proyecto XzenAuto). La clave "publishable" es pública por diseño:
  // la seguridad la ponen las reglas RLS de la base de datos.
  supabaseUrl: "https://fllhjemdhohsewqwzrpc.supabase.co",
  supabaseKey: "sb_publishable_35vEokZExHYOBDuqpSmudA_jVa_Caxo",

  // Webhooks de n8n. Vacíos = la compra y los formularios se van por WhatsApp.
  checkoutUrl: "" /* pendiente n8n: "https://n8n.srv964593.hstgr.cloud/webhook/gyrarte-checkout" */,
  contactoUrl: "" /* pendiente n8n: "https://n8n.srv964593.hstgr.cloud/webhook/gyrarte-contacto" */,

  defaultWa: "524438438164",
  maxPorCompra: 10,
  moneda: "MXN",
  zonaHoraria: "America/Mexico_City",
};
