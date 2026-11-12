import { useMemo, useState } from 'react';
import { EditHabitsButton } from '../components/EditHabits';
import { HabitWheel, MONTHS, monthStats } from '../components/Habits';
import { ask, LineChart, Sheet, TopBar } from '../components/ui';
import { useStore } from '../data/store';
import type { Measurement } from '../data/types';
import { bestSet, formatShort, sessionsFor, todayISO } from '../data/util';

const MEASURES: { key: keyof Measurement; label: string; unit: string }[] = [
	{ key: 'weight', label: 'Peso', unit: ' kg' },
	{ key: 'chest', label: 'Pecho', unit: ' cm' },
	{ key: 'arm', label: 'Brazo', unit: ' cm' },
	{ key: 'absHigh', label: 'Abdomen alto', unit: ' cm' },
	{ key: 'absLow', label: 'Abdomen bajo', unit: ' cm' },
	{ key: 'leg', label: 'Pierna', unit: ' cm' },
];

export default function Progress({ userId }: { userId?: string }) {
	const { me } = useStore();
	const [tab, setTab] = useState<'habits' | 'weight' | 'measures' | 'training'>('habits');
	const uid = userId ?? me!.id;
	return (
		<>
			{!userId && <TopBar title="Progreso" />}
			<div className="tabs">
				<button className={tab === 'habits' ? 'on' : ''} onClick={() => setTab('habits')}>
					Hábitos
				</button>
				<button className={tab === 'weight' ? 'on' : ''} onClick={() => setTab('weight')}>
					Peso
				</button>
				<button className={tab === 'measures' ? 'on' : ''} onClick={() => setTab('measures')}>
					Medidas
				</button>
				<button className={tab === 'training' ? 'on' : ''} onClick={() => setTab('training')}>
					Por ejercicio
				</button>
			</div>
			{tab === 'habits' && <HabitsProgress userId={uid} editable={!userId || userId === me!.id} />}
			{tab === 'weight' && <Metric userId={uid} only="weight" />}
			{tab === 'measures' && <Metric userId={uid} />}
			{tab === 'training' && <ExerciseProgress userId={uid} />}
		</>
	);
}

function Metric({ userId, only }: { userId: string; only?: 'weight' }) {
	const { db, addMeasurement, deleteMeasurement } = useStore();
	const options = only ? MEASURES.filter((m) => m.key === 'weight') : MEASURES.filter((m) => m.key !== 'weight');
	const [key, setKey] = useState(options[0].key);
	const [adding, setAdding] = useState(false);
	const meta = MEASURES.find((m) => m.key === key)!;
	const rows = db.measurements.filter((m) => m.userId === userId).sort((a, b) => a.date.localeCompare(b.date));
	const pts = rows.filter((r) => typeof r[key] === 'number').map((r) => ({ label: formatShort(r.date), value: r[key] as number }));
	const first = pts[0]?.value;
	const last = pts[pts.length - 1]?.value;
	const diff = first != null && last != null ? Math.round((last - first) * 10) / 10 : null;

	return (
		<>
			{!only && (
				<div className="tabs">
					{options.map((o) => (
						<button key={o.key} className={o.key === key ? 'on' : ''} onClick={() => setKey(o.key)}>
							{o.label}
						</button>
					))}
				</div>
			)}
			<div className="card">
				<div className="card-head">
					{meta.label}
					{diff != null && pts.length > 1 && (
						<span className={`pill ${diff <= 0 ? 'green' : 'yellow'}`}>
							{diff > 0 ? '+' : ''}
							{diff}
							{meta.unit}
						</span>
					)}
				</div>
				<div className="card-body">
					{last != null && (
						<div style={{ fontSize: 30, fontWeight: 900, marginBottom: 4 }}>
							{last}
							<span style={{ fontSize: 15, color: 'var(--ink-3)' }}>{meta.unit}</span>
						</div>
					)}
					<LineChart points={pts} unit={meta.unit} />
				</div>
			</div>
			<button className="btn" onClick={() => setAdding(true)}>
				+ Añadir registro
			</button>

			<div className="section-label">Registros</div>
			<div className="card">
				{rows.length === 0 && <div className="empty">Añade tu primer registro de peso y medidas</div>}
				{[...rows].reverse().map((r) => (
					<div className="row" key={r.id}>
						<div className="grow">
							<div className="name">{formatShort(r.date)}</div>
							<div className="muted">
								{MEASURES.filter((m) => typeof r[m.key] === 'number')
									.map((m) => `${m.label} ${r[m.key]}`)
									.join(' · ')}
							</div>
						</div>
						<button className="icon-btn" onClick={async () => (await ask('¿Borrar registro?')) && deleteMeasurement(r.id)} aria-label="Borrar">
							🗑
						</button>
					</div>
				))}
			</div>
			{adding && (
				<AddMeasurement
					onClose={() => setAdding(false)}
					onSave={(m) => {
						addMeasurement({ ...m, userId });
						setAdding(false);
					}}
				/>
			)}
		</>
	);
}

function AddMeasurement({ onClose, onSave }: { onClose: () => void; onSave: (m: Omit<Measurement, 'id' | 'userId'>) => void }) {
	const [date, setDate] = useState(todayISO());
	const [vals, setVals] = useState<Record<string, string>>({});
	const save = () => {
		const m: Omit<Measurement, 'id' | 'userId'> = { date };
		for (const { key } of MEASURES) {
			const n = Number((vals[key] || '').replace(',', '.'));
			if (vals[key] && !Number.isNaN(n)) (m as Record<string, unknown>)[key] = n;
		}
		onSave(m);
	};
	return (
		<Sheet title="Nuevo registro" onClose={onClose}>
			<label className="field">
				<span>Fecha</span>
				<input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
			</label>
			<div className="grid-2">
				{MEASURES.map((m) => (
					<label className="field" key={m.key}>
						<span>
							{m.label} ({m.unit.trim()})
						</span>
						<input inputMode="decimal" value={vals[m.key] ?? ''} onChange={(e) => setVals((v) => ({ ...v, [m.key]: e.target.value }))} />
					</label>
				))}
			</div>
			<button className="btn" onClick={save}>
				Guardar
			</button>
		</Sheet>
	);
}

function ExerciseProgress({ userId }: { userId: string }) {
	const { db } = useStore();
	const sessions = sessionsFor(db.sessions, userId).reverse();
	const [sel, setSel] = useState<string | null>(null);

	const byExercise = useMemo(() => {
		// Un ejercicio repetido en varios días se sigue por separado en cada día (cada uno con sus pesos)
		const map = new Map<string, { key: string; name: string; day: string; points: { date: string; kg: number; reps: number }[] }>();
		const repeated = new Set<string>();
		const daysByName = new Map<string, Set<string>>();
		for (const s of sessions)
			for (const e of s.entries) {
				if (!daysByName.has(e.name)) daysByName.set(e.name, new Set());
				daysByName.get(e.name)!.add(s.dayId);
			}
		daysByName.forEach((d, n) => d.size > 1 && repeated.add(n));
		for (const s of sessions)
			for (const e of s.entries) {
				const b = bestSet(e.sets);
				if (!b) continue;
				const k = `${s.dayId}|${e.name}`;
				const day = repeated.has(e.name) ? s.dayName.split('·')[0].trim() : '';
				if (!map.has(k)) map.set(k, { key: k, name: e.name, day, points: [] });
				map.get(k)!.points.push({ date: s.date, ...b });
			}
		return [...map.values()].sort((a, b) => a.name.localeCompare(b.name) || a.day.localeCompare(b.day));
	}, [sessions]);

	const current = byExercise.find((e) => e.key === sel);
	if (current) {
		const pts = current.points.map((p) => ({ label: formatShort(p.date), value: p.kg }));
		return (
			<>
				<button className="back" onClick={() => setSel(null)}>
					‹ Todos los ejercicios
				</button>
				<div className="card">
					<div className="card-head">
						{current.name}
						{current.day && <span className="pill">{current.day}</span>}
					</div>
					<div className="card-body">
						<div className="muted" style={{ marginBottom: 6 }}>
							Mejor serie de cada sesión (kg)
						</div>
						<LineChart points={pts} unit=" kg" />
					</div>
					{[...current.points].reverse().map((p, i, arr) => {
						const prev = arr[i + 1];
						const d = prev ? Math.round((p.kg - prev.kg) * 100) / 100 : 0;
						return (
							<div className="row" key={i}>
								<div className="grow name">{formatShort(p.date)}</div>
								<span className="muted">{p.reps} reps</span>
								<b style={{ minWidth: 64, textAlign: 'right' }}>{p.kg} kg</b>
								<span className={d > 0 ? 'delta-up' : d < 0 ? 'delta-down' : 'muted'} style={{ minWidth: 48, textAlign: 'right' }}>
									{prev ? (d > 0 ? `▲ ${d}` : d < 0 ? `▼ ${-d}` : '=') : ''}
								</span>
							</div>
						);
					})}
				</div>
			</>
		);
	}

	return (
		<div className="card">
			<div className="card-head">
				Ejercicios
				<span className="pill">1ª sesión → última</span>
			</div>
			{byExercise.length === 0 && <div className="empty">Completa entrenos para ver tu progreso</div>}
			{byExercise.map((e) => {
				const first = e.points[0];
				const last = e.points[e.points.length - 1];
				const d = Math.round((last.kg - first.kg) * 100) / 100;
				const dr = last.reps - first.reps;
				return (
					<div className="row clickable" key={e.name} onClick={() => setSel(e.name)}>
						<div className="grow">
							<div className="name">{e.name}</div>
							<div className="muted">
								{first.kg}kg×{first.reps} → {last.kg}kg×{last.reps} · {e.points.length} sesiones
							</div>
						</div>
						<span className={d > 0 || (d === 0 && dr > 0) ? 'delta-up' : d < 0 ? 'delta-down' : 'muted'}>
							{d !== 0 ? `${d > 0 ? '▲' : '▼'} ${Math.abs(d)} kg` : dr !== 0 ? `${dr > 0 ? '▲' : '▼'} ${Math.abs(dr)} rep` : '='}
						</span>
						<span className="chev">›</span>
					</div>
				);
			})}
		</div>
	);
}

function HabitsProgress({ userId, editable }: { userId: string; editable: boolean }) {
	const { db, planOf, toggleHabit, habitsLocal } = useStore();
	const now = new Date();
	const [ym, setYm] = useState({ y: now.getFullYear(), m: now.getMonth() });
	const plan = planOf(userId);
	const habits = plan?.habits?.items ?? [];
	const logs = db.habitLogs.filter((l) => l.userId === userId);
	if (!habits.length)
		return (
			<div className="card">
				<div className="empty">
					Todavía no hay hábitos asignados.
					<div style={{ marginTop: 10 }}>
						<EditHabitsButton userId={userId} />
					</div>
				</div>
			</div>
		);

	const stats = monthStats(habits, logs, ym.y, ym.m, now);
	const isCurrent = ym.y === now.getFullYear() && ym.m === now.getMonth();
	const move = (d: number) =>
		setYm(({ y, m }) => {
			const t = new Date(y, m + d, 1);
			return { y: t.getFullYear(), m: t.getMonth() };
		});
	const totalDone = stats.reduce((a, s) => a + s.done, 0);
	const totalPossible = stats.reduce((a, s) => a + s.elapsed, 0);

	return (
		<>
			<div className="card">
				<div className="card-head">
					Rueda de hábitos
					<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
						<span className="pill yellow">
							{totalDone}/{totalPossible}
						</span>
						<EditHabitsButton userId={userId} />
					</span>
				</div>
				<div className="month-nav">
					<button onClick={() => move(-1)} aria-label="Mes anterior">
						‹
					</button>
					<b style={{ textTransform: 'capitalize' }}>
						{MONTHS[ym.m]} {ym.y}
					</b>
					<button onClick={() => move(1)} disabled={isCurrent} aria-label="Mes siguiente">
						›
					</button>
				</div>
				<div style={{ padding: '0 8px 8px' }}>
					<HabitWheel habits={habits} logs={logs} year={ym.y} month={ym.m} onToggle={editable ? (date, id) => toggleHabit(userId, date, id) : undefined} />
				</div>
				{habitsLocal && (
					<p className="muted" style={{ textAlign: 'center', margin: '0 14px 8px', color: '#8a6d00' }}>
						Modo provisional: las marcas se guardan en este móvil y se subirán solas cuando se active la tabla de hábitos en Supabase.
					</p>
				)}
				<p className="muted" style={{ textAlign: 'center', margin: '0 14px 14px' }}>
					Cada anillo es un hábito (el 1º por fuera) y cada casilla un día.{editable ? ' Toca una casilla para marcarla o desmarcarla.' : ''}
				</p>
			</div>

			{plan?.habits.goal && (
				<div className="card">
					<div className="card-body">
						<div className="muted" style={{ textTransform: 'uppercase', fontWeight: 800, fontSize: 11, letterSpacing: '0.06em' }}>
							Objetivo
						</div>
						<div style={{ fontWeight: 800, fontSize: 16 }}>{plan.habits.goal}</div>
					</div>
				</div>
			)}

			<div className="card">
				<div className="card-head">Detalle del mes</div>
				{stats.map((st) => (
					<div className="habit-row" key={st.habit.id}>
						<span style={{ fontSize: 22 }}>{st.habit.emoji || '•'}</span>
						<div style={{ minWidth: 0 }}>
							<div style={{ fontWeight: 700 }}>{st.habit.name}</div>
							<div className="muted">
								{st.done} de {st.elapsed} días · racha {st.streak} · mejor {st.best}
							</div>
							<div className="bar">
								<div style={{ width: `${Math.round(st.pct * 100)}%`, background: st.color }} />
							</div>
						</div>
						<b style={{ fontSize: 18, fontVariantNumeric: 'tabular-nums' }}>{Math.round(st.pct * 100)}%</b>
					</div>
				))}
			</div>
		</>
	);
}
