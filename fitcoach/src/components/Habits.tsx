import type { Habit, HabitLog } from '../data/types';
import { toISO } from '../data/util';

/** Un color por anillo, del exterior al interior (como los anillos de actividad). */
export const HABIT_COLORS = ['#ff3b5c', '#8ce04a', '#4cc9f0', '#ffd966', '#b98cff'];

export const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

export const daysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
const iso = (y: number, m: number, d: number) => toISO(new Date(y, m, d));

export interface HabitStat {
	habit: Habit;
	color: string;
	done: number; // días cumplidos en el mes
	elapsed: number; // días del mes transcurridos (hasta hoy)
	pct: number; // done / elapsed
	streak: number; // racha actual (días seguidos hasta hoy, o hasta ayer si hoy aún no)
	best: number; // mejor racha del mes
}

export function monthStats(habits: Habit[], logs: HabitLog[], y: number, m: number, today = new Date()): HabitStat[] {
	const map = new Map(logs.map((l) => [l.date, l.done]));
	const total = daysInMonth(y, m);
	const isCurrent = today.getFullYear() === y && today.getMonth() === m;
	const isPast = new Date(y, m + 1, 1) <= today;
	const elapsed = isCurrent ? today.getDate() : isPast ? total : 0;
	return habits.map((habit, i) => {
		let done = 0,
			run = 0,
			best = 0;
		for (let d = 1; d <= elapsed; d++) {
			if (map.get(iso(y, m, d))?.includes(habit.id)) {
				done++;
				run++;
				best = Math.max(best, run);
			} else run = 0;
		}
		// Racha actual hacia atrás desde hoy (sin cortar si hoy aún no está marcado)
		let streak = 0;
		const start = new Date(today);
		if (!map.get(toISO(start))?.includes(habit.id)) start.setDate(start.getDate() - 1);
		for (let k = 0; k < 400; k++) {
			const dd = new Date(start);
			dd.setDate(start.getDate() - k);
			if (map.get(toISO(dd))?.includes(habit.id)) streak++;
			else break;
		}
		return { habit, color: HABIT_COLORS[i % HABIT_COLORS.length], done, elapsed, pct: elapsed ? done / elapsed : 0, streak, best };
	});
}

const polar = (r: number, a: number) => [r * Math.cos(a), r * Math.sin(a)] as const;

function arc(r: number, a0: number, a1: number) {
	const [x0, y0] = polar(r, a0);
	const [x1, y1] = polar(r, a1);
	const large = a1 - a0 > Math.PI ? 1 : 0;
	return `M${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1}`;
}

/** Anillos concéntricos estilo "Actividad": progreso del mes de cada hábito. */
export function HabitRings({ stats, size = 170 }: { stats: HabitStat[]; size?: number }) {
	const n = Math.max(1, stats.length);
	const outer = 96;
	const gap = 3;
	const w = Math.min(16, (outer - 26) / n - gap);
	const top = -Math.PI / 2;
	return (
		<svg viewBox="-100 -100 200 200" width={size} height={size} role="img" aria-label="Progreso de hábitos del mes">
			{stats.map((s, i) => {
				const r = outer - w / 2 - i * (w + gap);
				const p = Math.min(1, s.pct);
				return (
					<g key={s.habit.id}>
						<circle r={r} fill="none" stroke={s.color} strokeOpacity={0.2} strokeWidth={w} />
						{p >= 0.999 ? (
							<circle r={r} fill="none" stroke={s.color} strokeWidth={w} />
						) : p > 0 ? (
							<path d={arc(r, top, top + p * 2 * Math.PI)} fill="none" stroke={s.color} strokeWidth={w} strokeLinecap="round" />
						) : null}
						<text x={0} y={-r} textAnchor="middle" dominantBaseline="central" fontSize={w * 0.7}>
							{s.habit.emoji || '•'}
						</text>
					</g>
				);
			})}
		</svg>
	);
}

/**
 * Rueda mensual: cada sector es un día (empieza arriba y gira en sentido horario)
 * y cada anillo es un hábito (el 1º por fuera).
 */
export function HabitWheel({
	habits,
	logs,
	year,
	month,
	onToggle,
}: {
	habits: Habit[];
	logs: HabitLog[];
	year: number;
	month: number;
	onToggle?: (date: string, habitId: string) => void;
}) {
	const total = daysInMonth(year, month);
	const map = new Map(logs.map((l) => [l.date, l.done]));
	const todayISO = toISO(new Date());
	const inner = 46;
	const ringW = Math.min(24, (150 - inner) / Math.max(1, habits.length));
	const outer = inner + ringW * habits.length;
	const step = (2 * Math.PI) / total;
	const top = -Math.PI / 2;

	const sector = (r0: number, r1: number, a0: number, a1: number) => {
		const [x0, y0] = polar(r1, a0);
		const [x1, y1] = polar(r1, a1);
		const [x2, y2] = polar(r0, a1);
		const [x3, y3] = polar(r0, a0);
		return `M${x0},${y0} A${r1},${r1} 0 0 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 0 0 ${x3},${y3} Z`;
	};

	const cells = [];
	for (let d = 1; d <= total; d++) {
		const date = iso(year, month, d);
		const future = date > todayISO;
		const done = map.get(date) ?? [];
		const a0 = top + (d - 1) * step;
		const a1 = a0 + step;
		habits.forEach((h, i) => {
			const r1 = outer - i * ringW;
			const r0 = r1 - ringW;
			const on = done.includes(h.id);
			cells.push(
				<path
					key={`${d}-${h.id}`}
					d={sector(r0, r1, a0, a1)}
					style={{
						fill: on ? HABIT_COLORS[i % HABIT_COLORS.length] : future ? '#f7f7f7' : '#d9d9d9',
						stroke: 'rgba(0,0,0,0.3)',
						strokeWidth: 0.6,
						cursor: onToggle && !future ? 'pointer' : 'default',
					}}
					onClick={onToggle && !future ? () => onToggle(date, h.id) : undefined}
				>
					<title>
						{d} {MONTHS[month]} · {h.name}: {on ? 'cumplido' : future ? 'por llegar' : 'sin cumplir'}
					</title>
				</path>,
			);
		});
		const [tx, ty] = polar(outer + 11, a0 + step / 2);
		cells.push(
			<text
				key={`n${d}`}
				x={tx}
				y={ty}
				textAnchor="middle"
				dominantBaseline="central"
				fontSize={8.5}
				fontWeight={date === todayISO ? 900 : 600}
				style={{ fill: date === todayISO ? '#111' : '#7a7a7a' }}
			>
				{d}
			</text>,
		);
		if (date === todayISO) {
			cells.push(<path key="today" d={sector(inner, outer, a0, a1)} style={{ fill: 'none', stroke: '#111', strokeWidth: 2, pointerEvents: 'none' }} />);
		}
	}

	const stats = monthStats(habits, logs, year, month);
	const global = stats.length ? stats.reduce((a, s) => a + s.done, 0) / Math.max(1, stats.reduce((a, s) => a + s.elapsed, 0)) : 0;

	return (
		<svg viewBox="-175 -175 350 350" className="wheel" role="img" aria-label={`Rueda de hábitos de ${MONTHS[month]}`}>
			{cells}
			<text x={0} y={-6} textAnchor="middle" fontSize={26} fontWeight={900} style={{ fill: '#111' }}>
				{Math.round(global * 100)}%
			</text>
			<text x={0} y={14} textAnchor="middle" fontSize={9} fontWeight={700} letterSpacing="0.06em" style={{ fill: '#7a7a7a' }}>
				{MONTHS[month].toUpperCase()}
			</text>
		</svg>
	);
}
