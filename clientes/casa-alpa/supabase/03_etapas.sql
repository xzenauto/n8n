-- 03: etapas nuevas
alter table public.casa_alpa_prospectos drop constraint if exists casa_alpa_prospectos_etapa_check;
alter table public.casa_alpa_prospectos add constraint casa_alpa_prospectos_etapa_check
  check (etapa = any (array['explorando','interesado','cotizacion_solicitada','listo_comprar','link_enviado','handoff','compro']));
