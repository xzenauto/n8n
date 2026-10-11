-- Resultados de la prueba diaria de agencias (los lee el reporte semanal)
create table if not exists public."RS_pruebas_diarias" (
  id bigint generated always as identity primary key,
  fecha timestamptz not null default now(),
  agencia text not null,
  ok boolean not null,
  paso text,
  detalle text,
  respuesta_ia text
);
alter table public."RS_pruebas_diarias" enable row level security;
create index if not exists rs_pruebas_diarias_fecha on public."RS_pruebas_diarias"(fecha);
