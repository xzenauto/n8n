import { useMemo, useState } from 'react';
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
	const [tab, setTab] = useState<'weight' | 'measures' | 'training'>('weight');
	const uid = userId ?? me!.id;
	return (
		<>
			{!userId && <TopBar title="Progreso" />}
			<div className="tabs">
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
		const map = new Map<string, { name: string; points: { date: string; kg: number; reps: number }[] }>();
		for (const s of sessions)
			for (const e of s.entries) {
				const b = bestSet(e.sets);
				if (!b) continue;
				const k = e.name;
				if (!map.has(k)) map.set(k, { name: e.name, points: [] });
				map.get(k)!.points.push({ date: s.date, ...b });
			}
		return [...map.values()];
	}, [sessions]);

	const current = byExercise.find((e) => e.name === sel);
	if (current) {
		const pts = current.points.map((p) => ({ label: formatShort(p.date), value: p.kg }));
		return (
			<>
				<button className="back" onClick={() => setSel(null)}>
					‹ Todos los ejercicios
				</button>
				<div className="card">
					<div className="card-head">{current.name}</div>
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
