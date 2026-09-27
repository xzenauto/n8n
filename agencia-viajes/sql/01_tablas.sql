-- Agencia de viajes (Lucía) – tablas en Supabase (proyecto XzenAuto)
-- Estado final consolidado de las migraciones aplicadas.

create table if not exists public.viajes_promos (
  id                 text primary key,              -- id_promo del Sheet
  activa             boolean not null default true,
  destino            text not null,
  hotel              text,
  titulo             text not null,
  vigencia_desde     date,                          -- cuándo se puede vender
  vigencia_hasta     date,
  viaje_desde        date,                          -- fechas de estancia válidas
  viaje_hasta        date,
  noches             int,
  plan               text,
  dias_aplica        text,
  precio_desde       numeric(12,2),                 -- MXN
  precio_detalle     text,
  precios_menores    text,
  incluye            text,
  condiciones        text,
  descripcion        text,
  imagen_url         text,
  ad_ids             text[] not null default '{}',
  actualizado_en     timestamptz not null default now()
);
create index if not exists viajes_promos_ad_ids_idx on public.viajes_promos using gin (ad_ids);
create index if not exists viajes_promos_destino_idx on public.viajes_promos (lower(destino));

create table if not exists public.viajes_contactos (
  ghl_contact_id          text primary key,
  nombre                  text,
  telefono                text,
  canal                   text,
  seguimiento_pausado     boolean not null default false,
  ultimo_msg_cliente_en   timestamptz,
  ultimo_msg_ia_en        timestamptz,
  ultimo_procesado_en     timestamptz,
  ghl_conversation_id     text,
  resumen_historial       text,
  creado_en               timestamptz not null default now(),
  actualizado_en          timestamptz not null default now()
);

create table if not exists public.viajes_leads (
  id                   uuid primary key default gen_random_uuid(),
  ghl_contact_id       text not null references public.viajes_contactos(ghl_contact_id) on delete cascade,
  ghl_opportunity_id   text,
  canal                text,
  ad_id                text,
  promo_id             text references public.viajes_promos(id) on delete set null,
  destino              text,
  fecha_salida         date,
  fecha_regreso        date,
  fechas_texto         text,
  fechas_sin_definir   boolean not null default false,
  adultos              int,
  ninos                int,
  edades_ninos         int[],
  datos_completos      boolean not null default false,
  urgente              boolean not null default false,
  etapa                text not null default 'nuevo',
  resumen_ia           text,
  completado_en        timestamptz,
  cerrado              boolean not null default false,
  creado_en            timestamptz not null default now(),
  actualizado_en       timestamptz not null default now()
);
create index if not exists viajes_leads_contact_idx on public.viajes_leads (ghl_contact_id, cerrado);
create unique index if not exists viajes_leads_opp_uidx on public.viajes_leads (ghl_opportunity_id);

create table if not exists public.viajes_seguimientos (
  id                 uuid primary key default gen_random_uuid(),
  ghl_contact_id     text not null references public.viajes_contactos(ghl_contact_id) on delete cascade,
  lead_id            uuid references public.viajes_leads(id) on delete cascade,
  tipo               text not null check (tipo in ('datos','cotizacion')),
  numero             int not null,                 -- 1..4 (99 = cierre por falta de respuesta)
  serie              text,
  programado_para    timestamptz not null,
  estado             text not null default 'pendiente'
                     check (estado in ('pendiente','procesando','enviado','cancelado','fallido','manual')),
  mensaje            text,
  enviado_en         timestamptz,
  error              text,
  creado_en          timestamptz not null default now()
);
create index if not exists viajes_seg_pend_idx on public.viajes_seguimientos (estado, programado_para);
create unique index if not exists viajes_seg_serie_uidx on public.viajes_seguimientos (lead_id, tipo, serie, numero);

create table if not exists public.viajes_recordatorios (
  id                 uuid primary key default gen_random_uuid(),
  ghl_contact_id     text not null references public.viajes_contactos(ghl_contact_id) on delete cascade,
  lead_id            uuid references public.viajes_leads(id) on delete cascade,
  tipo               text not null check (tipo in ('pago','viaje')),
  referencia         text,
  fecha_evento       timestamptz not null,
  programado_para    timestamptz not null,
  estado             text not null default 'pendiente'
                     check (estado in ('pendiente','procesando','enviado','cancelado','fallido','manual')),
  mensaje            text,
  enviado_en         timestamptz,
  error              text,
  creado_en          timestamptz not null default now(),
  unique (ghl_contact_id, tipo, referencia, fecha_evento)
);
create index if not exists viajes_rec_pend_idx on public.viajes_recordatorios (estado, programado_para);

create table if not exists public.viajes_eventos_log (
  id               bigserial primary key,
  ghl_contact_id   text,
  tipo             text not null,
  detalle          jsonb,
  creado_en        timestamptz not null default now()
);

create or replace view public.viajes_promos_vigentes
with (security_invoker = true) as
select * from public.viajes_promos p
where p.activa
  and (p.vigencia_hasta is null or p.vigencia_hasta >= (now() at time zone 'America/Mexico_City')::date)
  and (p.vigencia_desde is null or p.vigencia_desde <= (now() at time zone 'America/Mexico_City')::date)
  and (p.viaje_hasta   is null or p.viaje_hasta   >= (now() at time zone 'America/Mexico_City')::date);

-- RLS activo sin políticas: solo el backend (service_role desde n8n) accede.
alter table public.viajes_promos        enable row level security;
alter table public.viajes_contactos     enable row level security;
alter table public.viajes_leads         enable row level security;
alter table public.viajes_seguimientos  enable row level security;
alter table public.viajes_recordatorios enable row level security;
alter table public.viajes_eventos_log   enable row level security;
