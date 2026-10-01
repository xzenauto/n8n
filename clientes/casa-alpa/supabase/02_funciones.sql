-- Casa Alpa / Vale v2 — funciones RPC vigentes (sólo service_role puede ejecutarlas).

CREATE OR REPLACE FUNCTION public.casa_alpa_buscar_catalogo(p_categoria text DEFAULT NULL::text, p_presupuesto_max numeric DEFAULT NULL::numeric, p_personas integer DEFAULT NULL::integer, p_color text DEFAULT NULL::text, p_texto text DEFAULT NULL::text, p_limite integer DEFAULT 4)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'public'
AS $function$
declare
  v_cat text := nullif(translate(lower(trim(coalesce(p_categoria,''))), 'áéíóúü', 'aeiouu'), '');
  v_res jsonb;
  v_fuera boolean := false;
begin
  if v_cat in ('recamaras','dormitorio','cama','camas') then v_cat := 'recamara'; end if;
  if v_cat in ('comedores','mesa') then v_cat := 'comedor'; end if;
  if v_cat in ('salas','sillon','sillones','sofa','love seat') then v_cat := 'sala'; end if;

  for i in 1..2 loop
    with base as (
      select c.*,
        -- precio real: la variante disponible más barata en Shopify (si ya se sincronizó)
        case when exists (select 1 from casa_alpa_variantes v where v.producto_id = c.id)
             then (select min(v.precio) from casa_alpa_variantes v where v.producto_id = c.id and v.disponible)
             else c.precio end as precio_desde
      from casa_alpa_catalogo c
      where c.activo
        and (v_cat is null or c.categoria = v_cat)
        and (p_personas is null or (c.capacidad_personas is not null and c.capacidad_personas >= p_personas))
        and (i = 2 or p_color is null or exists (select 1 from unnest(c.colores) col where col ilike '%' || p_color || '%'))
        and (i = 2 or p_texto is null or c.nombre ilike '%' || p_texto || '%' or c.descripcion_corta ilike '%' || p_texto || '%')
    ), disponibles as (
      select * from base where precio_desde is not null   -- excluye productos agotados en Shopify
    ), filtrado as (
      select * from disponibles
      where i = 2 or p_presupuesto_max is null or precio_desde <= p_presupuesto_max * 1.10
    )
    select jsonb_agg(row_to_json(x)::jsonb) into v_res from (
      select f.id as producto_id, f.nombre, f.categoria, f.precio_desde, f.capacidad_personas, f.medidas,
             f.materiales, f.colores, f.descripcion_corta, f.formas_pago,
             (select coalesce(jsonb_agg(jsonb_build_object('variante_id', v.shopify_variant_id, 'titulo', v.titulo, 'precio', v.precio) order by v.precio), '[]'::jsonb)
                from casa_alpa_variantes v where v.producto_id = f.id and v.disponible) as variantes
      from filtrado f
      order by case when i = 2 then f.precio_desde
                    when p_presupuesto_max is null then f.precio_desde
                    else abs(p_presupuesto_max - f.precio_desde) end
      limit case when i = 2 then 2 else greatest(1, least(coalesce(p_limite, 4), 6)) end
    ) x;

    exit when v_res is not null or (p_presupuesto_max is null and p_color is null and p_texto is null);
    v_fuera := true;  -- segunda vuelta: sin filtros de presupuesto/color/texto
  end loop;

  return jsonb_build_object(
    'productos', coalesce(v_res, '[]'::jsonb),
    'coincidencia_parcial', v_fuera and v_res is not null,
    'nota', case when v_res is null then 'No hay productos disponibles que calcen. No inventes: ofrece pasar con un asesor.'
                 when v_fuera then 'Ninguno calza exacto con presupuesto/color pedido; estas son las alternativas más económicas de la categoría. Dilo con honestidad.'
                 else 'Precios reales de la tienda. Cita el precio de la variante que corresponda (tamaño/medida/color).' end
  );
end $function$;

CREATE OR REPLACE FUNCTION public.casa_alpa_generar_link_pago(p_contact_id text, p_items jsonb, p_opportunity_id text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public'
AS $function$
declare
  v_id uuid := gen_random_uuid();
  v_items jsonb;
  v_total numeric;
  v_cart text;
  v_url text;
  v_pedidos int;
  v_validos int;
begin
  if p_contact_id is null or p_items is null or jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then
    return jsonb_build_object('ok', false, 'error', 'Faltan productos. Manda items: [{"variante_id": 123, "cantidad": 1}]');
  end if;
  v_pedidos := jsonb_array_length(p_items);

  select count(*), jsonb_agg(jsonb_build_object('variante_id', v.shopify_variant_id, 'producto', c.nombre, 'variante', v.titulo,
                                    'cantidad', i.cantidad, 'precio', v.precio)),
         sum(v.precio * i.cantidad),
         string_agg(v.shopify_variant_id::text || ':' || i.cantidad, ',')
    into v_validos, v_items, v_total, v_cart
  from (select (e->>'variante_id')::bigint as variante_id, greatest(1, least(coalesce((e->>'cantidad')::int, 1), 10)) as cantidad
          from jsonb_array_elements(p_items) e) i
  join casa_alpa_variantes v on v.shopify_variant_id = i.variante_id and v.disponible
  join casa_alpa_catalogo c on c.id = v.producto_id and c.activo;

  if coalesce(v_validos, 0) <> v_pedidos then
    return jsonb_build_object('ok', false, 'error', 'Alguna variante no existe o no está disponible. Usa variante_id tal como lo da buscar_catalogo; si no hay variante, pasa con un asesor.');
  end if;

  v_url := 'https://casaalpa.mx/cart/' || v_cart
        || '?attributes%5Bghl_contact_id%5D=' || p_contact_id
        || '&attributes%5Bvale_link_id%5D=' || v_id::text;

  insert into casa_alpa_links_pago (id, contact_id, opportunity_id, items, total, url)
  values (v_id, p_contact_id, p_opportunity_id, v_items, v_total, v_url);

  return jsonb_build_object('ok', true, 'url', v_url, 'total', v_total, 'items', v_items,
    'nota', 'Manda el url tal cual. El envío y la dirección los captura el checkout de Shopify.');
end $function$;

revoke all on function public.casa_alpa_buscar_catalogo(text, numeric, int, text, text, int) from public, anon, authenticated;
revoke all on function public.casa_alpa_generar_link_pago(text, jsonb, text) from public, anon, authenticated;
grant execute on function public.casa_alpa_buscar_catalogo(text, numeric, int, text, text, int) to service_role;
grant execute on function public.casa_alpa_generar_link_pago(text, jsonb, text) to service_role;
