/**
 * Entreno a medias. Se guarda en el móvil por usuario (no por día), para que
 * empezar otro día nunca borre en silencio lo que ya estaba apuntado.
 */
import type { RestState } from '../components/RestTimer';
import type { SetLog } from './types';

export interface Draft {
	dayId: string;
	readiness: number | null;
	fatigue: number | null;
	note: string;
	logs: SetLog[][];
	stepIdx: number;
	rest?: RestState;
	updatedAt?: number;
}

const OLD_KEY = 'fitcoach.draft.v1';
const key = (userId: string) => `axis.draft.v2:${userId}`;

export function getDraft(userId: string): Draft | null {
	try {
		const raw = localStorage.getItem(key(userId));
		if (raw) return JSON.parse(raw) as Draft;
		// Borrador de la versión anterior (una sola clave para todo el móvil): se adopta
		const old = localStorage.getItem(OLD_KEY);
		if (old) {
			localStorage.setItem(key(userId), old);
			localStorage.removeItem(OLD_KEY);
			return JSON.parse(old) as Draft;
		}
	} catch {
		/* sin almacenamiento */
	}
	return null;
}

export function setDraft(userId: string, d: Draft | null) {
	try {
		if (d) localStorage.setItem(key(userId), JSON.stringify({ ...d, updatedAt: Date.now() }));
		else localStorage.removeItem(key(userId));
	} catch {
		/* sin almacenamiento */
	}
}

/** Series con algo apuntado (reps o kg). */
export const loggedSets = (d: Draft) => d.logs.flat().filter((s) => s.reps.trim() || s.kg.trim()).length;
