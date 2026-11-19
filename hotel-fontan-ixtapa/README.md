# App de huéspedes · Hotel Fontán Ixtapa

> **Esta carpeta es la primera versión (demo sin backend).** La app actual, con cuentas, puntos, pre-check-in y panel del personal, vive en el repo `xzenauto/xzenstudio-web`, carpeta `app/fontan/`, y se publica en https://xzenstudio.com/app/fontan/

Web app móvil (un solo archivo, sin dependencias) para que el huésped, desde su teléfono:

- **Pida mantenimiento** (A/C, TV, baño, luz, caja de seguridad, puerta, WiFi…).
- **Pida room service** de desayuno o cena con carrito y hora de entrega.
- **Pida amenidades**: toallas, almohadas, agua, limpieza, cuna, plancha.
- **Pida que recojan sus maletas** (hora, piezas, destino).
- **Vea las actividades del día** con lo que pasa "ahora", filtros (Familia, Adultos, Viko Club, Noche) y recordatorios.
- **Consulte restaurantes y horarios**, con estado abierto/cerrado en tiempo real (hora de Ixtapa).
- **Haga pre-reservaciones** en los restaurantes de especialidad (La Hacienda, Kantina, Marisquería).
- **Vea el mapa** ilustrado del hotel y toque cada área para ver detalles.
- **Siga sus solicitudes** (Recibida → Asignada → En camino → Completada) y contacte a recepción por WhatsApp o teléfono.

## Archivos

| Archivo | Uso |
|---|---|
| `index.html` | App lista para publicar (fotos embebidas). **No editar a mano.** |
| `src/app.html` | Código fuente de la app. |
| `src/img/` | Fotos tomadas del sitio oficial. |
| `build.py` | Genera `index.html` desde `src/`: `python3 build.py` |

## Conectar con n8n

En `src/app.html`, dentro de `CONFIG`, pon la URL de un nodo **Webhook** (POST) de n8n en `webhookUrl` y vuelve a correr `build.py`.
Sin URL, la app trabaja en **modo demo**: guarda las solicitudes en el teléfono y simula su avance.

Cada solicitud envía un JSON como este:

```json
{
  "id": "R-K3J9A",
  "tipo": "mantenimiento | roomservice | amenidades | maletas | reserva",
  "titulo": "Mantenimiento · Aire acondicionado",
  "detalle": "Lo antes posible · No enfría",
  "hotel": "Fontán Ixtapa",
  "habitacion": "1204",
  "huesped": "Familia Herrera",
  "creadaISO": "2026-11-18T23:40:00.000Z",
  "categoria": "ac"
}
```

Campos extra por tipo: `roomservice` → `comida`, `hora`, `platillos[]`, `notas`; `reserva` → `restaurante`, `fecha`, `hora`, `personas`, `ocasion`, `notas`; `maletas` → `hora`, `piezas`, `destino`; `amenidades` → `articulos[]`, `notas`.

Desde n8n se puede enrutar por `tipo` (Switch) hacia WhatsApp del área, Google Sheets, GHL, etc.

## Datos

Tomados de hotelfontanixtapa.com: restaurantes incluidos y sus horarios, especialidades, actividades (bicitours de 14 y 4 km, volleyball de playa, música en vivo, noches DJ y temáticas, Viko Club), dirección, WhatsApp y teléfono.

**Son de ejemplo y deben confirmarse con el hotel:** menú y horario de room service, horarios de las especialidades y de albercas, el programa diario de actividades y la distribución del mapa (ilustrativo, no a escala).
