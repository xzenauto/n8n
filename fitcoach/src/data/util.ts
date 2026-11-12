import { FOODS, type Food } from './foods';
import type { EquivalenceGroup, Meal, MealItem, Program, Session, TrainingDay } from './types';

export const uid = (p = 'id') => `${p}_${Math.random().toString(36).slice(2, 9)}${Date.now().toString(36).slice(-4)}`;

export function toISO(d: Date): string {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}

export const todayISO = () => toISO(new Date());

export function fromISO(s: string): Date {
	const [y, m, d] = s.split('-').map(Number);
	return new Date(y, m - 1, d);
}

/** 0 = lunes … 6 = domingo */
export const weekdayIndex = (d: Date) => (d.getDay() + 6) % 7;

export const WEEKDAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export const WEEKDAYS_SHORT = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

export function formatLong(d: Date): string {
	const s = d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
	return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatShort(iso: string): string {
	return fromISO(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

/** Interpreta pesos como "2*25", "1,75", "13*10". */
export function parseKg(v: string | undefined | null): number | null {
	if (v == null) return null;
	const s = String(v).trim().replace(',', '.');
	if (!s) return null;
	if (s.includes('*') || s.includes('x')) {
		const parts = s.split(/[*x]/).map((n) => Number(n.trim()));
		if (parts.some((n) => Number.isNaN(n))) return null;
		return parts.reduce((a, b) => a * b, 1);
	}
	const n = Number(s);
	return Number.isNaN(n) ? null : n;
}

// ---------- Alimentos ----------

const foodMap = new Map(FOODS.map((f) => [f.id, f]));
export const getFood = (id: string): Food | undefined => foodMap.get(id);

export function macrosOf(items: MealItem[]) {
	let kcal = 0,
		p = 0,
		c = 0,
		f = 0;
	for (const it of items) {
		const food = getFood(it.foodId);
		if (!food) continue;
		const k = it.grams / 100;
		kcal += food.kcal * k;
		p += food.p * k;
		c += food.c * k;
		f += food.f * k;
	}
	return { kcal: Math.round(kcal), p: Math.round(p), c: Math.round(c), f: Math.round(f) };
}

const MAIN_MACRO: Record<Food['group'], 'c' | 'p' | 'f' | 'kcal'> = {
	H: 'c',
	P: 'p',
	G: 'f',
	V: 'kcal',
};
const MACRO_LABEL = { c: 'hidratos', p: 'proteína', f: 'grasa', kcal: 'calorías' };

export interface EquivalenceResult {
	grams: number;
	method: 'tabla' | 'macro';
	detail: string;
}

/** Calcula cuántos gramos de `toId` equivalen a `grams` de `fromId`. */
export function equivalent(
	fromId: string,
	grams: number,
	toId: string,
	groups: EquivalenceGroup[],
): EquivalenceResult | null {
	// 1) Tabla de equivalencias del entrenador
	for (const g of groups) {
		const a = g.items.find((i) => i.foodId === fromId);
		const b = g.items.find((i) => i.foodId === toId);
		if (a && b && a.grams > 0) {
			return {
				grams: round5((grams * b.grams) / a.grams),
				method: 'tabla',
				detail: `${a.grams} g = ${b.grams} g (${g.name})`,
			};
		}
	}
	// 2) Cálculo por macro principal
	const from = getFood(fromId);
	const to = getFood(toId);
	if (!from || !to) return null;
	const macro = MAIN_MACRO[from.group];
	const target = (from[macro] * grams) / 100;
	if (!to[macro]) return null;
	return {
		grams: round5((target * 100) / to[macro]),
		method: 'macro',
		detail: `Mismos ${MACRO_LABEL[macro]}: ${Math.round(target * 10) / 10}${macro === 'kcal' ? ' kcal' : ' g'}`,
	};
}

const round5 = (n: number) => (n >= 20 ? Math.round(n / 5) * 5 : Math.round(n));

// ---------- Entreno ----------

export function dayFor(program: Program | undefined, date: Date): TrainingDay | null {
	if (!program) return null;
	const id = program.schedule[weekdayIndex(date)];
	return program.days.find((d) => d.id === id) ?? null;
}

export function nextTrainingFrom(program: Program | undefined, date: Date): { day: TrainingDay; date: Date } | null {
	if (!program) return null;
	for (let i = 1; i <= 7; i++) {
		const d = new Date(date);
		d.setDate(d.getDate() + i);
		const td = dayFor(program, d);
		if (td) return { day: td, date: d };
	}
	return null;
}

export function sessionsFor(sessions: Session[], userId: string) {
	return sessions.filter((s) => s.userId === userId).sort((a, b) => b.date.localeCompare(a.date));
}

/**
 * Último registro de un ejercicio EN ESE MISMO DÍA del plan. Un ejercicio repetido en otro
 * día (p. ej. Extensión de cuádriceps el Día 1 y el Día 4) lleva sus propios pesos y no se mezcla.
 * Se busca por el id del ejercicio y, si el entrenador lo sustituyó, por el nombre dentro del mismo día.
 */
export function lastLogOf(sessions: Session[], userId: string, exerciseId: string, name: string, dayId: string) {
	const sameDay = sessionsFor(sessions, userId).filter((s) => s.dayId === dayId);
	for (const s of sameDay) {
		const e = s.entries.find((x) => x.exerciseId === exerciseId && x.sets.length) ?? s.entries.find((x) => x.name === name && x.sets.length);
		if (e) return { session: s, entry: e };
	}
	return null;
}

export function bestSet(sets: { reps: string; kg: string }[]) {
	let best: { kg: number; reps: number } | null = null;
	for (const s of sets) {
		const kg = parseKg(s.kg);
		const reps = Number(s.reps);
		if (kg == null || !reps) continue;
		if (!best || kg > best.kg || (kg === best.kg && reps > best.reps)) best = { kg, reps };
	}
	return best;
}

// ---------- Dieta ----------

export function nextMeal(meals: Meal[], now: Date): { meal: Meal; tomorrow: boolean } | null {
	if (!meals.length) return null;
	const sorted = [...meals].sort((a, b) => a.time.localeCompare(b.time));
	const hm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
	const next = sorted.find((m) => m.time >= hm);
	return next ? { meal: next, tomorrow: false } : { meal: sorted[0], tomorrow: true };
}

// ---------- Objetivo de la serie (doble progresión) ----------

export function parseRange(reps: string): { min: number; max: number } | null {
	const nums = (reps.match(/\d+/g) ?? []).map(Number);
	if (!nums.length) return null;
	return { min: Math.min(...nums), max: Math.max(...nums) };
}

export interface SetTarget {
	kind: 'new' | 'reach' | 'more' | 'up';
	reps: string; // repeticiones objetivo para mostrar
	kg: string; // peso objetivo para mostrar
	tip: string; // frase corta para el atleta
}

/**
 * Trabajamos con rangos (p. ej. 6-8): si la semana pasada hiciste menos del tope,
 * el objetivo es hacer una repetición más con el mismo peso; si llegaste al tope,
 * toca subir el peso y volver a la parte baja del rango.
 */
export function setTarget(range: string, prev?: { reps: string; kg: string } | null): SetTarget {
	const r = parseRange(range);
	const reps = Number(prev?.reps);
	const kg = prev?.kg?.trim() || '';
	if (!r) return { kind: 'new', reps: '–', kg: kg || '–', tip: 'Apunta lo que hagas hoy' };
	if (!prev || !reps) return { kind: 'new', reps: range, kg: kg || '–', tip: `Elige un peso con el que hagas ${range} reps` };
	if (reps >= r.max)
		return { kind: 'up', reps: `${r.min}`, kg: kg ? `> ${kg}` : '↑', tip: `Llegaste al tope (${reps}). Sube el peso y busca ${r.min} reps` };
	if (reps < r.min) return { kind: 'reach', reps: `${r.min}`, kg: kg || '–', tip: `Mismo peso: llega a ${r.min} reps para entrar en el rango` };
	return { kind: 'more', reps: `${reps + 1}`, kg: kg || '–', tip: `Mismo peso y haz una más: ${reps + 1} reps` };
}


// ---------- Qué toca hoy (días fijos o rotativo) ----------

export interface UpNext {
	rotation: boolean;
	/** Entreno de hoy (en rotativo: la siguiente sesión pendiente, o la que ya se hizo hoy) */
	today: TrainingDay | null;
	todayDone: boolean;
	/** Lo siguiente: en días fijos, con su día de la semana; en rotativo, la sesión de después */
	next: { day: TrainingDay; label: string } | null;
	/** Último entreno hecho (rotativo) */
	last?: { day: TrainingDay; date: string };
}

export function upNext(program: Program | undefined, sessions: Session[], userId: string, now = new Date()): UpNext {
	const none: UpNext = { rotation: false, today: null, todayDone: false, next: null };
	if (!program || !program.days.length) return none;
	const todayIso = toISO(now);
	const mine = sessionsFor(sessions, userId);
	const doneTodaySession = mine.find((s) => s.date === todayIso);

	if (!program.rotation) {
		const today = dayFor(program, now);
		const nx = nextTrainingFrom(program, now);
		return { rotation: false, today, todayDone: !!doneTodaySession, next: nx ? { day: nx.day, label: WEEKDAYS[weekdayIndex(nx.date)] } : null };
	}

	const days = program.days;
	const after = (id?: string) => {
		const i = days.findIndex((d) => d.id === id);
		return days[(i + 1) % days.length] ?? days[0];
	};
	// Último entreno hecho de este programa (las sesiones vienen de más reciente a más antigua)
	const lastSession = mine.find((s) => days.some((d) => d.id === s.dayId));
	const last = lastSession ? { day: days.find((d) => d.id === lastSession.dayId)!, date: lastSession.date } : undefined;
	if (doneTodaySession && days.some((d) => d.id === doneTodaySession.dayId)) {
		const today = days.find((d) => d.id === doneTodaySession.dayId)!;
		return { rotation: true, today, todayDone: true, next: { day: after(today.id), label: 'Próxima sesión' }, last };
	}
	const today = lastSession ? after(lastSession.dayId) : days[0];
	return { rotation: true, today, todayDone: false, next: days.length > 1 ? { day: after(today.id), label: 'Después' } : null, last };
}
