# Simulación — Prospecto desde el anuncio "XZEN_AgenciaViajes_VideoCarlos1"

> Datos técnicos que recibe n8n en el primer mensaje:
> `referral.source_id = 52613807845997` → vertical **agencia_viajes** → tag `demo-agencia-viajes`.
> El nombre del agente ("Sofía") es provisional.

---

**👤 Cliente:** Hola, vi su anuncio, quiero más información

**🤖 Sofía:** ¡Hola! 👋 Soy Sofía, la asistente virtual de xzen Auto.
Te cuento algo curioso: **esta conversación ya es la demostración**. Así es como tus clientes
serían atendidos en tu agencia, a cualquier hora.
¿Cómo te llamas y cómo se llama tu agencia?

**👤 Cliente:** Soy Laura, de Viajes Horizonte en Guadalajara

**🤖 Sofía:** ¡Mucho gusto, Laura! ✈️
Para entender tu caso: más o menos, ¿cuántas consultas reciben a la semana entre WhatsApp,
Facebook e Instagram?

**👤 Cliente:** Uff, como 150. Somos 3 vendedoras y no nos damos abasto, y en la noche nadie contesta

**🤖 Sofía:** Te entiendo, es justo lo que más vemos en agencias. Con 150 consultas, si solo
una de cada diez se enfría por no responder a tiempo, son 15 viajes a la semana que se van con
otra agencia.
Con el sistema:
✅ La IA contesta al momento, también de noche y en fin de semana
✅ Pregunta destino, fechas, número de viajeros y presupuesto
✅ Tus vendedoras reciben al cliente ya calificado, todo en una sola bandeja

¿Quieres que te lo demuestre en vivo? 😄

**👤 Cliente:** Va

**🤖 Sofía:** Perfecto. Imagina que **yo soy Viajes Horizonte** y tú eres una clienta que
escribe a las 11 de la noche. Escríbeme como lo haría ella 👇

**👤 Cliente:** Hola, cuánto cuesta un viaje a Cancún?

**🤖 Sofía (modo demo):** ¡Hola! Qué gusto que pienses en Cancún 🌴 Para darte la mejor
opción, ¿para qué fechas y cuántas personas viajarían?

**👤 Cliente:** Del 15 al 20 de diciembre, 2 adultos y un niño

**🤖 Sofía (modo demo):** ¡Excelente temporada! ¿Buscas todo incluido o solo hotel y vuelo?
¿Y tienes un presupuesto aproximado por persona?

**👤 Cliente:** Todo incluido, unos 15 mil por persona

**🤖 Sofía:** *(sale del papel)* Listo, ahí paro la demo 🙂
En esos 3 mensajes el sistema ya guardó en tu CRM: **Cancún · 15–20 dic · 2 adultos + 1 niño ·
todo incluido · ~$15,000 por persona**, y le avisó a una de tus vendedoras para que mande la
cotización a primera hora. Nadie se quedó sin respuesta.

Te dejo un video corto donde se ve cómo funciona por dentro 🎥
https://youtu.be/t2bvakV2WMw

¿Te gustaría una llamada de 30 minutos con nuestro equipo para ver cómo quedaría en
Viajes Horizonte?

**👤 Cliente:** Sí, cuánto cuesta el sistema?

**🤖 Sofía:** Depende de cuántos canales y vendedoras tengas, por eso en la llamada te
armamos una propuesta a la medida de tu agencia. 📅
Tengo estos espacios disponibles (hora de CDMX):
• Martes 28 de octubre, 10:00 a.m.
• Martes 28 de octubre, 4:30 p.m.
• Miércoles 29 de octubre, 12:00 p.m.
¿Cuál te acomoda?

> 🔧 *Por dentro: `consultar_disponibilidad` → GET /calendars/{calendarId}/free-slots*

**👤 Cliente:** El martes a las 4:30

**🤖 Sofía:** ¡Perfecto! Para confirmarla, ¿me compartes tu correo?

**👤 Cliente:** laura@viajeshorizonte.mx

**🤖 Sofía:** ✅ ¡Listo, Laura! Tu llamada quedó agendada:
📅 **Martes 28 de octubre, 4:30 p.m. (hora CDMX)**
Te llegará la confirmación con el enlace a laura@viajeshorizonte.mx.
Mientras tanto, si se te ocurre cualquier duda, escríbeme por aquí. ¡Nos vemos el martes! ✈️

> 🔧 *Por dentro: `agendar_cita` → POST /calendars/events/appointments ·
> tags `demo-agencia-viajes`, `cita-agendada` · oportunidad movida a "Demo agendada".*

---

## Variante: el cliente no quiere agendar todavía
**👤 Cliente:** Ahorita no, lo platico con mi socio
**🤖 Sofía:** ¡Claro! Te dejo el video para que lo vean juntos 🎥 https://youtu.be/t2bvakV2WMw
¿Te parece si te escribo el jueves para ver qué opinan?
> 🔧 *Tag `seguimiento-pendiente` → recordatorio automático en 48 h.*

## Variante: pide hablar con una persona
**👤 Cliente:** Prefiero hablar con alguien
**🤖 Sofía:** ¡Por supuesto! Ya le avisé al equipo y en breve una persona te escribe por aquí 🙌
> 🔧 *`pasar_a_humano` → tag `atender-humano`, el bot deja de responder a este contacto.*
