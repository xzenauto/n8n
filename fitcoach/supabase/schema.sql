-- FitCoach · esquema para Supabase (preparado, aún NO aplicado).
-- Ejecutar en un proyecto Supabase dedicado a la app.
-- Los usuarios se crean en auth.users (Supabase Auth); aquí guardamos el perfil.

create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  name text not null,
  phone text default '',
  is_admin boolean not null default false,
  is_athlete boolean not null default true,
  created_at timestamptz not null default now()
);

-- Programa de entreno y dieta como JSON (misma forma que src/data/types.ts)
create table public.plans (
  user_id uuid primary key references public.profiles on delete cascade,
  program jsonb not null,
  diet jsonb not null,
  updated_at timestamptz not null default now()
);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles on delete cascade,
  day_id text not null,
  day_name text not null,
  date date not null,
  readiness smallint check (readiness between 0 and 10),
  fatigue smallint check (fatigue between 0 and 10),
  note text default '',
  entries jsonb not null default '[]'
);
create index on public.sessions (user_id, date desc);

create table public.measurements (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles on delete cascade,
  date date not null,
  weight numeric, chest numeric, arm numeric,
  abs_high numeric, abs_low numeric, leg numeric
);
create index on public.measurements (user_id, date);

create table public.equivalences (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  items jsonb not null default '[]'
);

-- ---------- Seguridad (RLS) ----------
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce((select is_admin from public.profiles where id = auth.uid()), false)
$$;

alter table public.profiles enable row level security;
alter table public.plans enable row level security;
alter table public.sessions enable row level security;
alter table public.measurements enable row level security;
alter table public.equivalences enable row level security;

-- Perfil: cada uno ve/edita el suyo (sin poder hacerse admin); el admin todo.
create policy "perfil propio" on public.profiles for select using (id = auth.uid() or public.is_admin());
create policy "editar perfil propio" on public.profiles for update using (id = auth.uid())
  with check (id = auth.uid() and is_admin = (select is_admin from public.profiles where id = auth.uid()));
create policy "admin gestiona perfiles" on public.profiles for all using (public.is_admin()) with check (public.is_admin());

-- Plan: el atleta lo lee; solo el admin lo modifica.
create policy "leer plan propio" on public.plans for select using (user_id = auth.uid() or public.is_admin());
create policy "admin gestiona planes" on public.plans for all using (public.is_admin()) with check (public.is_admin());

-- Entrenos y medidas: el atleta gestiona los suyos; el admin todos.
create policy "sesiones propias" on public.sessions for all
  using (user_id = auth.uid() or public.is_admin()) with check (user_id = auth.uid() or public.is_admin());
create policy "medidas propias" on public.measurements for all
  using (user_id = auth.uid() or public.is_admin()) with check (user_id = auth.uid() or public.is_admin());

-- Equivalencias: todos los usuarios con sesión las leen; solo admin edita.
create policy "leer equivalencias" on public.equivalences for select using (auth.uid() is not null);
create policy "admin equivalencias" on public.equivalences for all using (public.is_admin()) with check (public.is_admin());

-- Alta de usuarios por el admin: se hace con una Edge Function que usa la
-- service_role key (auth.admin.createUser) y después inserta en profiles/plans.
