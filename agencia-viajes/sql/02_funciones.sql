-- Agencia de viajes (Lucía) – funciones RPC que usa n8n (estado final).
-- Horario hábil: L-V 9:00-18:00, Sáb 10:00-14:00, Dom cerrado (America/Mexico_City).

create or replace function public.viajes_touch() returns trigger
language plpgsql set search_path = public as $$
begin new.actualizado_en := now(); return new; end $$;

drop trigger if exists viajes_contactos_touch on public.viajes_contactos;
create trigger viajes_contactos_touch before update on public.viajes_contactos
  for each row execute function public.viajes_touch();
drop trigger if exists viajes_leads_touch on public.viajes_leads;
create trigger viajes_leads_touch before update on public.viajes_leads
  for each row execute function public.viajes_touch();

-- Siguiente momento dentro del horario hábil
create or replace function public.viajes_siguiente_horario(ts timestamptz)
returns timestamptz language plpgsql stable set search_path = public as $$
declare
  l timestamp := ts at time zone 'America/Mexico_City';
  d int; abre time; cierra time; i int := 0;
begin
  loop
    d := extract(isodow from l);            -- 1=lun ... 7=dom
    if d between 1 and 5 then abre := '09:00'; cierra := '18:00';
    elsif d = 6 then abre := '10:00'; cierra := '14:00';
    else abre := null; end if;
    if abre is not null then
      if l::time < abre then
        return (l::date + abre) at time zone 'America/Mexico_City';
      elsif l::time < cierra then
        return l at time zone 'America/Mexico_City';
      end if;
    end if;
    l := (l::date + 1)::timestamp;
    i := i + 1; exit when i > 8;
  end loop;
  return ts;
end $$;

-- Serie de envíos (horas desde p_desde) en horario hábil y sin que dos caigan juntos
create or replace function public.viajes_serie_horarios(p_desde timestamptz, p_horas numeric[])
returns timestamptz[] language plpgsql stable set search_path = public as $$
declare res timestamptz[] := '{}'; prev timestamptz; prev_h numeric := 0; t timestamptz; i int;
begin
  for i in 1 .. coalesce(array_length(p_horas, 1), 0) loop
    t := p_desde + make_interval(secs => p_horas[i] * 3600);
    if prev is not null then
      t := greatest(t, prev + make_interval(secs => (p_horas[i] - prev_h) * 1800));
    end if;
    t := viajes_siguiente_horario(t);
    res := res || t; prev := t; prev_h := p_horas[i];
  end loop;
  return res;
end $$;

-- Recordatorio: día anterior 10:00; si cae domingo, sábado 11:00
create or replace function public.viajes_horario_recordatorio(p_fecha date)
returns timestamptz language sql immutable set search_path = public as $$
  select case when extract(isodow from p_fecha - 1) = 7
              then ((p_fecha - 2) + time '11:00') at time zone 'America/Mexico_City'
              else ((p_fecha - 1) + time '10:00') at time zone 'America/Mexico_City' end
$$;

-- Agrupar ráfagas de mensajes
create or replace function public.viajes_registrar_mensaje(p_contact_id text)
returns jsonb language sql set search_path = public as $$
  insert into viajes_contactos (ghl_contact_id, ultimo_msg_cliente_en)
  values (p_contact_id, clock_timestamp())
  on conflict (ghl_contact_id) do update set ultimo_msg_cliente_en = clock_timestamp()
  returning jsonb_build_object('contact_id', ghl_contact_id, 'token', ultimo_msg_cliente_en)
$$;

create or replace function public.viajes_es_ultimo(p_contact_id text, p_token timestamptz)
returns jsonb language sql stable set search_path = public as $$
  select jsonb_build_object('es_ultimo', coalesce(max(ultimo_msg_cliente_en) <= p_token, true))
  from viajes_contactos where ghl_contact_id = p_contact_id
$$;

-- Contexto para Lucía: contacto, leads, promos vigentes y mapa ad_id -> promo
create or replace function public.viajes_get_contexto(p_contact_id text)
returns jsonb language sql stable set search_path = public as $$
  select jsonb_build_object(
    'contacto', (select to_jsonb(c) from viajes_contactos c where c.ghl_contact_id = p_contact_id),
    'ads', coalesce((select jsonb_object_agg(a, jsonb_build_object('id', p.id, 'titulo', p.titulo, 'destino', p.destino,
                 'vigente', exists (select 1 from viajes_promos_vigentes v where v.id = p.id)))
               from viajes_promos p, unnest(p.ad_ids) a), '{}'::jsonb),
    'leads', coalesce((select jsonb_agg(to_jsonb(l) order by l.creado_en desc)
                       from (select * from viajes_leads where ghl_contact_id = p_contact_id
                             order by creado_en desc limit 5) l), '[]'::jsonb),
    'promos', coalesce((select jsonb_agg(jsonb_build_object(
                 'id', id, 'destino', destino, 'hotel', hotel, 'titulo', titulo,
                 'vigencia_hasta', vigencia_hasta, 'viaje_desde', viaje_desde, 'viaje_hasta', viaje_hasta,
                 'noches', noches, 'plan', plan, 'dias_aplica', dias_aplica, 'precio_desde', precio_desde,
                 'precio_detalle', precio_detalle, 'precios_menores', precios_menores, 'incluye', incluye,
                 'condiciones', condiciones, 'descripcion', descripcion, 'ad_ids', ad_ids) order by destino)
               from viajes_promos_vigentes), '[]'::jsonb)
  )
$$;

-- Guardar turno de Lucía y (re)programar seguimientos por datos incompletos (5h, 20h, 48h, cierre 72h)
create or replace function public.viajes_guardar_turno(p jsonb)
returns jsonb language plpgsql set search_path = public as $$
declare
  v_contact text := p->>'contact_id';
  v_lead viajes_leads;
  v_prev_completo boolean := false;
  v_serie text := to_char(clock_timestamp(), 'YYYYMMDDHH24MISS');
  v_base timestamptz := now();
begin
  insert into viajes_contactos (ghl_contact_id) values (v_contact) on conflict do nothing;
  update viajes_contactos set
    nombre = coalesce(nullif(p->>'nombre',''), nombre),
    telefono = coalesce(nullif(p->>'telefono',''), telefono),
    canal = coalesce(nullif(p->>'canal',''), canal),
    ghl_conversation_id = coalesce(nullif(p->>'conversation_id',''), ghl_conversation_id),
    ultimo_procesado_en = greatest(ultimo_procesado_en, (p->>'procesado_hasta')::timestamptz),
    ultimo_msg_ia_en = case when coalesce(p->>'respuesta_enviada','false')::boolean then now() else ultimo_msg_ia_en end
  where ghl_contact_id = v_contact;

  select datos_completos into v_prev_completo from viajes_leads where ghl_opportunity_id = p->>'opportunity_id';
  v_prev_completo := coalesce(v_prev_completo, false);

  insert into viajes_leads as l (ghl_contact_id, ghl_opportunity_id, canal, ad_id, promo_id, destino,
      fecha_salida, fecha_regreso, fechas_texto, fechas_sin_definir, adultos, ninos, edades_ninos,
      datos_completos, urgente, etapa, resumen_ia, completado_en)
  values (v_contact, p->>'opportunity_id', p->>'canal', nullif(p->>'ad_id',''),
      (select id from viajes_promos where id = nullif(p->>'promo_id','')),
      nullif(p->>'destino',''), nullif(p->>'fecha_salida','')::date, nullif(p->>'fecha_regreso','')::date,
      nullif(p->>'fechas_texto',''), coalesce((p->>'fechas_sin_definir')::boolean,false),
      nullif(p->>'adultos','')::int, nullif(p->>'ninos','')::int,
      case when jsonb_typeof(p->'edades_ninos') = 'array'
           then array(select jsonb_array_elements_text(p->'edades_ninos')::int) end,
      coalesce((p->>'datos_completos')::boolean,false), coalesce((p->>'urgente')::boolean,false),
      coalesce(p->>'etapa','nuevo'), p->>'resumen',
      case when coalesce((p->>'datos_completos')::boolean,false) then now() end)
  on conflict (ghl_opportunity_id) do update set
      canal = coalesce(excluded.canal, l.canal),
      ad_id = coalesce(excluded.ad_id, l.ad_id),
      promo_id = coalesce(excluded.promo_id, l.promo_id),
      destino = excluded.destino, fecha_salida = excluded.fecha_salida, fecha_regreso = excluded.fecha_regreso,
      fechas_texto = excluded.fechas_texto, fechas_sin_definir = excluded.fechas_sin_definir,
      adultos = excluded.adultos, ninos = excluded.ninos, edades_ninos = excluded.edades_ninos,
      datos_completos = excluded.datos_completos, urgente = excluded.urgente, etapa = excluded.etapa,
      resumen_ia = coalesce(excluded.resumen_ia, l.resumen_ia),
      completado_en = coalesce(l.completado_en, excluded.completado_en)
  returning * into v_lead;

  -- El cliente respondió: se cancelan los seguimientos de datos pendientes
  update viajes_seguimientos set estado = 'cancelado', error = 'cliente respondió'
  where ghl_contact_id = v_contact and tipo = 'datos' and estado = 'pendiente';

  if not v_lead.datos_completos and not coalesce((p->>'escalar')::boolean,false) then
    insert into viajes_seguimientos (ghl_contact_id, lead_id, tipo, numero, serie, programado_para)
    select v_contact, v_lead.id, 'datos', (array[1,2,3,99])[k], v_serie, t
    from unnest(viajes_serie_horarios(v_base, array[5,20,48,72])) with ordinality u(t, k);
  end if;

  insert into viajes_eventos_log (ghl_contact_id, tipo, detalle) values (v_contact, 'turno_lucia', p);

  return jsonb_build_object('lead_id', v_lead.id,
    'recien_completado', v_lead.datos_completos and not v_prev_completo,
    'datos_completos', v_lead.datos_completos);
end $$;

-- Mensaje que atiende una vendedora (o IA pausada): marcar procesado y cortar seguimientos
create or replace function public.viajes_marcar_procesado(p_contact_id text, p_hasta timestamptz, p_motivo text)
returns jsonb language plpgsql set search_path = public as $$
declare n int;
begin
  update viajes_contactos set ultimo_procesado_en = greatest(ultimo_procesado_en, p_hasta)
  where ghl_contact_id = p_contact_id;
  update viajes_seguimientos set estado = 'cancelado', error = 'cliente respondió'
  where ghl_contact_id = p_contact_id and estado = 'pendiente';
  get diagnostics n = row_count;
  insert into viajes_eventos_log (ghl_contact_id, tipo, detalle)
  values (p_contact_id, 'mensaje_' || p_motivo, jsonb_build_object('cancelados', n));
  return jsonb_build_object('cancelados', n);
end $$;

create or replace function public.viajes_asegurar_lead(p_contact_id text, p_opp_id text, p_nombre text, p_etapa text)
returns uuid language plpgsql set search_path = public as $$
declare v uuid;
begin
  insert into viajes_contactos (ghl_contact_id, nombre) values (p_contact_id, p_nombre)
  on conflict (ghl_contact_id) do update set nombre = coalesce(viajes_contactos.nombre, excluded.nombre);
  insert into viajes_leads (ghl_contact_id, ghl_opportunity_id, etapa)
  values (p_contact_id, p_opp_id, coalesce(p_etapa, 'nuevo'))
  on conflict (ghl_opportunity_id) do update set etapa = coalesce(p_etapa, viajes_leads.etapa)
  returning id into v;
  return v;
end $$;

-- Seguimientos de cotización: 5h, 10h, 20h, 48h desde que la tarjeta entró a "Cotización enviada"
create or replace function public.viajes_programar_cotizacion(p_items jsonb)
returns jsonb language plpgsql set search_path = public as $$
declare it jsonb; v_lead uuid; v_desde timestamptz; v_serie text; nuevos int := 0;
begin
  for it in select * from jsonb_array_elements(coalesce(p_items,'[]'::jsonb)) loop
    v_lead := viajes_asegurar_lead(it->>'contact_id', it->>'opportunity_id', it->>'nombre', 'cotizacion_enviada');
    v_desde := coalesce((it->>'desde')::timestamptz, now());
    v_serie := to_char(v_desde at time zone 'UTC', 'YYYYMMDDHH24MISS');
    if not exists (select 1 from viajes_seguimientos where lead_id = v_lead and tipo = 'cotizacion' and serie = v_serie) then
      update viajes_seguimientos set estado = 'cancelado', error = 'nueva serie'
      where lead_id = v_lead and tipo = 'cotizacion' and estado = 'pendiente';
      insert into viajes_seguimientos (ghl_contact_id, lead_id, tipo, numero, serie, programado_para, estado, error)
      select it->>'contact_id', v_lead, 'cotizacion', n, v_serie, t,
             case when t < now() - interval '2 hours' then 'cancelado' else 'pendiente' end,
             case when t < now() - interval '2 hours' then 'vencido al programar' end
      from (select k::int n, t from unnest(viajes_serie_horarios(v_desde, array[5,10,20,48])) with ordinality u(t, k)) x;
      nuevos := nuevos + 1;
    end if;
  end loop;
  return jsonb_build_object('series_nuevas', nuevos);
end $$;

-- Recordatorios de pago y de viaje (1 día antes)
create or replace function public.viajes_sync_recordatorios(p_contactos text[], p_items jsonb)
returns jsonb language plpgsql set search_path = public as $$
declare it jsonb; v_lead uuid; v_fecha date; v_prog timestamptz; n int := 0; c int;
begin
  create temp table if not exists _rec_vigentes (contact text, tipo text, referencia text, fecha date) on commit drop;
  truncate _rec_vigentes;
  for it in select * from jsonb_array_elements(coalesce(p_items,'[]'::jsonb)) loop
    v_fecha := (it->>'fecha')::date;
    continue when v_fecha is null or v_fecha < (now() at time zone 'America/Mexico_City')::date;
    v_lead := viajes_asegurar_lead(it->>'contact_id', it->>'opportunity_id', it->>'nombre', it->>'etapa');
    v_prog := viajes_horario_recordatorio(v_fecha);
    if v_prog < now() then v_prog := viajes_siguiente_horario(now()); end if;
    continue when v_prog >= (v_fecha + time '00:00') at time zone 'America/Mexico_City' + interval '1 day';
    insert into _rec_vigentes values (it->>'contact_id', it->>'tipo', it->>'referencia', v_fecha);
    insert into viajes_recordatorios (ghl_contact_id, lead_id, tipo, referencia, fecha_evento, programado_para)
    values (it->>'contact_id', v_lead, it->>'tipo', it->>'referencia',
            (v_fecha + time '12:00') at time zone 'America/Mexico_City', v_prog)
    on conflict (ghl_contact_id, tipo, referencia, fecha_evento) do update
      set estado = case when viajes_recordatorios.estado = 'cancelado' then 'pendiente' else viajes_recordatorios.estado end,
          programado_para = case when viajes_recordatorios.estado = 'cancelado' then excluded.programado_para
                                 else viajes_recordatorios.programado_para end;
    n := n + 1;
  end loop;
  update viajes_recordatorios r set estado = 'cancelado', error = 'ya no aplica'
  where r.estado = 'pendiente' and r.ghl_contact_id = any(p_contactos)
    and not exists (select 1 from _rec_vigentes v where v.contact = r.ghl_contact_id and v.tipo = r.tipo
                    and v.referencia = r.referencia
                    and (v.fecha + time '12:00') at time zone 'America/Mexico_City' = r.fecha_evento);
  get diagnostics c = row_count;
  return jsonb_build_object('vigentes', n, 'cancelados', c);
end $$;

-- Tomar lo que toca enviar (y marcarlo "procesando" para no duplicar)
create or replace function public.viajes_tomar_pendientes(p_limit int default 25)
returns jsonb language plpgsql set search_path = public as $$
declare res jsonb;
begin
  update viajes_seguimientos set estado = 'fallido', error = 'atorado en procesando'
  where estado = 'procesando' and programado_para < now() - interval '2 hours';
  update viajes_recordatorios set estado = 'fallido', error = 'atorado en procesando'
  where estado = 'procesando' and programado_para < now() - interval '2 hours';

  with s as (
    update viajes_seguimientos set estado = 'procesando'
    where id in (select id from viajes_seguimientos where estado = 'pendiente' and programado_para <= now()
                 order by programado_para limit p_limit for update skip locked)
    returning 'seguimiento'::text tabla, id, ghl_contact_id, lead_id, tipo, numero, null::text referencia, null::timestamptz fecha_evento
  ), r as (
    update viajes_recordatorios set estado = 'procesando'
    where id in (select id from viajes_recordatorios where estado = 'pendiente' and programado_para <= now()
                 order by programado_para limit p_limit for update skip locked)
    returning 'recordatorio'::text tabla, id, ghl_contact_id, lead_id, tipo, null::int numero, referencia, fecha_evento
  ), todo as (select * from s union all select * from r)
  select coalesce(jsonb_agg(jsonb_build_object(
      'tabla', t.tabla, 'id', t.id, 'contact_id', t.ghl_contact_id, 'lead_id', t.lead_id, 'tipo', t.tipo,
      'numero', t.numero, 'referencia', t.referencia, 'fecha_evento', t.fecha_evento,
      'canal', c.canal, 'nombre', c.nombre, 'conversation_id', c.ghl_conversation_id,
      'opportunity_id', l.ghl_opportunity_id, 'lead', to_jsonb(l))), '[]'::jsonb)
  into res
  from todo t
  left join viajes_contactos c on c.ghl_contact_id = t.ghl_contact_id
  left join viajes_leads l on l.id = t.lead_id;
  return res;
end $$;

-- Registrar el resultado de cada envío
create or replace function public.viajes_marcar_envio(p_items jsonb)
returns jsonb language plpgsql set search_path = public as $$
declare it jsonb; n int := 0;
begin
  for it in select * from jsonb_array_elements(coalesce(p_items,'[]'::jsonb)) loop
    if it->>'tabla' = 'seguimiento' then
      update viajes_seguimientos set estado = it->>'estado', mensaje = it->>'mensaje', error = it->>'error',
        enviado_en = case when it->>'estado' in ('enviado','manual') then now() end
      where id = (it->>'id')::uuid;
      if it->>'estado' = 'cancelado' then   -- si se cancela uno, se cancela el resto de la serie
        update viajes_seguimientos s set estado = 'cancelado', error = it->>'error'
        from viajes_seguimientos x
        where x.id = (it->>'id')::uuid and s.lead_id = x.lead_id and s.tipo = x.tipo
          and s.serie = x.serie and s.estado = 'pendiente';
      end if;
    else
      update viajes_recordatorios set estado = it->>'estado', mensaje = it->>'mensaje', error = it->>'error',
        enviado_en = case when it->>'estado' in ('enviado','manual') then now() end
      where id = (it->>'id')::uuid;
    end if;
    if nullif(it->>'etapa','') is not null then
      update viajes_leads set etapa = it->>'etapa' where id = (it->>'lead_id')::uuid;
    end if;
    if it->>'estado' = 'enviado' then
      update viajes_contactos set ultimo_msg_ia_en = now() where ghl_contact_id = it->>'contact_id';
    end if;
    n := n + 1;
  end loop;
  return jsonb_build_object('actualizados', n);
end $$;

-- Sincronizar promos desde Google Sheets (las que se borran del Sheet se desactivan)
create or replace function public.viajes_sync_promos(p_rows jsonb)
returns jsonb language plpgsql set search_path = public as $$
declare n int; d int;
begin
  create temp table if not exists _promos_in on commit drop as select * from viajes_promos where false;
  truncate _promos_in;
  insert into _promos_in (id, activa, destino, hotel, titulo, vigencia_desde, vigencia_hasta, viaje_desde, viaje_hasta,
      noches, plan, dias_aplica, precio_desde, precio_detalle, precios_menores, incluye, condiciones, descripcion,
      imagen_url, ad_ids, actualizado_en)
  select distinct on (trim(r->>'id_promo'))
    trim(r->>'id_promo'),
    upper(coalesce(r->>'activa','SI')) in ('SI','SÍ','TRUE','1','X','ACTIVA'),
    coalesce(nullif(trim(r->>'destino'),''),'Sin destino'), nullif(trim(r->>'hotel'),''),
    coalesce(nullif(trim(r->>'titulo'),''), trim(r->>'id_promo')),
    nullif(r->>'vigencia_desde','')::date, nullif(r->>'vigencia_hasta','')::date,
    nullif(r->>'viaje_desde','')::date, nullif(r->>'viaje_hasta','')::date,
    nullif(regexp_replace(coalesce(r->>'noches',''),'[^0-9]','','g'),'')::int,
    nullif(r->>'plan',''), nullif(r->>'dias_aplica',''),
    nullif(regexp_replace(coalesce(r->>'precio_desde',''),'[^0-9.]','','g'),'')::numeric,
    nullif(r->>'precio_detalle',''), nullif(r->>'precios_menores',''), nullif(r->>'incluye',''),
    nullif(r->>'condiciones',''), nullif(r->>'descripcion',''), nullif(r->>'imagen_url',''),
    coalesce(array(select trim(x) from unnest(string_to_array(coalesce(r->>'ad_ids',''), ',')) x where trim(x) <> ''), '{}'),
    now()
  from jsonb_array_elements(coalesce(p_rows,'[]'::jsonb)) r
  where nullif(trim(r->>'id_promo'),'') is not null;

  insert into viajes_promos select * from _promos_in
  on conflict (id) do update set activa = excluded.activa, destino = excluded.destino, hotel = excluded.hotel,
    titulo = excluded.titulo, vigencia_desde = excluded.vigencia_desde, vigencia_hasta = excluded.vigencia_hasta,
    viaje_desde = excluded.viaje_desde, viaje_hasta = excluded.viaje_hasta, noches = excluded.noches,
    plan = excluded.plan, dias_aplica = excluded.dias_aplica, precio_desde = excluded.precio_desde,
    precio_detalle = excluded.precio_detalle, precios_menores = excluded.precios_menores,
    incluye = excluded.incluye, condiciones = excluded.condiciones, descripcion = excluded.descripcion,
    imagen_url = excluded.imagen_url, ad_ids = excluded.ad_ids, actualizado_en = now();
  get diagnostics n = row_count;
  update viajes_promos set activa = false, actualizado_en = now()
  where activa and id not in (select id from _promos_in);
  get diagnostics d = row_count;
  return jsonb_build_object('sincronizadas', n, 'desactivadas', d);
end $$;

-- Solo el backend (service_role) puede ejecutar estas funciones
do $$
declare f text;
begin
  foreach f in array array[
    'viajes_registrar_mensaje(text)','viajes_es_ultimo(text,timestamptz)','viajes_get_contexto(text)',
    'viajes_guardar_turno(jsonb)','viajes_marcar_procesado(text,timestamptz,text)',
    'viajes_asegurar_lead(text,text,text,text)','viajes_programar_cotizacion(jsonb)',
    'viajes_sync_recordatorios(text[],jsonb)','viajes_tomar_pendientes(int)','viajes_marcar_envio(jsonb)',
    'viajes_sync_promos(jsonb)','viajes_siguiente_horario(timestamptz)','viajes_serie_horarios(timestamptz,numeric[])',
    'viajes_horario_recordatorio(date)','viajes_touch()']
  loop
    execute format('revoke execute on function public.%s from public, anon, authenticated', f);
    execute format('grant execute on function public.%s to service_role', f);
  end loop;
end $$;
