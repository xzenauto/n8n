# Gyrarte — sitio web con venta de boletos

Sitio estático (HTML/CSS/JS) que replica gyrarte.com y agrega:

- **Venta de boletos con Mercado Pago**: tarjeta, OXXO o transferencia.
- **Panel de administrador** en `/admin` para que el promotor dé de alta, edite, oculte o borre conciertos y vea las ventas.
- **n8n**: crea el pago, registra cada venta en Supabase y manda al comprador a GoHighLevel.
- Formularios de contacto y newsletter conectados a GoHighLevel.

```
index.html              Inicio (con "Próximos conciertos")
conciertos/             Lista de conciertos + compra
artistas-gyrarte/       Artistas
agenda/                 Galería y espectáculos
contacto/               Formulario de contacto
gracias/                Página de regreso desde Mercado Pago
admin/                  Panel del promotor (no aparece en el menú, noindex)
assets/js/config.js     URLs de Supabase y n8n
n8n/*.json              Flujos para importar en n8n
```

## Cómo funciona

```
Cliente → "Comprar boletos" → n8n (gyrarte-checkout)
   n8n lee precio, fecha y cupo REALES en Supabase → crea la preferencia en Mercado Pago
Cliente paga en Mercado Pago → regresa a /gracias
Mercado Pago avisa a n8n (gyrarte-mp-webhook)
   n8n consulta el pago en MP → guarda la venta en Supabase → contacto + nota en GHL
Promotor → /admin → (inicia sesión) → alta de conciertos → aparecen al instante en el sitio
```

**Seguridad.** Esconder la página `/admin` no es lo que la protege. La protegen las reglas RLS de Supabase: cualquiera puede *leer* los conciertos publicados, pero solo un usuario registrado en `gyrarte_admins` puede crear, editar o borrar conciertos y ver ventas. El precio nunca se toma del navegador: n8n lo lee de la base de datos.

## Puesta en marcha

### 1. Crear el usuario del promotor (Supabase, proyecto XzenAuto)
1. Supabase → Authentication → Users → **Add user** → correo y contraseña. Marca "Auto confirm user".
2. SQL Editor:
   ```sql
   insert into public.gyrarte_admins (user_id, email, nombre)
   select id, email, 'Nombre del promotor' from auth.users where email = 'correo@promotor.com';
   ```
3. Para que funcione "Olvidé mi contraseña", agrega `https://gyrarte.com/admin/` en Authentication → URL Configuration → Redirect URLs.

### 2. n8n
1. Importa los 3 archivos de `n8n/` (Workflows → Import from file).
2. Crea estas credenciales y asígnalas en los nodos marcados:
   - **Mercado Pago Gyrarte** (Header Auth): Name `Authorization`, Value `Bearer APP_USR-…` (el *Access Token* de producción de tu cuenta de Mercado Pago → Tus integraciones).
   - **Supabase XzenAuto (service role)** (tipo Supabase): host `https://fllhjemdhohsewqwzrpc.supabase.co` y la *service_role key*. Esta clave nunca debe ir en el sitio web.
   - **GHL Gyrarte** (Header Auth): Name `Authorization`, Value `Bearer <token de la subcuenta>`.
3. Reemplaza `REEMPLAZAR_LOCATION_ID_GYRARTE` por el locationId de la subcuenta de GHL de Gyrarte (flujos 2 y 3).
4. Activa los 3 flujos.
5. En GHL, crea un workflow con disparador **Contact Tag = `gyrarte-boleto`** que envíe el correo o WhatsApp de confirmación al comprador.

### 3. Subir a Hostinger
Este sitio necesita un plan de **Web Hosting** (con Administrador de archivos). El *Website Builder* no permite subir HTML propio.
1. hPanel → Archivos → Administrador de archivos → `public_html/`.
2. Sube todo el contenido de esta carpeta **excepto** `n8n/` y `LEEME.md`.
3. Apunta el dominio gyrarte.com a ese hosting. Haz el cambio cuando ya tengas todo probado.

### Prueba recomendada antes de publicar
Usa las credenciales de **prueba** de Mercado Pago (usuarios de prueba) y crea un concierto de prueba oculto, con precio de $10, para hacer una compra completa.

## Pendientes / notas
- Las fotos se cargan desde `assets.zyrosite.com` (los servidores de Hostinger Builder). Si cancelas el Builder, descárgalas y súbelas a `assets/img/`.
- El cupo cuenta los pagos aprobados y pendientes. Un pago iniciado y no terminado no aparta lugar.
- El boleto es el comprobante de Mercado Pago más la confirmación por correo. Si quieres boletos con código QR y control de acceso, se agrega después.
