-- FitCoach (xzenstudio.com/app/appgym) · tablas gym_* en el proyecto Supabase
-- "Guarderia Fito&Friends", que comparte con la guardería, merch y pádel.
-- Los usuarios son de Supabase Auth; un usuario solo entra en FitCoach si tiene fila en gym_profiles.

create table public.gym_profiles (
  id uuid primary key references auth.users on delete cascade,
  email text not null,
  name text not null,
  phone text not null default '',
  is_admin boolean not null default false,
  is_athlete boolean not null default true,
  created_at timestamptz not null default now()
);

-- Programa de entreno y dieta en JSON (misma forma que src/data/types.ts)
create table public.gym_plans (
  user_id uuid primary key references public.gym_profiles on delete cascade,
  program jsonb not null,
  diet jsonb not null,
  updated_at timestamptz not null default now()
);

create table public.gym_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.gym_profiles on delete cascade,
  day_id text not null,
  day_name text not null,
  date date not null,
  readiness smallint check (readiness between 0 and 10),
  fatigue smallint check (fatigue between 0 and 10),
  note text not null default '',
  entries jsonb not null default '[]',
  created_at timestamptz not null default now()
);
create index gym_sessions_user_date on public.gym_sessions (user_id, date desc);

create table public.gym_measurements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.gym_profiles on delete cascade,
  date date not null,
  weight numeric, chest numeric, arm numeric,
  abs_high numeric, abs_low numeric, leg numeric
);
create index gym_measurements_user_date on public.gym_measurements (user_id, date);

create table public.gym_equivalences (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  items jsonb not null default '[]',
  created_at timestamptz not null default now()
);

-- ---------- Seguridad ----------
create or replace function public.gym_is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select is_admin from public.gym_profiles where id = auth.uid()), false)
$$;
revoke execute on function public.gym_is_admin() from anon;

-- Un atleta puede cambiar su nombre y teléfono, pero no su email ni sus roles.
create or replace function public.gym_profiles_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if coalesce(auth.role(), '') <> 'service_role' and not public.gym_is_admin() then
    new.is_admin := old.is_admin;
    new.is_athlete := old.is_athlete;
    new.email := old.email;
  end if;
  new.id := old.id;
  return new;
end $$;
create trigger gym_profiles_guard before update on public.gym_profiles
  for each row execute function public.gym_profiles_guard();

alter table public.gym_profiles enable row level security;
alter table public.gym_plans enable row level security;
alter table public.gym_sessions enable row level security;
alter table public.gym_measurements enable row level security;
alter table public.gym_equivalences enable row level security;

create policy gym_profiles_select on public.gym_profiles for select to authenticated
  using (id = (select auth.uid()) or public.gym_is_admin());
create policy gym_profiles_update on public.gym_profiles for update to authenticated
  using (id = (select auth.uid()) or public.gym_is_admin());
-- Altas y bajas solo desde la Edge Function gym-admin (service role).

create policy gym_plans_select on public.gym_plans for select to authenticated
  using (user_id = (select auth.uid()) or public.gym_is_admin());
create policy gym_plans_admin_insert on public.gym_plans for insert to authenticated
  with check (public.gym_is_admin());
create policy gym_plans_admin_update on public.gym_plans for update to authenticated
  using (public.gym_is_admin()) with check (public.gym_is_admin());
create policy gym_plans_admin_delete on public.gym_plans for delete to authenticated
  using (public.gym_is_admin());

create policy gym_sessions_own on public.gym_sessions for all to authenticated
  using (user_id = (select auth.uid()) or public.gym_is_admin())
  with check (user_id = (select auth.uid()) or public.gym_is_admin());

create policy gym_measurements_own on public.gym_measurements for all to authenticated
  using (user_id = (select auth.uid()) or public.gym_is_admin())
  with check (user_id = (select auth.uid()) or public.gym_is_admin());

create policy gym_equivalences_select on public.gym_equivalences for select to authenticated
  using (exists (select 1 from public.gym_profiles where id = (select auth.uid())));
create policy gym_equivalences_admin_insert on public.gym_equivalences for insert to authenticated
  with check (public.gym_is_admin());
create policy gym_equivalences_admin_update on public.gym_equivalences for update to authenticated
  using (public.gym_is_admin()) with check (public.gym_is_admin());
create policy gym_equivalences_admin_delete on public.gym_equivalences for delete to authenticated
  using (public.gym_is_admin());

-- ---------- Hábitos (migración gym_habits) ----------
alter table public.gym_plans add column habits jsonb not null default '{"goal":"","items":[]}'::jsonb;

create table public.gym_habit_logs (
  user_id uuid not null references public.gym_profiles on delete cascade,
  date date not null,
  done text[] not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (user_id, date)
);
alter table public.gym_habit_logs enable row level security;
create policy gym_habit_logs_own on public.gym_habit_logs for all to authenticated
  using (user_id = (select auth.uid()) or public.gym_is_admin())
  with check (user_id = (select auth.uid()) or public.gym_is_admin());

-- ---------- (NO APLICADO) Alternativa para que el atleta edite sus hábitos por RLS ----------
-- Hoy lo hace la Edge Function gym-admin (acción my-habits), que solo modifica el campo habits del propio atleta.
create or replace function public.gym_plans_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if coalesce(auth.role(), '') <> 'service_role' and not public.gym_is_admin() then
    new.program := old.program;
    new.diet := old.diet;
  end if;
  new.user_id := old.user_id;
  return new;
end $$;
revoke execute on function public.gym_plans_guard() from public, anon, authenticated;
create trigger gym_plans_guard before update on public.gym_plans
  for each row execute function public.gym_plans_guard();
create policy gym_plans_self_update on public.gym_plans for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

-- ---------- Notificaciones push (migración gym_push_notifications) ----------
create table if not exists public.gym_push_subs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.gym_profiles on delete cascade,
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  tz text not null default 'Atlantic/Canary',
  last_quote date,
  last_habits date,
  created_at timestamptz not null default now()
);
alter table public.gym_push_subs enable row level security;
create policy gym_push_subs_own on public.gym_push_subs for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
-- pg_cron cada hora → función gym-push (8:00 frase del día, 21:00 hábitos pendientes, hora local)
select cron.schedule('gym-recordatorios', '0 * * * *', $$
  select net.http_post(url := 'https://jlbrcgdfsqlvssgbrxzr.supabase.co/functions/v1/gym-push',
    headers := jsonb_build_object('Content-Type', 'application/json', 'x-cron-secret', (select valor from public.config_privada where clave = 'cron_secret')),
    body := '{}'::jsonb);
$$);

-- ---------- Plantillas, biblioteca de ejercicios y comunidad (migración gym_templates_library_community) ----------
-- gym_templates (admin), gym_exercises (lectura: usuarios de la app; escritura: admin),
-- gym_announcements (lectura: usuarios de la app; escritura: admin) y la función
-- gym_community_ranking(p_from, p_to): % medio diario de hábitos cumplidos (cada hábito vale
-- 100 / nº de hábitos del atleta) y racha de días al 100 %, sin exponer los hábitos de nadie.
-- Ver la migración aplicada en Supabase para el SQL completo.
