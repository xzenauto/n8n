import { TopBar } from '../components/ui';
import { useStore } from '../data/store';
import type { TrainingDay } from '../data/types';
import { dayFor, formatShort, nextTrainingFrom, sessionsFor, toISO, WEEKDAYS, weekdayIndex } from '../data/util';

interface Props {
	openDay: string | null;
	setOpenDay: (id: string | null) => void;
	onStart: (dayId: string) => void;
}

export default function Trainings({ openDay, setOpenDay, onStart }: Props) {
	const { myPlan } = useStore();
	if (!myPlan || myPlan.program.days.length === 0)
		return (
			<>
				<TopBar title="Entrenos" />
				<div className="card">
					<div className="empty">Todavía no tienes entrenos asignados.</div>
				</div>
			</>
		);

	const program = myPlan.program;
	const day = program.days.find((d) => d.id === openDay);
	if (day) return <DayDetail day={day} onBack={() => setOpenDay(null)} onStart={() => onStart(day.id)} />;

	const now = new Date();
	const today = dayFor(program, now);
	const next = nextTrainingFrom(program, now);
	const weekdaysOf = (id: string) =>
		program.schedule
			.map((d, i) => (d === id ? WEEKDAYS[i] : null))
			.filter(Boolean)
			.join(', ');

	return (
		<>
			<TopBar title="Entrenos" sub={program.name} />

			<div className="section-label">Te toca hoy</div>
			{today ? (
				<DayCard day={today} badge="Hoy" yellow onClick={() => setOpenDay(today.id)} />
			) : (
				<div className="card">
					<div className="card-body">
						<p className="card-title">Descanso</p>
						<p className="muted" style={{ margin: 0 }}>
							Hoy no hay entreno programado.
						</p>
					</div>
				</div>
			)}

			{next && (
				<>
					<div className="section-label">Lo siguiente</div>
					<DayCard day={next.day} badge={WEEKDAYS[weekdayIndex(next.date)]} onClick={() => setOpenDay(next.day.id)} />
				</>
			)}

			<div className="section-label">Todos los entrenos</div>
			<div className="card">
				{program.days.map((d) => (
					<div key={d.id} className="row clickable" onClick={() => setOpenDay(d.id)}>
						<div className="grow">
							<div className="name">{d.name}</div>
							<div className="muted">
								{d.exercises.length} ejercicios{weekdaysOf(d.id) ? ` · ${weekdaysOf(d.id)}` : ''}
							</div>
						</div>
						<span className="chev">›</span>
					</div>
				))}
			</div>
		</>
	);
}

function DayCard({ day, badge, yellow, onClick }: { day: TrainingDay; badge: string; yellow?: boolean; onClick: () => void }) {
	return (
		<div className="card" onClick={onClick} style={{ cursor: 'pointer' }}>
			<div className="card-head">
				{day.warmup || 'Entreno'}
				<span className={`pill ${yellow ? 'yellow' : ''}`}>{badge}</span>
			</div>
			<div className="row">
				<div className="grow">
					<div className="card-title" style={{ margin: 0 }}>
						{day.name}
					</div>
					<div className="muted">{day.exercises.map((e) => e.name).join(' · ')}</div>
				</div>
				<span className="chev">›</span>
			</div>
		</div>
	);
}

function DayDetail({ day, onBack, onStart }: { day: TrainingDay; onBack: () => void; onStart: () => void }) {
	const { db, me, myPlan } = useStore();
	const history = sessionsFor(db.sessions, me!.id).filter((s) => s.dayId === day.id);
	const doneToday = history.some((s) => s.date === toISO(new Date()));
	const cardio = myPlan?.program.cardio ?? [];

	return (
		<>
			<TopBar title={day.name} sub={[day.warmup, day.rest && `Descanso ${day.rest}`].filter(Boolean).join(' · ')} onBack={onBack} />

			<div className="card">
				<table className="ex-table">
					<thead>
						<tr>
							<th>Ejercicio</th>
							<th>Series</th>
							<th>Reps</th>
							<th>RIR</th>
						</tr>
					</thead>
					<tbody>
						{day.exercises.map((e) => (
							<tr key={e.id}>
								<td>
									{e.name}
									{(e.note || e.video) && (
										<span className="note">
											{e.note}
											{e.note && e.video ? ' · ' : ''}
											{e.video && (
												<a href={e.video} target="_blank" rel="noreferrer">
													Vídeo
												</a>
											)}
										</span>
									)}
								</td>
								<td>{e.sets}</td>
								<td>{e.reps}</td>
								<td>{e.rir}</td>
							</tr>
						))}
					</tbody>
				</table>
				<div className="card-body">
					<button className="btn" onClick={onStart} disabled={day.exercises.length === 0}>
						{doneToday ? 'Repetir entreno' : 'Iniciar entreno'}
					</button>
					<p className="muted" style={{ textAlign: 'center', margin: '10px 0 0' }}>
						RIR “F” = al fallo
					</p>
				</div>
			</div>

			{cardio.length > 0 && (
				<>
					<div className="section-label">Protocolo de cardio</div>
					<div className="card">
						{cardio.map((c) => (
							<div className="row" key={c.id}>
								<div className="grow">
									<div className="name">{c.name}</div>
									<div className="muted">{c.notes}</div>
								</div>
								<span className="pill yellow">{c.dose}</span>
							</div>
						))}
					</div>
				</>
			)}

			<div className="section-label">Historial de este día</div>
			<div className="card">
				{history.length === 0 && <div className="empty">Aún no has hecho este entreno</div>}
				{history.map((s) => (
					<details key={s.id} className="row" style={{ display: 'block' }}>
						<summary style={{ cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'center' }}>
							<b style={{ flex: 1 }}>{formatShort(s.date)}</b>
							{s.readiness != null && <span className="pill">Readiness {s.readiness}</span>}
							{s.fatigue != null && <span className="pill dark">Fatiga {s.fatigue}</span>}
						</summary>
						<div style={{ marginTop: 8 }}>
							{s.entries
								.filter((e) => e.sets.length)
								.map((e) => (
									<div key={e.exerciseId} style={{ padding: '4px 0', fontSize: 13 }}>
										<b>{e.name}</b>
										<div className="muted">{e.sets.map((x) => `${x.reps}×${x.kg || '–'}kg @${x.rir}`).join('  ·  ')}</div>
									</div>
								))}
							{s.note && <p className="muted">📝 {s.note}</p>}
						</div>
					</details>
				))}
			</div>
		</>
	);
}
