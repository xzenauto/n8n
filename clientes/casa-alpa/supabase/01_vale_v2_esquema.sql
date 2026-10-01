-- Casa Alpa / Vale v2 — esquema aplicado en Supabase (proyecto fllhjemdhohsewqwzrpc) el 2026-10-01.
-- Las funciones vigentes están en 02_funciones.sql.

alter table public.casa_alpa_catalogo
  add column if not exists shopify_product_id bigint,
  add column if not exists shopify_handle text;

alter table public.casa_alpa_prospectos
  add column if not exists canal text,
  add column if not exists ad_id text,
  add column if not exists opportunity_id text;

-- Variantes de Shopify (tamaño/color con su propio precio y variant_id). Las llena el workflow "Casa Alpa - Sync variantes Shopify".
create table if not exists public.casa_alpa_variantes (
  id bigserial primary key,
  producto_id uuid not null references public.casa_alpa_catalogo(id) on delete cascade,
  shopify_variant_id bigint not null unique,
  titulo text,
  precio numeric,
  precio_antes numeric,
  disponible boolean not null default true,
  updated_at timestamptz not null default now()
);
create index if not exists casa_alpa_variantes_producto_idx on public.casa_alpa_variantes(producto_id);

-- Historial de conversación persistente + buffer anti-ráfaga
create table if not exists public.casa_alpa_mensajes (
  id bigserial primary key,
  contact_id text not null,
  rol text not null check (rol in ('cliente','vale')),
  contenido text not null,
  procesado boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists casa_alpa_mensajes_contact_idx on public.casa_alpa_mensajes(contact_id, id);

-- Links de pago enviados por Vale
create table if not exists public.casa_alpa_links_pago (
  id uuid primary key default gen_random_uuid(),
  contact_id text not null,
  opportunity_id text,
  items jsonb not null,
  total numeric not null,
  url text not null,
  estado text not null default 'enviado' check (estado in ('enviado','pagado','cancelado')),
  recordatorio_enviado boolean not null default false,
  shopify_order_id text,
  shopify_order_name text,
  created_at timestamptz not null default now(),
  pagado_at timestamptz
);
create index if not exists casa_alpa_links_contact_idx on public.casa_alpa_links_pago(contact_id, created_at desc);

-- RLS: sólo la secret key (n8n) accede
alter table public.casa_alpa_variantes enable row level security;
alter table public.casa_alpa_mensajes enable row level security;
alter table public.casa_alpa_links_pago enable row level security;
-- La política de prospectos estaba abierta a cualquiera con la publishable key
drop policy if exists "service role full access prospectos" on public.casa_alpa_prospectos;
