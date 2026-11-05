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

/** Último registro de un ejercicio (por id, o por nombre si cambió de día). */
export function lastLogOf(sessions: Session[], userId: string, exerciseId: string, name: string) {
	for (const s of sessionsFor(sessions, userId)) {
		const e =
			s.entries.find((x) => x.exerciseId === exerciseId && x.sets.length) ??
			s.entries.find((x) => x.name === name && x.sets.length);
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
