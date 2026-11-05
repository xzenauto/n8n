import { createClient } from '@supabase/supabase-js';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { DB, EquivalenceGroup, Measurement, Plan, Session, User } from './types';

/**
 * Capa de datos sobre Supabase (proyecto "Guarderia Fito&Friends", tablas gym_*).
 * Los cambios se aplican primero en pantalla y luego se guardan; si el guardado
 * falla se avisa y se recargan los datos del servidor.
 */

// Se configuran en fitcoach/.env.local (no se sube al repo): ver .env.example
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const sb = createClient(SUPABASE_URL, SUPABASE_KEY, {
	// Clave propia: en xzenstudio.com conviven otras apps con el mismo proyecto.
	auth: { persistSession: true, autoRefreshToken: true, storageKey: 'gym-auth' },
});

const EMPTY: DB = { users: [], plans: [], sessions: [], measurements: [], equivalences: [] };

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
const toPlan = (r: Row): Plan => ({ userId: r.user_id, program: r.program, diet: r.diet });
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

async function must<T extends { error: { message: string } | null }>(p: PromiseLike<T>): Promise<T> {
	const r = await p;
	if (r.error) throw new Error(r.error.message);
	return r;
}

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
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
	const [db, setDb] = useState<DB>(EMPTY);
	const [meId, setMeId] = useState<string | null>(null);
	const [status, setStatus] = useState<Status>('loading');
	const [saveError, setSaveError] = useState<string | null>(null);
	const loadedFor = useRef<string | null>(null);

	const load = useCallback(async (userId: string) => {
		const [p, pl, s, m, e] = await Promise.all([
			sb.from('gym_profiles').select('*'),
			sb.from('gym_plans').select('*'),
			sb.from('gym_sessions').select('*').order('date', { ascending: false }),
			sb.from('gym_measurements').select('*').order('date'),
			sb.from('gym_equivalences').select('*').order('created_at'),
		]);
		const users = (p.data ?? []).map(toUser);
		if (!users.some((u) => u.id === userId)) {
			setDb(EMPTY);
			setStatus('noAccess');
			return;
		}
		setDb({
			users,
			plans: (pl.data ?? []).map(toPlan),
			sessions: (s.data ?? []).map(toSession),
			measurements: (m.data ?? []).map(toMeasurement),
			equivalences: (e.data ?? []).map((r) => ({ id: r.id, name: r.name, items: r.items ?? [] })),
		});
		setMeId(userId);
		setStatus('ready');
	}, []);

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
			load(uid).catch(() => setStatus('signedOut'));
		};
		sb.auth.getSession().then(({ data }) => handle(data.session?.user.id ?? null));
		const { data: sub } = sb.auth.onAuthStateChange((_e, session) => handle(session?.user.id ?? null));
		return () => sub.subscription.unsubscribe();
	}, [load]);

	const me = db.users.find((u) => u.id === meId) ?? null;

	/** Aplica el cambio en pantalla y lo guarda; si falla, avisa y recarga. */
	const apply = useCallback(
		(local: (d: DB) => DB, remote: () => Promise<unknown>) => {
			setDb((d) => local(structuredClone(d)));
			remote().catch((err: Error) => {
				setSaveError(`No se pudo guardar: ${err.message}. Revisa tu conexión.`);
				if (meId) load(meId);
			});
		},
		[load, meId],
	);

	const store = useMemo<Store>(
		() => ({
			status,
			db,
			me,
			myPlan: me ? db.plans.find((p) => p.userId === me.id) : undefined,
			saveError,
			clearSaveError: () => setSaveError(null),
			async login(email, password) {
				const { error } = await sb.auth.signInWithPassword({ email: email.trim().toLowerCase(), password });
				if (error) return error.message === 'Invalid login credentials' ? 'Email o contraseña incorrectos' : error.message;
				return null;
			},
			logout() {
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
				apply(
					(d) => {
						const u = d.users.find((x) => x.id === id);
						if (u) Object.assign(u, patch);
						return d;
					},
					() => must(sb.from('gym_profiles').update(row).eq('id', id)),
				);
			},
			async createUser({ name, email, phone, password, isAdmin, isAthlete, copyFrom }) {
				if (!name.trim() || !email.trim()) return 'Nombre y email son obligatorios';
				if (password.length < 6) return 'La contraseña debe tener al menos 6 caracteres';
				const src = copyFrom ? db.plans.find((p) => p.userId === copyFrom) : undefined;
				const plan = isAthlete
					? src
						? { program: src.program, diet: src.diet }
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
				apply(
					(d) => {
						const i = d.plans.findIndex((p) => p.userId === plan.userId);
						if (i >= 0) d.plans[i] = plan;
						else d.plans.push(plan);
						return d;
					},
					() => must(sb.from('gym_plans').upsert({ user_id: plan.userId, program: plan.program, diet: plan.diet, updated_at: new Date().toISOString() })),
				);
			},
			addSession(s) {
				const full: Session = { ...s, id: crypto.randomUUID() };
				apply(
					(d) => {
						d.sessions.unshift(full);
						return d;
					},
					() =>
						must(
							sb.from('gym_sessions').insert({
								id: full.id,
								user_id: full.userId,
								day_id: full.dayId,
								day_name: full.dayName,
								date: full.date,
								readiness: full.readiness,
								fatigue: full.fatigue,
								note: full.note,
								entries: full.entries,
							}),
						),
				);
				return full;
			},
			deleteSession(id) {
				apply(
					(d) => {
						d.sessions = d.sessions.filter((s) => s.id !== id);
						return d;
					},
					() => must(sb.from('gym_sessions').delete().eq('id', id)),
				);
			},
			addMeasurement(m) {
				const full: Measurement = { ...m, id: crypto.randomUUID() };
				apply(
					(d) => {
						d.measurements.push(full);
						return d;
					},
					() => must(sb.from('gym_measurements').insert(fromMeasurement(full))),
				);
			},
			deleteMeasurement(id) {
				apply(
					(d) => {
						d.measurements = d.measurements.filter((m) => m.id !== id);
						return d;
					},
					() => must(sb.from('gym_measurements').delete().eq('id', id)),
				);
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
					async () => {
						if (removed.length) await must(sb.from('gym_equivalences').delete().in('id', removed));
						if (fixed.length) await must(sb.from('gym_equivalences').upsert(fixed.map((g) => ({ id: g.id, name: g.name, items: g.items }))));
					},
				);
			},
		}),
		[status, db, me, meId, saveError, apply, load],
	);

	return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}

export function useStore() {
	const s = useContext(Ctx);
	if (!s) throw new Error('useStore fuera de StoreProvider');
	return s;
}
