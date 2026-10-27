-- Buffer de mensajes de WhatsApp para Maripino (xzen Auto): agrupa ráfagas y evita respuestas duplicadas.
-- Proyecto Supabase: XzenAuto (fllhjemdhohsewqwzrpc). Ejecutar una vez en el SQL Editor.
create table if not exists public.maripino_buffer (
  id bigserial primary key,
  contact_id text not null,
  texto text not null default '',
  origen text not null default 'mensaje',
  creado_en timestamptz not null default clock_timestamp(),
  procesado_en timestamptz
);
create index if not exists maripino_buffer_pendientes on public.maripino_buffer (contact_id, id) where procesado_en is null;
alter table public.maripino_buffer enable row level security;

-- Guarda un mensaje entrante y devuelve su id (el "turno" de esa ejecución).
create or replace function public.maripino_buffer_agregar(p_contact_id text, p_texto text, p_origen text)
returns jsonb language sql security definer set search_path = public as $$
  insert into maripino_buffer (contact_id, texto, origen)
  values (p_contact_id, coalesce(p_texto, ''), coalesce(p_origen, 'mensaje'))
  returning jsonb_build_object('id', id, 'creado_en', creado_en)
$$;

-- Si p_id es el mensaje pendiente más reciente del contacto, marca todos sus pendientes como procesados
-- y los devuelve en orden; si llegó otro después, devuelve es_ultimo = false (esa otra ejecución responde).
create or replace function public.maripino_buffer_tomar(p_contact_id text, p_id bigint)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  v_ultimo bigint;
  v_res jsonb;
begin
  perform pg_advisory_xact_lock(hashtext('maripino:' || p_contact_id));
  select max(id) into v_ultimo from maripino_buffer where contact_id = p_contact_id and procesado_en is null;
  if v_ultimo is null or v_ultimo <> p_id then
    return jsonb_build_object('es_ultimo', false);
  end if;
  with tomados as (
    update maripino_buffer set procesado_en = clock_timestamp()
    where contact_id = p_contact_id and procesado_en is null
    returning id, texto, origen, creado_en
  )
  select jsonb_build_object(
    'es_ultimo', true,
    'textos', coalesce(jsonb_agg(texto order by id) filter (where texto <> ''), '[]'::jsonb),
    'primero_en', min(creado_en),
    'cantidad', count(*)
  ) into v_res from tomados;
  -- Limpieza: lo procesado hace más de 7 días ya no hace falta.
  delete from maripino_buffer where procesado_en < now() - interval '7 days';
  return v_res;
end $$;

revoke all on function public.maripino_buffer_agregar(text, text, text) from public, anon, authenticated;
revoke all on function public.maripino_buffer_tomar(text, bigint) from public, anon, authenticated;
grant execute on function public.maripino_buffer_agregar(text, text, text) to service_role;
grant execute on function public.maripino_buffer_tomar(text, bigint) to service_role;
