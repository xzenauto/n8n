-- Casa Alpa / Vale v3 (2026-10-01): venta consultiva con precio al final.
-- Aplicado en Supabase como migraciones casa_alpa_vale_v3_ventas y casa_alpa_capacidad_por_variantes.

alter table public.casa_alpa_catalogo
  add column if not exists imagenes jsonb not null default '[]'::jsonb,   -- todas las fotos de Shopify (sync)
  add column if not exists descripcion_tienda text,                       -- descripción de la página del producto (sync)
  add column if not exists url_producto text;

-- Información del negocio editable; Vale la recibe junto con las FAQs del Google Doc
create table if not exists public.casa_alpa_info_negocio (
  id bigserial primary key,
  tema text not null unique,
  contenido text not null,
  activo boolean not null default true,
  orden int not null default 100,
  updated_at timestamptz not null default now()
);
alter table public.casa_alpa_info_negocio enable row level security;
insert into public.casa_alpa_info_negocio (tema, contenido, orden) values
  ('Meses sin intereses', 'Hasta 12 meses sin intereses pagando con tarjeta de crédito en el link de pago.', 10),
  ('Formas de pago', 'Se paga en línea en el link de pago de la tienda (casaalpa.mx): tarjeta de crédito o débito, y hasta 12 meses sin intereses con tarjeta de crédito.', 20),
  ('Envíos', 'Enviamos a toda la República Mexicana. El costo de envío se calcula automáticamente en el link de pago al capturar la dirección de entrega.', 30)
on conflict (tema) do update set contenido = excluded.contenido, updated_at = now();

-- Precios del catálogo = precio más bajo de sus variantes en Shopify (el sync lo mantiene)
update public.casa_alpa_catalogo c set precio = s.min_precio
from (select producto_id, min(precio) min_precio from public.casa_alpa_variantes group by producto_id) s
where s.producto_id = c.id;

-- Capacidad máxima considerando las opciones ("8 personas", "10 personas")
create or replace function public.casa_alpa_capacidad_max(p_producto_id uuid)
returns int language sql stable set search_path = public as $$
  select greatest(
    coalesce((select capacidad_personas from casa_alpa_catalogo where id = p_producto_id), 0),
    coalesce((select max((m[1])::int) from casa_alpa_variantes v, regexp_matches(coalesce(v.titulo, ''), '(\d+)\s*personas', 'gi') m
              where v.producto_id = p_producto_id and v.disponible), 0));
$$;

-- buscar_catalogo ya NO devuelve precios (sólo opciones, medidas, materiales, descripción, fotos disponibles
-- y si entra o no en el presupuesto). La definición completa vigente se puede ver con:
--   select pg_get_functiondef('public.casa_alpa_buscar_catalogo(text,numeric,integer,text,text,integer)'::regprocedure);

-- Cotización con precios por opción: sólo cuando el cliente ya eligió producto
create or replace function public.casa_alpa_cotizar_producto(p_producto_id uuid)
returns jsonb language sql stable set search_path = public as $$
  select coalesce((
    select jsonb_build_object(
      'producto_id', c.id, 'nombre', c.nombre,
      'opciones', coalesce((select jsonb_agg(jsonb_build_object('variante_id', v.shopify_variant_id, 'opcion', coalesce(v.titulo, 'única'),
                                    'precio', v.precio, 'precio_antes', v.precio_antes) order by v.precio)
                            from casa_alpa_variantes v where v.producto_id = c.id and v.disponible), '[]'::jsonb),
      'pago', (select string_agg(contenido, ' ') from casa_alpa_info_negocio where activo and tema in ('Meses sin intereses','Envíos')),
      'nota', 'Precios en pesos mexicanos, tal como los cobra la tienda. Si precio_antes viene, es el precio anterior (rebajado).')
    from casa_alpa_catalogo c where c.id = p_producto_id and c.activo
  ), jsonb_build_object('error', 'Producto no encontrado o inactivo. Usa producto_id de buscar_catalogo.'));
$$;

revoke all on function public.casa_alpa_cotizar_producto(uuid) from public, anon, authenticated;
revoke all on function public.casa_alpa_capacidad_max(uuid) from public, anon, authenticated;
grant execute on function public.casa_alpa_cotizar_producto(uuid) to service_role;
grant execute on function public.casa_alpa_capacidad_max(uuid) to service_role;

alter table public.casa_alpa_prospectos drop constraint if exists casa_alpa_prospectos_etapa_check;
alter table public.casa_alpa_prospectos add constraint casa_alpa_prospectos_etapa_check
  check (etapa = any (array['explorando','interesado','eligiendo','cotizado','cotizacion_solicitada','listo_comprar','link_enviado','handoff','compro']));
