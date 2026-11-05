// FitCoach · operaciones de administrador sobre usuarios (necesitan la service role).
// Solo la puede usar un usuario con gym_profiles.is_admin = true.
import { createClient } from 'npm:@supabase/supabase-js@2.45.4';

const cors = {
	'Access-Control-Allow-Origin': '*',
	'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
	'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

const json = (body: unknown, status = 200) =>
	new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
	if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
	if (req.method !== 'POST') return json({ error: 'Método no permitido' }, 405);

	const url = Deno.env.get('SUPABASE_URL')!;
	const admin = createClient(url, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });

	// ¿Quién llama?
	const token = (req.headers.get('Authorization') ?? '').replace(/^Bearer\s+/i, '');
	const { data: who, error: whoErr } = await admin.auth.getUser(token);
	if (whoErr || !who?.user) return json({ error: 'Sesión no válida' }, 401);
	const { data: me } = await admin.from('gym_profiles').select('is_admin').eq('id', who.user.id).maybeSingle();
	if (!me?.is_admin) return json({ error: 'Solo un administrador puede hacer esto' }, 403);

	let body: Record<string, unknown>;
	try {
		body = await req.json();
	} catch {
		return json({ error: 'Petición no válida' }, 400);
	}

	try {
		switch (body.action) {
			case 'create': {
				const email = String(body.email ?? '').trim().toLowerCase();
				const password = String(body.password ?? '');
				const name = String(body.name ?? '').trim();
				if (!email || !name) return json({ error: 'Nombre y email son obligatorios' }, 400);
				if (password.length < 6) return json({ error: 'La contraseña debe tener al menos 6 caracteres' }, 400);

				// Si el email ya existe en Auth (p. ej. usuario de otra app), se reutiliza.
				let userId: string | null = null;
				const { data: created, error } = await admin.auth.admin.createUser({ email, password, email_confirm: true, user_metadata: { name } });
				if (error) {
					const { data: list } = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 });
					const existing = list?.users.find((u) => u.email?.toLowerCase() === email);
					if (!existing) return json({ error: error.message }, 400);
					const { data: already } = await admin.from('gym_profiles').select('id').eq('id', existing.id).maybeSingle();
					if (already) return json({ error: 'Ya existe un usuario con ese email' }, 400);
					userId = existing.id;
					await admin.auth.admin.updateUserById(userId, { password });
				} else userId = created.user.id;

				const { error: pErr } = await admin.from('gym_profiles').insert({
					id: userId,
					email,
					name,
					phone: String(body.phone ?? ''),
					is_admin: !!body.isAdmin,
					is_athlete: !!body.isAthlete,
				});
				if (pErr) return json({ error: pErr.message }, 400);
				if (body.isAthlete && body.plan && typeof body.plan === 'object') {
					const plan = body.plan as { program: unknown; diet: unknown };
					const { error: plErr } = await admin.from('gym_plans').insert({ user_id: userId, program: plan.program, diet: plan.diet });
					if (plErr) return json({ error: plErr.message }, 400);
				}
				return json({ id: userId });
			}
			case 'password': {
				const id = String(body.id ?? '');
				const password = String(body.password ?? '');
				if (password.length < 6) return json({ error: 'La contraseña debe tener al menos 6 caracteres' }, 400);
				const { data: target } = await admin.from('gym_profiles').select('id').eq('id', id).maybeSingle();
				if (!target) return json({ error: 'Usuario no encontrado' }, 404);
				const { error } = await admin.auth.admin.updateUserById(id, { password });
				if (error) return json({ error: error.message }, 400);
				return json({ ok: true });
			}
			case 'delete': {
				const id = String(body.id ?? '');
				if (id === who.user.id) return json({ error: 'No puedes borrarte a ti mismo' }, 400);
				// Solo se borran los datos de FitCoach; la cuenta de Auth puede usarse en otras apps del proyecto.
				const { error } = await admin.from('gym_profiles').delete().eq('id', id);
				if (error) return json({ error: error.message }, 400);
				return json({ ok: true });
			}
			default:
				return json({ error: 'Acción desconocida' }, 400);
		}
	} catch (e) {
		return json({ error: e instanceof Error ? e.message : 'Error inesperado' }, 500);
	}
});
