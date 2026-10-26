#!/usr/bin/env bash
# Sube (crea) los flujos de Maripino en n8n por la API pública.
# Requiere que la petición lleve la cabecera X-N8N-API-KEY (la inyecta el proxy del entorno
# o se exporta N8N_API_KEY).
set -euo pipefail
cd "$(dirname "$0")"
N8N_URL="${N8N_URL:-https://n8n.srv964593.hstgr.cloud}"
python3 generar_flujos.py
for f in maripino-configuracion.json maripino-agente.json; do
  echo "→ $f"
  curl -sS -X POST "$N8N_URL/api/v1/workflows" \
    -H "Content-Type: application/json" \
    ${N8N_API_KEY:+-H "X-N8N-API-KEY: $N8N_API_KEY"} \
    --data @"$f"
  echo
done
