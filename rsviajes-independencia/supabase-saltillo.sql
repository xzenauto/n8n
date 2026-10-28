-- RS Viajes Saltillo: tablas copiadas de Hijar (memoria, buffer, promos), vista de promos vigentes y funciones del buffer.
-- RS_sync_promos también reconoce la agencia 'saltillo' (→ RSSaltillo_promos).
create table public."RS-Saltillo" (like public."RS-Hijar" including all);
create table public."RSSaltillo_buffer" (like public."RSHijar_buffer" including all);
create table public."RSSaltillo_promos" (like public."RSHijar_promos" including all);
alter table public."RS-Saltillo" enable row level security;
alter table public."RSSaltillo_buffer" enable row level security;
alter table public."RSSaltillo_promos" enable row level security;
create trigger "RSSaltillo_promos_updated_at" before update on public."RSSaltillo_promos" for each row execute function "RSIndependencia_touch_updated_at"();
-- Vista RSSaltillo_promos_vigentes y funciones RSSaltillo_buffer_add / RSSaltillo_buffer_take: iguales a las de Hijar cambiando el nombre de la tabla.
