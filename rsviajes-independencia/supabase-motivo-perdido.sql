-- Motivo cuando el cliente se da por perdido (aplicado 2026-11-21)
alter table public."RSIndependencia_leads" add column if not exists motivo_perdido text;
alter table public."RSCentro_leads" add column if not exists motivo_perdido text;
alter table public."RSPeriodismo_leads" add column if not exists motivo_perdido text;
alter table public."RSMatriz_leads" add column if not exists motivo_perdido text;
alter table public."RSHijar_leads" add column if not exists motivo_perdido text;
alter table public."RSSaltillo_leads" add column if not exists motivo_perdido text;
