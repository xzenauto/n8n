// FitCoach · notificaciones push.
// - La llama pg_cron cada hora (cabecera x-cron-secret): a las 8:00 envía la frase del día
//   y a las 21:00 recuerda los hábitos que faltan, en la hora local de cada suscripción.
// - Un atleta con sesión puede pedir una notificación de prueba ({ action: 'test' }).
import webpush from 'npm:web-push@3.6.7';
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';

const cors = {
	'Access-Control-Allow-Origin': '*',
	'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-cron-secret',
	'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (d: unknown, status = 200) => new Response(JSON.stringify(d), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

// Frases propias (una por día del mes). Se podrán cambiar por otra fuente más adelante.
const FRASES = [
	'La constancia gana a la motivación. Hoy toca cumplir, aunque no apetezca.',
	'No tienes que hacerlo perfecto, tienes que hacerlo hoy.',
	'Cada repetición cuenta, también las que nadie ve.',
	'El progreso es lento hasta que de repente se nota. Sigue.',
	'Tu yo de dentro de tres meses te va a dar las gracias por hoy.',
	'Disciplina es elegir lo que quieres de verdad por encima de lo que quieres ahora.',
	'Un buen día empieza con una decisión pequeña. Toma la primera.',
	'No cuentes los días: haz que los días cuenten.',
	'El cansancio pasa; el orgullo de haber cumplido se queda.',
	'Lo difícil de hoy es el calentamiento de lo que vendrá mañana.',
	'Hazlo por la persona que quieres ser, no por la que fuiste ayer.',
	'Pequeños hábitos, repetidos cada día, construyen un cuerpo y una mente nuevos.',
	'Si hoy cuesta, es que estás creciendo.',
	'No esperes a tener ganas: las ganas llegan cuando empiezas.',
	'La versión fuerte de ti se construye un día normal como hoy.',
	'Una serie más, un vaso de agua más, una hora más de sueño. Así se gana.',
	'El objetivo no es ser mejor que nadie, es ser mejor que ayer.',
	'Cumplir también los días malos es lo que te hace distinto.',
	'Lo que haces cada día importa más que lo que haces de vez en cuando.',
	'Confía en el proceso: los números llegan a quien no falla.',
	'Hoy no hace falta motivación, hace falta compromiso.',
	'Tu cuerpo escucha todo lo que haces. Dale motivos para cambiar.',
	'Empieza donde estás, usa lo que tienes, haz lo que puedas.',
	'Cada hábito cumplido es un voto por la persona que quieres ser.',
	'Descansa si lo necesitas, pero no abandones.',
	'El esfuerzo de hoy es la fuerza de mañana.',
	'Nadie llega lejos saltándose los días aburridos.',
	'Sé constante el tiempo suficiente para que se note.',
	'Tú decides si hoy es un día más o un día que suma.',
	'La meta se alcanza paso a paso. Hoy, da el tuyo.',
	'Termina el mes más fuerte de lo que lo empezaste.',
];

/** Fecha (yyyy-mm-dd) y hora local en la zona horaria dada. */
function localNow(tz: string) {
	const parts = Object.fromEntries(
		new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23' })
			.formatToParts(new Date())
			.map((p) => [p.type, p.value]),
	);
	return { date: `${parts.year}-${parts.month}-${parts.day}`, hour: Number(parts.hour), day: Number(parts.day) };
}

Deno.serve(async (req) => {
	if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
	if (req.method !== 'POST') return json({ error: 'Método no permitido' }, 405);

	const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });
	const cfg = Object.fromEntries(((await db.from('config_privada').select('clave,valor')).data || []).map((r) => [r.clave, r.valor]));
	if (!cfg.vapid_publica || !cfg.vapid_privada) return json({ error: 'Faltan claves VAPID' }, 500);
	webpush.setVapidDetails('mailto:xzenauto@gmail.com', cfg.vapid_publica, cfg.vapid_privada);

	const body = await req.json().catch(() => ({}));
	const fromCron = !!cfg.cron_secret && req.headers.get('x-cron-secret') === cfg.cron_secret;

	type Sub = { id: string; user_id: string; endpoint: string; p256dh: string; auth: string; tz: string; last_quote: string | null; last_habits: string | null };
	const send = async (s: Sub, payload: Record<string, unknown>) => {
		try {
			await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, JSON.stringify(payload), { TTL: 6 * 3600 });
			return true;
		} catch (err) {
			const code = (err as { statusCode?: number }).statusCode;
			if (code === 404 || code === 410) await db.from('gym_push_subs').delete().eq('id', s.id);
			else console.error('push', code, String(err));
			return false;
		}
	};

	// Notificación de prueba pedida desde la app por el propio atleta
	if (!fromCron) {
		if (body.action !== 'test') return json({ error: 'No autorizado' }, 401);
		const token = (req.headers.get('Authorization') ?? '').replace(/^Bearer\s+/i, '');
		const { data: who } = await db.auth.getUser(token);
		if (!who?.user) return json({ error: 'Sesión no válida' }, 401);
		const { data: subs } = await db.from('gym_push_subs').select('*').eq('user_id', who.user.id);
		let ok = 0;
		for (const s of (subs ?? []) as Sub[]) if (await send(s, { title: 'FitCoach', body: '¡Las notificaciones funcionan! Te avisaremos a las 8:00 y a las 21:00.', url: './' })) ok++;
		return json({ enviados: ok, dispositivos: subs?.length ?? 0 });
	}

	// Prueba lanzada desde el servidor (con el secreto del cron) a un atleta concreto
	if (body.action === 'test' && body.user_id) {
		const { data: subs } = await db.from('gym_push_subs').select('*').eq('user_id', body.user_id);
		const res: string[] = [];
		for (const s of (subs ?? []) as Sub[]) {
			try {
				await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, JSON.stringify({ title: 'FitCoach', body: '¡Las notificaciones funcionan! Te avisaremos a las 8:00 y a las 21:00.', url: './' }), { TTL: 3600 });
				res.push('ok');
			} catch (err) {
				const e = err as { statusCode?: number; body?: string };
				res.push(`error ${e.statusCode ?? ''} ${e.body ?? String(err)}`);
			}
		}
		return json({ dispositivos: subs?.length ?? 0, resultado: res });
	}

	// Envío programado
	const { data: subs } = await db.from('gym_push_subs').select('*');
	if (!subs?.length) return json({ enviados: 0 });
	const userIds = [...new Set(subs.map((s) => s.user_id))];
	const [{ data: profiles }, { data: plans }] = await Promise.all([
		db.from('gym_profiles').select('id,name').in('id', userIds),
		db.from('gym_plans').select('user_id,habits').in('user_id', userIds),
	]);
	const nameOf = new Map((profiles ?? []).map((p) => [p.id, String(p.name).split(' ')[0]]));
	const habitsOf = new Map((plans ?? []).map((p) => [p.user_id, (p.habits?.items ?? []) as { id: string; emoji: string; name: string }[]]));

	let frases = 0,
		recordatorios = 0;
	for (const s of subs as Sub[]) {
		const now = localNow(s.tz || 'Atlantic/Canary');
		if (now.hour === 8 && s.last_quote !== now.date) {
			const frase = FRASES[(now.day - 1) % FRASES.length];
			if (await send(s, { title: `Buenos días, ${nameOf.get(s.user_id) ?? ''} 💪`.replace(' ,', ','), body: frase, url: './' })) frases++;
			await db.from('gym_push_subs').update({ last_quote: now.date }).eq('id', s.id);
		}
		if (now.hour === 21 && s.last_habits !== now.date) {
			const items = habitsOf.get(s.user_id) ?? [];
			if (items.length) {
				const { data: log } = await db.from('gym_habit_logs').select('done').eq('user_id', s.user_id).eq('date', now.date).maybeSingle();
				const done: string[] = log?.done ?? [];
				const missing = items.filter((h) => !done.includes(h.id));
				if (missing.length) {
					const list = missing.map((h) => `${h.emoji} ${h.name}`).join(', ');
					const text = missing.length === items.length ? `Aún no has marcado tus hábitos de hoy: ${list}.` : `Te ${missing.length === 1 ? 'falta 1 hábito' : `faltan ${missing.length} hábitos`} por marcar: ${list}.`;
					if (await send(s, { title: 'Tus hábitos de hoy', body: text, url: './' })) recordatorios++;
				}
			}
			await db.from('gym_push_subs').update({ last_habits: now.date }).eq('id', s.id);
		}
	}
	return json({ frases, recordatorios });
});
