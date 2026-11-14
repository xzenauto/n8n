-- Columnas para cotizaciones de solo vuelo (aplicado 2026-11-13)
alter table public."RSIndependencia_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
alter table public."RSCentro_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
alter table public."RSPeriodismo_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
alter table public."RSMatriz_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
alter table public."RSHijar_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
alter table public."RSSaltillo_leads" add column if not exists tipo_viaje text, add column if not exists origen text, add column if not exists equipaje text;
