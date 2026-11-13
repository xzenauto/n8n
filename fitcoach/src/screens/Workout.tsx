import { useEffect, useMemo, useState } from 'react';
import { RestTimer, restIdle, restStart, type RestState } from '../components/RestTimer';
import { ask, Scale } from '../components/ui';
import { useStore } from '../data/store';
import { getDraft, setDraft as storeDraft, type Draft } from '../data/draft';
import type { SetLog } from '../data/types';
import { bestSet, formatShort, lastLogOf, parseKg, setTarget, toISO } from '../data/util';
import { videoFor } from '../data/videos';

type Step = { kind: 'readiness' } | { kind: 'set'; ex: number; set: number } | { kind: 'fatigue' } | { kind: 'done' };

/** Si el entrenador cambió el día después de empezar, ajusta el borrador a los ejercicios y series actuales. */
function fitDraft(d: Draft | null, sets: number[], stepCount: number): Draft | null {
	if (!d) return null;
	const logs = sets.map((n, i) => Array.from({ length: n }, (_, j) => d.logs[i]?.[j] ?? { reps: '', kg: '', rir: '' }));
	return { ...d, logs, stepIdx: Math.min(d.stepIdx, stepCount - 2) };
}

export default function Workout({ dayId, onExit }: { dayId: string; onExit: () => void }) {
	const { myPlan, me, db, addSession } = useStore();
	const day = myPlan!.program.days.find((d) => d.id === dayId)!;

	const steps = useMemo<Step[]>(() => {
		const s: Step[] = [{ kind: 'readiness' }];
		day.exercises.forEach((e, ex) => {
			for (let set = 0; set < Math.max(1, e.sets); set++) s.push({ kind: 'set', ex, set });
		});
		s.push({ kind: 'fatigue' }, { kind: 'done' });
		return s;
	}, [day]);

	const [draft, setDraft] = useState<Draft>(
		() =>
			fitDraft(getDraft(me!.id)?.dayId === dayId ? getDraft(me!.id) : null, day.exercises.map((e) => Math.max(1, e.sets)), steps.length) ?? {
				dayId,
				readiness: null,
				fatigue: null,
				note: '',
				logs: day.exercises.map((e) => Array.from({ length: Math.max(1, e.sets) }, () => ({ reps: '', kg: '', rir: '' }))),
				stepIdx: 0,
			},
	);
	const step = steps[draft.stepIdx];

	useEffect(() => {
		if (step.kind !== 'done') storeDraft(me!.id, draft);
	}, [draft, step.kind]);

	useEffect(() => {
		window.scrollTo(0, 0);
	}, [draft.stepIdx]);

	const go = (delta: number) =>
		setDraft((d) => {
			const stepIdx = Math.min(steps.length - 1, Math.max(0, d.stepIdx + delta));
			// Al terminar una serie (avanzar desde una pantalla de serie a otra) arranca el descanso
			const fromSet = steps[d.stepIdx]?.kind === 'set';
			const toSet = steps[stepIdx]?.kind === 'set';
			const from = steps[d.stepIdx];
			const to = steps[stepIdx];
			// Entre series: el descanso del día. Al cambiar de ejercicio: 4 minutos.
			const newExercise = fromSet && toSet && from.kind === 'set' && to.kind === 'set' && from.ex !== to.ex;
			const rest = delta > 0 && fromSet && toSet ? restStart(newExercise) : delta > 0 && !toSet ? restIdle : d.rest;
			return { ...d, stepIdx, rest };
		});

	function finish() {
		addSession({
			userId: me!.id,
			dayId,
			dayName: day.name,
			date: toISO(new Date()),
			readiness: draft.readiness,
			fatigue: draft.fatigue,
			note: draft.note.trim(),
			entries: day.exercises.map((e, i) => ({
				exerciseId: e.id,
				name: e.name,
				sets: draft.logs[i].filter((s) => s.reps.trim() || s.kg.trim()),
			})),
		});
		storeDraft(me!.id, null);
		go(1);
	}

	async function exit() {
		if (step.kind === 'done' || (await ask('¿Salir del entreno? Tu progreso se guarda y podrás continuar luego.'))) onExit();
	}

	async function discard() {
		if (await ask('¿Descartar este entreno? Se perderá lo apuntado.')) {
			storeDraft(me!.id, null);
			onExit();
		}
	}

	const totalSets = steps.filter((s) => s.kind === 'set').length;
	const doneSets = steps.slice(0, draft.stepIdx).filter((s) => s.kind === 'set').length;

	return (
		<div className="runner">
			<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 'calc(14px + env(safe-area-inset-top))' }}>
				<button className="back" onClick={exit}>
					✕ Salir
				</button>
				<span className="dark-muted">{day.name}</span>
			</div>
			<div className="progress-bar">
				<div style={{ width: `${(doneSets / totalSets) * 100}%` }} />
			</div>

			{step.kind === 'readiness' && (
				<>
					<h1 style={{ margin: '8px 0 4px', fontSize: 26 }}>¿Cómo llegas hoy?</h1>
					<p className="dark-muted" style={{ marginTop: 0 }}>
						Readiness: del 0 (fatal) al 10 (a tope), ¿qué tan bien estás para entrenar?
					</p>
					<div className="card">
						<div className="card-body">
							<Scale value={draft.readiness} onChange={(n) => setDraft((d) => ({ ...d, readiness: n }))} />
						</div>
					</div>
					<div className="card">
						<div className="card-head">Hoy toca</div>
						{day.exercises.map((e) => (
							<div className="row" key={e.id}>
								<div className="grow name">{e.name}</div>
								<span className="pill">
									{e.sets} × {e.reps}
								</span>
							</div>
						))}
					</div>
					<div className="spacer" />
					<button className="btn" disabled={draft.readiness == null} onClick={() => go(1)}>
						Empezar
					</button>
				</>
			)}

			{step.kind === 'set' && (
				<SetScreen
					key={draft.stepIdx}
					rest={draft.rest ?? restIdle}
					restText={day.rest}
					onRest={(r) => setDraft((d) => ({ ...d, rest: r }))}
					exIndex={step.ex}
					setIndex={step.set}
					total={day.exercises.length}
					exercise={day.exercises[step.ex]}
					value={draft.logs[step.ex][step.set]}
					doneSets={draft.logs[step.ex]}
					last={lastLogOf(db.sessions, me!.id, day.exercises[step.ex].id, day.exercises[step.ex].name, day.id)}
					onChange={(v) =>
						setDraft((d) => {
							const logs = d.logs.map((l) => [...l]);
							logs[step.ex][step.set] = v;
							return { ...d, logs };
						})
					}
					onPrev={() => go(-1)}
					onNext={() => go(1)}
					isLastSet={step.set === Math.max(1, day.exercises[step.ex].sets) - 1}
					isLastExercise={step.ex === day.exercises.length - 1}
					nextExercise={day.exercises[step.ex + 1] ?? null}
				/>
			)}

			{step.kind === 'fatigue' && (
				<>
					<h1 style={{ margin: '8px 0 4px', fontSize: 26 }}>¡Entreno terminado!</h1>
					<p className="dark-muted" style={{ marginTop: 0 }}>
						Fatiga post: del 0 (fresco) al 10 (destrozado), ¿cómo acabas?
					</p>
					<div className="card">
						<div className="card-body">
							<Scale value={draft.fatigue} onChange={(n) => setDraft((d) => ({ ...d, fatigue: n }))} />
						</div>
					</div>
					<div className="card">
						<div className="card-body">
							<label className="field" style={{ margin: 0 }}>
								<span>Observaciones (opcional)</span>
								<textarea rows={3} value={draft.note} onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))} placeholder="Ej.: sin muñequera, máquina ocupada…" />
							</label>
						</div>
					</div>
					<div className="spacer" />
					<div className="btn-row">
						<button className="btn secondary" onClick={() => go(-1)}>
							Atrás
						</button>
						<button className="btn" disabled={draft.fatigue == null} onClick={finish}>
							Guardar entreno
						</button>
					</div>
					<button className="btn" style={{ background: 'transparent', color: 'var(--red)', marginTop: 8 }} onClick={discard}>
						Descartar entreno
					</button>
				</>
			)}

			{step.kind === 'done' && <Summary dayName={day.name} logs={draft.logs} names={day.exercises.map((e) => e.name)} readiness={draft.readiness} fatigue={draft.fatigue} onExit={onExit} />}
		</div>
	);
}

interface SetProps {
	exIndex: number;
	setIndex: number;
	total: number;
	exercise: { name: string; note: string; video: string; sets: number; reps: string; rir: string };
	value: SetLog;
	doneSets: SetLog[];
	last: ReturnType<typeof lastLogOf>;
	onChange: (v: SetLog) => void;
	onPrev: () => void;
	onNext: () => void;
	isLastSet: boolean;
	isLastExercise: boolean;
	nextExercise: { name: string; sets: number; reps: string } | null;
	rest: RestState;
	restText: string;
	onRest: (r: RestState) => void;
}

function SetScreen({ exIndex, setIndex, total, exercise, value, doneSets, last, onChange, onPrev, onNext, isLastSet, isLastExercise, nextExercise, rest, restText, onRest }: SetProps) {
	const n = Math.max(1, exercise.sets);
	const prev = last?.entry.sets[setIndex] ?? last?.entry.sets[last.entry.sets.length - 1];
	const set = (k: keyof SetLog, v: string) => onChange({ ...value, [k]: v });
	const target = setTarget(exercise.reps, prev);
	const video = videoFor(exercise);
	const nextLabel = !isLastSet ? 'Siguiente serie' : isLastExercise ? 'Terminar' : 'Próximo ejercicio';

	return (
		<>
			<div className="dark-muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: 12 }}>
				Ejercicio {exIndex + 1} de {total}
			</div>
			<h1 style={{ margin: '4px 0 2px', fontSize: 24, lineHeight: 1.2 }}>{exercise.name}</h1>
			{exercise.note && (
				<div className="dark-muted" style={{ marginBottom: 8 }}>
					{exercise.note}
				</div>
			)}
			{video && (
				<a className="video-btn" href={video} target="_blank" rel="noreferrer">
					<span>▶</span> Ver vídeo del ejercicio
				</a>
			)}
			<div style={{ height: 12 }} />

			<div className="card">
				<div className="card-head">
					Serie {setIndex + 1} de {n}
					<span className="pill yellow">
						{[exercise.reps && `Objetivo ${exercise.reps}`, exercise.rir && `RIR ${exercise.rir}`].filter(Boolean).join(' · ') || 'Libre'}
					</span>
				</div>
				<div className="set-dots" style={{ paddingTop: 4 }}>
					{Array.from({ length: n }, (_, i) => (
						<span key={i} className={i === setIndex ? 'on' : doneSets[i]?.reps ? 'done' : ''} />
					))}
				</div>
				<div className="compare">
					<div>
						<h4>Semana pasada{last ? ` · ${formatShort(last.session.date)}` : ''}</h4>
						<div className="kv">
							<span>Reps</span>
							<b>{prev?.reps || '–'}</b>
						</div>
						<div className="kv">
							<span>Kg</span>
							<b>{prev?.kg || '–'}</b>
						</div>
						<div className="kv">
							<span>RIR</span>
							<b>{prev?.rir || '–'}</b>
						</div>
					</div>
					<div>
						<h4>Esta semana · objetivo</h4>
						<div className="kv">
							<span>Reps</span>
							<b>{target.reps}</b>
						</div>
						<div className="kv">
							<span>Kg</span>
							<b style={target.kind === 'up' ? { color: 'var(--green)' } : undefined}>{target.kind === 'up' ? `↑ ${target.kg}` : target.kg}</b>
						</div>
						<div className="kv">
							<span>RIR</span>
							<b>{exercise.rir || "–"}</b>
						</div>
					</div>
				</div>
				<div className={`target-tip ${target.kind}`}>
					<span>{target.kind === 'up' ? '⬆️' : '🎯'}</span>
					<span>
						{target.tip}
						<small>
							{[exercise.reps && `Rango ${exercise.reps}`, exercise.rir && `RIR ${exercise.rir}`].filter(Boolean).join(' · ')}
						</small>
					</span>
				</div>
				<div className="big-inputs">
					<label>
						<span>Kg</span>
						<input inputMode="decimal" value={value.kg} placeholder={prev?.kg || '0'} onChange={(e) => set('kg', e.target.value)} />
					</label>
					<label>
						<span>Reps</span>
						<input inputMode="numeric" value={value.reps} placeholder={target.kind === 'new' ? prev?.reps || '0' : target.reps} onChange={(e) => set('reps', e.target.value.replace(/[^\d]/g, ''))} />
					</label>
					<label>
						<span>RIR</span>
						<input value={value.rir} placeholder={exercise.rir.split('-')[0].trim() || '0'} onChange={(e) => set('rir', e.target.value.toUpperCase())} />
					</label>
				</div>
				{prev && (prev.kg || prev.reps) && (
					<div className="quick-fill">
						<span className="quick-fill-label">
							Copiar de la semana pasada ({[prev.reps && `${prev.reps} reps`, prev.kg && `${prev.kg} kg`, prev.rir && `RIR ${prev.rir}`].filter(Boolean).join(' · ')})
						</span>
						<button disabled={!prev.kg} onClick={() => onChange({ ...value, kg: prev.kg })}>
							Mismo peso
						</button>
						<button disabled={!prev.kg} onClick={() => onChange({ ...value, kg: prev.kg, rir: prev.rir || value.rir })}>
							Mismo peso y RIR
						</button>
						<button onClick={() => onChange({ kg: prev.kg, reps: prev.reps, rir: prev.rir || value.rir })}>Todo igual</button>
						<button disabled={!Number(prev.reps)} onClick={() => onChange({ kg: prev.kg, reps: String(Number(prev.reps) + 1), rir: prev.rir || value.rir })}>
							Todo igual +1 repe
						</button>
					</div>
				)}
			</div>

			<RestTimer state={rest} onChange={onRest} rest={restText} />

			<div className="spacer" />
			<div className="btn-row">
				<button className="btn secondary" onClick={onPrev}>
					Atrás
				</button>
				<button className="btn" onClick={onNext} style={{ flex: 2 }}>
					{nextLabel} ›
				</button>
			</div>
			<p className="next-ex">
				{nextExercise ? (
					<>
						A continuación: <b>{nextExercise.name}</b> · {nextExercise.sets} × {nextExercise.reps}
					</>
				) : (
					'Último ejercicio del día'
				)}
			</p>
		</>
	);
}

function Summary({ dayName, logs, names, readiness, fatigue, onExit }: { dayName: string; logs: SetLog[][]; names: string[]; readiness: number | null; fatigue: number | null; onExit: () => void }) {
	const vol = logs.flat().reduce((a, s) => a + (parseKg(s.kg) ?? 0) * (Number(s.reps) || 0), 0);
	return (
		<>
			<h1 style={{ margin: '8px 0 4px', fontSize: 26 }}>¡Guardado! 💪</h1>
			<p className="dark-muted" style={{ marginTop: 0 }}>
				{dayName}
			</p>
			<div className="card">
				<div className="stats" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
					<div>
						<b>{readiness ?? '–'}</b>
						<span>Readiness</span>
					</div>
					<div>
						<b>{fatigue ?? '–'}</b>
						<span>Fatiga</span>
					</div>
					<div>
						<b>{Math.round(vol).toLocaleString('es-ES')}</b>
						<span>Kg totales</span>
					</div>
				</div>
				{names.map((n, i) => {
					const b = bestSet(logs[i]);
					return (
						<div className="row" key={i}>
							<div className="grow">
								<div className="name">{n}</div>
								<div className="muted">
									{logs[i]
										.filter((s) => s.reps)
										.map((s) => `${s.reps}×${s.kg || '–'}`)
										.join(' · ') || 'Sin registrar'}
								</div>
							</div>
							{b && <span className="pill yellow">{b.kg} kg</span>}
						</div>
					);
				})}
			</div>
			<div className="spacer" />
			<button className="btn" onClick={onExit}>
				Volver
			</button>
		</>
	);
}
