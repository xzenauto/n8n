import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { createSeed, emptyPlan } from './seed';
import type { DB, EquivalenceGroup, Measurement, Plan, Session, User } from './types';
import { hashPassword, uid } from './util';

/**
 * Capa de datos. Hoy guarda todo en el navegador (localStorage) para poder
 * usar la app sin servidor. Todas las operaciones pasan por aquí, así que
 * para pasar a Supabase solo hay que cambiar este archivo (ver supabase/README.md).
 */

const DB_KEY = 'fitcoach.db.v1';
const SESSION_KEY = 'fitcoach.session.v1';

function safeGet(key: string): string | null {
	try {
		return localStorage.getItem(key);
	} catch {
		return null;
	}
}
function safeSet(key: string, value: string | null) {
	try {
		if (value == null) localStorage.removeItem(key);
		else localStorage.setItem(key, value);
	} catch {
		/* almacenamiento no disponible: la app sigue funcionando en memoria */
	}
}

function loadDB(): DB {
	const raw = safeGet(DB_KEY);
	if (raw) {
		try {
			const db = JSON.parse(raw) as DB;
			if (db.version === 1) return db;
		} catch {
			/* ignore */
		}
	}
	return createSeed();
}

interface Store {
	db: DB;
	me: User | null;
	myPlan: Plan | undefined;
	login(email: string, password: string): Promise<string | null>;
	logout(): void;
	changePassword(current: string, next: string): Promise<string | null>;
	updateUser(id: string, patch: Partial<Omit<User, 'id' | 'passHash'>>): void;
	createUser(data: { name: string; email: string; phone: string; password: string; isAdmin: boolean; isAthlete: boolean; copyFrom?: string }): Promise<string | null>;
	setUserPassword(id: string, password: string): Promise<void>;
	deleteUser(id: string): void;
	planOf(userId: string): Plan | undefined;
	savePlan(plan: Plan): void;
	addSession(s: Omit<Session, 'id'>): Session;
	deleteSession(id: string): void;
	addMeasurement(m: Omit<Measurement, 'id'>): void;
	deleteMeasurement(id: string): void;
	saveEquivalences(groups: EquivalenceGroup[]): void;
	resetDemo(): void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
	const [db, setDb] = useState<DB>(loadDB);
	const [meId, setMeId] = useState<string | null>(() => safeGet(SESSION_KEY));

	useEffect(() => {
		safeSet(DB_KEY, JSON.stringify(db));
	}, [db]);
	useEffect(() => {
		safeSet(SESSION_KEY, meId);
	}, [meId]);

	const me = db.users.find((u) => u.id === meId) ?? null;
	const update = useCallback((fn: (d: DB) => DB) => setDb((d) => fn(structuredClone(d))), []);

	const store = useMemo<Store>(
		() => ({
			db,
			me,
			myPlan: me ? db.plans.find((p) => p.userId === me.id) : undefined,
			async login(email, password) {
				const u = db.users.find((x) => x.email.toLowerCase() === email.trim().toLowerCase());
				if (!u) return 'No existe ningún usuario con ese email';
				const h = await hashPassword(u.email, password);
				if (h !== u.passHash) return 'Contraseña incorrecta';
				setMeId(u.id);
				return null;
			},
			logout() {
				setMeId(null);
			},
			async changePassword(current, next) {
				if (!me) return 'Sin sesión';
				if ((await hashPassword(me.email, current)) !== me.passHash) return 'La contraseña actual no es correcta';
				if (next.length < 6) return 'La nueva contraseña debe tener al menos 6 caracteres';
				const h = await hashPassword(me.email, next);
				update((d) => {
					d.users.find((u) => u.id === me.id)!.passHash = h;
					return d;
				});
				return null;
			},
			updateUser(id, patch) {
				update((d) => {
					const u = d.users.find((x) => x.id === id);
					if (u) Object.assign(u, patch);
					return d;
				});
			},
			async createUser({ name, email, phone, password, isAdmin, isAthlete, copyFrom }) {
				const e = email.trim().toLowerCase();
				if (!name.trim() || !e) return 'Nombre y email son obligatorios';
				if (db.users.some((u) => u.email.toLowerCase() === e)) return 'Ya existe un usuario con ese email';
				if (password.length < 6) return 'La contraseña debe tener al menos 6 caracteres';
				const id = uid('u');
				const passHash = await hashPassword(e, password);
				update((d) => {
					d.users.push({ id, email: e, name: name.trim(), phone, passHash, isAdmin, isAthlete, createdAt: new Date().toISOString().slice(0, 10) });
					if (isAthlete) {
						const src = copyFrom ? d.plans.find((p) => p.userId === copyFrom) : undefined;
						d.plans.push(src ? { ...structuredClone(src), userId: id } : emptyPlan(id));
					}
					return d;
				});
				return null;
			},
			async setUserPassword(id, password) {
				const u = db.users.find((x) => x.id === id);
				if (!u) return;
				const h = await hashPassword(u.email, password);
				update((d) => {
					d.users.find((x) => x.id === id)!.passHash = h;
					return d;
				});
			},
			deleteUser(id) {
				update((d) => {
					d.users = d.users.filter((u) => u.id !== id);
					d.plans = d.plans.filter((p) => p.userId !== id);
					d.sessions = d.sessions.filter((s) => s.userId !== id);
					d.measurements = d.measurements.filter((m) => m.userId !== id);
					return d;
				});
			},
			planOf(userId) {
				return db.plans.find((p) => p.userId === userId);
			},
			savePlan(plan) {
				update((d) => {
					const i = d.plans.findIndex((p) => p.userId === plan.userId);
					if (i >= 0) d.plans[i] = plan;
					else d.plans.push(plan);
					return d;
				});
			},
			addSession(s) {
				const full = { ...s, id: uid('s') };
				update((d) => {
					d.sessions.push(full);
					return d;
				});
				return full;
			},
			deleteSession(id) {
				update((d) => {
					d.sessions = d.sessions.filter((s) => s.id !== id);
					return d;
				});
			},
			addMeasurement(m) {
				update((d) => {
					d.measurements.push({ ...m, id: uid('m') });
					return d;
				});
			},
			deleteMeasurement(id) {
				update((d) => {
					d.measurements = d.measurements.filter((m) => m.id !== id);
					return d;
				});
			},
			saveEquivalences(groups) {
				update((d) => {
					d.equivalences = groups;
					return d;
				});
			},
			resetDemo() {
				setDb(createSeed());
			},
		}),
		[db, me, update],
	);

	return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}

export function useStore() {
	const s = useContext(Ctx);
	if (!s) throw new Error('useStore fuera de StoreProvider');
	return s;
}
