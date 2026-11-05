import { createClient } from '@supabase/supabase-js';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { enqueue, flush, pending, type Op } from './outbox';
import type { DB, EquivalenceGroup, HabitLog, Habits, Measurement, Plan, Session, User } from './types';

/**
 * Capa de datos sobre Supabase (proyecto "Guarderia Fito&Friends", tablas gym_*).
 * Los cambios se aplican primero en pantalla y pasan por una cola de guardado
 * (outbox.ts) que se reintenta sola si no hay conexión.
 */

// Se configuran en fitcoach/.env.local (no se sube al repo): ver .env.example
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const sb = createClient(SUPABASE_URL, SUPABASE_KEY, {
	// Clave propia: en xzenstudio.com conviven otras apps con el mismo proyecto.
	auth: { persistSession: true, autoRefreshToken: true, storageKey: 'gym-auth' },
});

const EMPTY: DB = { users: [], plans: [], sessions: [], measurements: [], equivalences: [], habitLogs: [] };

type Row = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const toUser = (r: Row): User => ({
	id: r.id,
	email: r.email,
	name: r.name,
	phone: r.phone ?? '',
	isAdmin: r.is_admin,
	isAthlete: r.is_athlete,
	createdAt: String(r.created_at).slice(0, 10),
});
const toPlan = (r: Row): Plan => ({ userId: r.user_id, program: r.program, diet: r.diet, habits: r.habits ?? { goal: '', items: [] } });
const toSession = (r: Row): Session => ({
	id: r.id,
	userId: r.user_id,
	dayId: r.day_id,
	dayName: r.day_name,
	date: r.date,
	readiness: r.readiness,
	fatigue: r.fatigue,
	note: r.note ?? '',
	entries: r.entries ?? [],
});
const num = (v: unknown) => (v == null ? undefined : Number(v));
const toMeasurement = (r: Row): Measurement => ({
	id: r.id,
	userId: r.user_id,
	date: r.date,
	weight: num(r.weight),
	chest: num(r.chest),
	arm: num(r.arm),
	absHigh: num(r.abs_high),
	absLow: num(r.abs_low),
	leg: num(r.leg),
});
const fromMeasurement = (m: Measurement) => ({
	id: m.id,
	user_id: m.userId,
	date: m.date,
	weight: m.weight ?? null,
	chest: m.chest ?? null,
	arm: m.arm ?? null,
	abs_high: m.absHigh ?? null,
	abs_low: m.absLow ?? null,
	leg: m.leg ?? null,
});

async function adminCall(body: Record<string, unknown>): Promise<string | null> {
	const { data, error } = await sb.functions.invoke('gym-admin', { body });
	if (error) {
		try {
			const ctx = (error as { context?: Response }).context;
			const j = ctx ? await ctx.json() : null;
			return j?.error ?? error.message;
		} catch {
			return error.message;
		}
	}
	return data?.error ?? null;
}

export type Status = 'loading' | 'signedOut' | 'noAccess' | 'ready';

interface Store {
	status: Status;
	db: DB;
	me: User | null;
	myPlan: Plan | undefined;
	saveError: string | null;
	clearSaveError(): void;
	/** Cambios guardados en el móvil que aún no han llegado a Supabase */
	pendingCount: number;
	/** true mientras Supabase no tenga la tabla de hábitos: se guardan en el móvil */
	habitsLocal: boolean;
	login(email: string, password: string): Promise<string | null>;
	logout(): void;
	changePassword(current: string, next: string): Promise<string | null>;
	updateUser(id: string, patch: Partial<Omit<User, 'id'>>): void;
	createUser(data: { name: string; email: string; phone: string; password: string; isAdmin: boolean; isAthlete: boolean; copyFrom?: string }): Promise<string | null>;
	setUserPassword(id: string, password: string): Promise<string | null>;
	deleteUser(id: string): Promise<string | null>;
	planOf(userId: string): Plan | undefined;
	savePlan(plan: Plan): void;
	addSession(s: Omit<Session, 'id'>): Session;
	deleteSession(id: string): void;
	addMeasurement(m: Omit<Measurement, 'id'>): void;
	deleteMeasurement(id: string): void;
	saveEquivalences(groups: EquivalenceGroup[]): void;
	habitLogOf(userId: string, date: string): HabitLog | undefined;
	toggleHabit(userId: string, date: string, habitId: string): void;
}

// Hábitos por defecto (hoja "🧘Hábitos") mientras Supabase no tenga la columna habits.
export const DEFAULT_HABITS: Habits = {
	goal: 'Aumentar testosterona · reducir uso de móvil',
	items: [
		{ id: 'h1', emoji: '😴', name: 'Despertar y acostarte a la misma hora (también fines de semana)' },
		{ id: 'h2', emoji: '☕', name: 'Posponer el café 1 hora' },
		{ id: 'h3', emoji: '🛒', name: 'No hacer compra diaria' },
		{ id: 'h4', emoji: '📵', name: 'No usar el móvil la 1ª hora del día' },
		{ id: 'h5', emoji: '🚶', name: 'Cumplir los pasos' },
	],
};

const LOCAL_LOGS = 'gym-habitlogs-local.v1';
const CACHE = 'gym-cache.v1';
const LOCAL_HABITS = 'gym-habits-config.v1:';
function lsGet<T>(key: string, fallback: T): T {
	try {
		const v = localStorage.getItem(key);
		return v ? (JSON.parse(v) as T) : fallback;
	} catch {
		return fallback;
	}
}
function lsSet(key: string, value: unknown) {
	try {
		if (value == null) localStorage.removeItem(key);
		else localStorage.setItem(key, JSON.stringify(value));
	} catch {
		/* sin almacenamiento */
	}
}

const sessionRow = (s: Session) => ({
	id: s.id,
	user_id: s.userId,
	day_id: s.dayId,
	day_name: s.dayName,
	date: s.date,
	readiness: s.readiness,
	fatigue: s.fatigue,
	note: s.note,
	entries: s.entries,
});

/** Aplica sobre los datos del servidor los cambios que siguen en la cola. */
function mergePending(d: DB): DB {
	for (const op of pending()) {
		const r = op.row as Row | undefined;
		if (op.table === 'gym_sessions') {
			if (op.kind === 'upsert') d.sessions = [toSession(r!), ...d.sessions.filter((x) => x.id !== r!.id)];
			else d.sessions = d.sessions.filter((x) => x.id !== op.match!.id);
		} else if (op.table === 'gym_measurements') {
			if (op.kind === 'upsert') d.measurements = [...d.measurements.filter((x) => x.id !== r!.id), toMeasurement(r!)];
			else d.measurements = d.measurements.filter((x) => x.id !== op.match!.id);
		} else if (op.table === 'gym_habit_logs' && op.kind === 'upsert') {
			d.habitLogs = [...d.habitLogs.filter((x) => !(x.userId === r!.user_id && x.date === r!.date)), { userId: r!.user_id, date: r!.date, done: r!.done ?? [] }];
		} else if (op.table === 'gym_plans' && op.kind === 'upsert') {
			const i = d.plans.findIndex((p) => p.userId === r!.user_id);
			const prev = d.plans[i];
			const plan = { userId: r!.user_id, program: r!.program, diet: r!.diet, habits: r!.habits ?? prev?.habits ?? { goal: '', items: [] } };
			if (i >= 0) d.plans[i] = plan;
			else d.plans.push(plan);
		}
	}
	return d;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
	const [db, setDb] = useState<DB>(EMPTY);
	const [meId, setMeId] = useState<string | null>(null);
	const [status, setStatus] = useState<Status>('loading');
	const [saveError, setSaveError] = useState<string | null>(null);
	const [pendingCount, setPendingCount] = useState(pending().length);
	const [habitsLocal, setHabitsLocal] = useState(false);
	const hasHabitsCol = useRef(true);
	const loadedFor = useRef<string | null>(null);

	/** Intenta enviar lo pendiente. */
	const kick = useCallback(() => {
		flush(sb).then(({ dropped }) => {
			setPendingCount(pending().length);
			if (dropped.length) setSaveError(`Un cambio no se pudo guardar en el servidor: ${dropped[0]}`);
		});
	}, []);

	const load = useCallback(async (userId: string) => {
		const [p, pl, s, m, e, h] = await Promise.all([
			sb.from('gym_profiles').select('*'),
			sb.from('gym_plans').select('*'),
			sb.from('gym_sessions').select('*').order('date', { ascending: false }),
			sb.from('gym_measurements').select('*').order('date'),
			sb.from('gym_equivalences').select('*').order('created_at'),
			sb.from('gym_habit_logs').select('user_id,date,done'),
		]);
		if (p.error && !p.data) throw new Error(p.error.message);
		const users = (p.data ?? []).map(toUser);
		if (!users.some((u) => u.id === userId)) {
			setDb(EMPTY);
			setStatus('noAccess');
			return;
		}
		const planRows = pl.data ?? [];
		hasHabitsCol.current = planRows.length === 0 || 'habits' in planRows[0];
		const remoteHabits = !h.error;
		setHabitsLocal(!remoteHabits || !hasHabitsCol.current);

		const plans = planRows.map(toPlan).map((plan) =>
			hasHabitsCol.current ? plan : { ...plan, habits: lsGet<Habits | null>(LOCAL_HABITS + plan.userId, null) ?? DEFAULT_HABITS },
		);
		let habitLogs: HabitLog[] = remoteHabits ? (h.data ?? []).map((r) => ({ userId: r.user_id, date: r.date, done: r.done ?? [] })) : lsGet<HabitLog[]>(LOCAL_LOGS, []);

		// Cuando Supabase ya tiene la tabla, se suben las marcas que se hicieron en el móvil.
		if (remoteHabits) {
			const local = lsGet<HabitLog[]>(LOCAL_LOGS, []);
			for (const l of local) {
				enqueue({ key: `gym_habit_logs:${l.userId}:${l.date}`, table: 'gym_habit_logs', kind: 'upsert', row: { user_id: l.userId, date: l.date, done: l.done, updated_at: new Date().toISOString() } });
				habitLogs = [...habitLogs.filter((x) => !(x.userId === l.userId && x.date === l.date)), l];
			}
			if (local.length) lsSet(LOCAL_LOGS, null);
		}

		const fresh: DB = {
			users,
			plans,
			sessions: (s.data ?? []).map(toSession),
			measurements: (m.data ?? []).map(toMeasurement),
			equivalences: (e.data ?? []).map((r) => ({ id: r.id, name: r.name, items: r.items ?? [] })),
			habitLogs,
		};
		// Copia en el móvil para poder abrir la app sin cobertura
		lsSet(CACHE, { userId, db: fresh, hasHabitsCol: hasHabitsCol.current, habitsLocal: !remoteHabits || !hasHabitsCol.current });
		setDb(mergePending(fresh));
		setMeId(userId);
		setStatus('ready');
		kick();
	}, [kick]);

	useEffect(() => {
		const handle = (uid: string | null) => {
			if (!uid) {
				loadedFor.current = null;
				setMeId(null);
				setDb(EMPTY);
				setStatus('signedOut');
				return;
			}
			if (loadedFor.current === uid) return;
			loadedFor.current = uid;
			load(uid).catch(() => {
				// Sin conexión al abrir: se usan los últimos datos guardados y se reintenta
				loadedFor.current = null;
				const cache = lsGet<{ userId: string; db: DB; hasHabitsCol: boolean; habitsLocal: boolean } | null>(CACHE, null);
				if (cache && cache.userId === uid) {
					hasHabitsCol.current = cache.hasHabitsCol;
					setHabitsLocal(cache.habitsLocal);
					setDb(
						mergePending({
							...cache.db,
							habitLogs: cache.habitsLocal ? lsGet<HabitLog[]>(LOCAL_LOGS, []) : cache.db.habitLogs,
						}),
					);
					setMeId(uid);
					setStatus('ready');
					setSaveError('Sin conexión: estás viendo los últimos datos guardados en el móvil. Lo que apuntes se enviará al volver la cobertura.');
				} else setSaveError('Sin conexión con el servidor. Reintentando…');
				setTimeout(() => handle(uid), 8000);
			});
		};
		sb.auth.getSession().then(({ data }) => handle(data.session?.user.id ?? null));
		const { data: sub } = sb.auth.onAuthStateChange((_e, session) => handle(session?.user.id ?? null));
		return () => sub.subscription.unsubscribe();
	}, [load]);

	// Reintentos: al recuperar la conexión, al volver a la app y cada 20 s si queda algo pendiente.
	useEffect(() => {
		const onVisible = () => document.visibilityState === 'visible' && kick();
		window.addEventListener('online', kick);
		document.addEventListener('visibilitychange', onVisible);
		const t = setInterval(() => pending().length && kick(), 20000);
		return () => {
			window.removeEventListener('online', kick);
			document.removeEventListener('visibilitychange', onVisible);
			clearInterval(t);
		};
	}, [kick]);

	useEffect(() => {
		if (saveError?.startsWith('Sin conexión') && status === 'ready' && loadedFor.current) setSaveError(null);
	}, [status, saveError, db]);

	const me = db.users.find((u) => u.id === meId) ?? null;

	/** Aplica el cambio en pantalla, lo deja en la cola y la intenta enviar. */
	const apply = useCallback(
		(local: (d: DB) => DB, ops: Omit<Op, 'at'>[]) => {
			setDb((d) => local(structuredClone(d)));
			ops.forEach(enqueue);
			setPendingCount(pending().length);
			kick();
		},
		[kick],
	);

	const store = useMemo<Store>(
		() => ({
			status,
			db,
			me,
			myPlan: me ? db.plans.find((p) => p.userId === me.id) : undefined,
			saveError,
			clearSaveError: () => setSaveError(null),
			pendingCount,
			habitsLocal,
			async login(email, password) {
				const { error } = await sb.auth.signInWithPassword({ email: email.trim().toLowerCase(), password });
				if (error) return error.message === 'Invalid login credentials' ? 'Email o contraseña incorrectos' : error.message;
				return null;
			},
			logout() {
				lsSet(CACHE, null);
				sb.auth.signOut();
			},
			async changePassword(current, next) {
				if (!me) return 'Sin sesión';
				if (next.length < 6) return 'La nueva contraseña debe tener al menos 6 caracteres';
				const check = await sb.auth.signInWithPassword({ email: me.email, password: current });
				if (check.error) return 'La contraseña actual no es correcta';
				const { error } = await sb.auth.updateUser({ password: next });
				return error ? error.message : null;
			},
			updateUser(id, patch) {
				const row: Row = {};
				if (patch.name !== undefined) row.name = patch.name;
				if (patch.phone !== undefined) row.phone = patch.phone;
				if (patch.isAdmin !== undefined) row.is_admin = patch.isAdmin;
				if (patch.isAthlete !== undefined) row.is_athlete = patch.isAthlete;
				setDb((d) => {
					const c = structuredClone(d);
					const u = c.users.find((x) => x.id === id);
					if (u) Object.assign(u, patch);
					return c;
				});
				sb.from('gym_profiles')
					.update(row)
					.eq('id', id)
					.then(({ error }) => error && setSaveError(`No se pudo guardar el perfil: ${error.message}`));
			},
			async createUser({ name, email, phone, password, isAdmin, isAthlete, copyFrom }) {
				if (!name.trim() || !email.trim()) return 'Nombre y email son obligatorios';
				if (password.length < 6) return 'La contraseña debe tener al menos 6 caracteres';
				const src = copyFrom ? db.plans.find((p) => p.userId === copyFrom) : undefined;
				const plan = isAthlete
					? src
						? { program: src.program, diet: src.diet, ...(hasHabitsCol.current ? { habits: src.habits } : {}) }
						: {
								program: { name: 'Nuevo programa', days: [], schedule: [null, null, null, null, null, null, null], cardio: [] },
								diet: { kcal: 0, protein: 0, carbs: 0, fat: 0, meals: [] },
							}
					: null;
				const err = await adminCall({ action: 'create', name, email, phone, password, isAdmin, isAthlete, plan });
				if (!err && meId) await load(meId);
				return err;
			},
			async setUserPassword(id, password) {
				return adminCall({ action: 'password', id, password });
			},
			async deleteUser(id) {
				const err = await adminCall({ action: 'delete', id });
				if (!err && meId) await load(meId);
				return err;
			},
			planOf(userId) {
				return db.plans.find((p) => p.userId === userId);
			},
			savePlan(plan) {
				const row: Row = { user_id: plan.userId, program: plan.program, diet: plan.diet, updated_at: new Date().toISOString() };
				if (hasHabitsCol.current) row.habits = plan.habits;
				else lsSet(LOCAL_HABITS + plan.userId, plan.habits);
				apply(
					(d) => {
						const i = d.plans.findIndex((p) => p.userId === plan.userId);
						if (i >= 0) d.plans[i] = plan;
						else d.plans.push(plan);
						return d;
					},
					[{ key: `gym_plans:${plan.userId}`, table: 'gym_plans', kind: 'upsert', row }],
				);
			},
			addSession(s) {
				const full: Session = { ...s, id: crypto.randomUUID() };
				apply(
					(d) => {
						d.sessions.unshift(full);
						return d;
					},
					[{ key: `gym_sessions:${full.id}`, table: 'gym_sessions', kind: 'upsert', row: sessionRow(full) }],
				);
				return full;
			},
			deleteSession(id) {
				apply(
					(d) => {
						d.sessions = d.sessions.filter((s) => s.id !== id);
						return d;
					},
					[{ key: `gym_sessions:${id}`, table: 'gym_sessions', kind: 'delete', match: { id } }],
				);
			},
			addMeasurement(m) {
				const full: Measurement = { ...m, id: crypto.randomUUID() };
				apply(
					(d) => {
						d.measurements.push(full);
						return d;
					},
					[{ key: `gym_measurements:${full.id}`, table: 'gym_measurements', kind: 'upsert', row: fromMeasurement(full) }],
				);
			},
			deleteMeasurement(id) {
				apply(
					(d) => {
						d.measurements = d.measurements.filter((m) => m.id !== id);
						return d;
					},
					[{ key: `gym_measurements:${id}`, table: 'gym_measurements', kind: 'delete', match: { id } }],
				);
			},
			habitLogOf(userId, date) {
				return db.habitLogs.find((l) => l.userId === userId && l.date === date);
			},
			toggleHabit(userId, date, habitId) {
				const cur = db.habitLogs.find((l) => l.userId === userId && l.date === date)?.done ?? [];
				const done = cur.includes(habitId) ? cur.filter((x) => x !== habitId) : [...cur, habitId];
				const local = (d: DB) => {
					const l = d.habitLogs.find((x) => x.userId === userId && x.date === date);
					if (l) l.done = done;
					else d.habitLogs.push({ userId, date, done });
					return d;
				};
				if (habitsLocal) {
					// Sin tabla en Supabase todavía: se guarda en el móvil y se subirá después.
					const logs = local({ ...EMPTY, habitLogs: lsGet<HabitLog[]>(LOCAL_LOGS, []) }).habitLogs;
					lsSet(LOCAL_LOGS, logs);
					setDb((d) => local(structuredClone(d)));
					return;
				}
				apply(local, [
					{ key: `gym_habit_logs:${userId}:${date}`, table: 'gym_habit_logs', kind: 'upsert', row: { user_id: userId, date, done, updated_at: new Date().toISOString() } },
				]);
			},
			saveEquivalences(groups) {
				const isUuid = (s: string) => /^[0-9a-f-]{36}$/i.test(s);
				const fixed = groups.map((g) => (isUuid(g.id) ? g : { ...g, id: crypto.randomUUID() }));
				const keep = new Set(fixed.map((g) => g.id));
				const removed = db.equivalences.filter((g) => !keep.has(g.id)).map((g) => g.id);
				apply(
					(d) => {
						d.equivalences = fixed;
						return d;
					},
					[
						...removed.map((id) => ({ key: `gym_equivalences:${id}`, table: 'gym_equivalences', kind: 'delete' as const, match: { id } })),
						...fixed.map((g) => ({ key: `gym_equivalences:${g.id}`, table: 'gym_equivalences', kind: 'upsert' as const, row: { id: g.id, name: g.name, items: g.items } })),
					],
				);
			},
		}),
		[status, db, me, meId, saveError, pendingCount, habitsLocal, apply, load],
	);

	return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}

export function useStore() {
	const s = useContext(Ctx);
	if (!s) throw new Error('useStore fuera de StoreProvider');
	return s;
}
