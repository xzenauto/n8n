import { useMemo, useState } from 'react';
import { HABIT_COLORS, HabitRings, monthStats } from '../components/Habits';
import { useStore } from '../data/store';
import type { Habit, HabitLog } from '../data/types';
import { toISO, uid } from '../data/util';

/** Los 10 hábitos que se proponen al atleta la primera vez. */
export const SUGGESTED_HABITS: Habit[] = [
	{ id: 's1', emoji: '😴', name: 'Dormir 7-8 horas' },
	{ id: 's2', emoji: '⏰', name: 'Acostarte y despertar a la misma hora' },
	{ id: 's3', emoji: '💧', name: 'Beber 2 litros de agua' },
	{ id: 's4', emoji: '🚶', name: 'Cumplir tus pasos del día' },
	{ id: 's5', emoji: '🥩', name: 'Llegar a tu proteína del día' },
	{ id: 's6', emoji: '📵', name: 'Nada de móvil la primera hora del día' },
	{ id: 's7', emoji: '☀️', name: 'Tomar luz solar por la mañana' },
	{ id: 's8', emoji: '🧘', name: '5 minutos de respiración o meditación' },
	{ id: 's9', emoji: '🥦', name: 'Verdura en al menos 2 comidas' },
	{ id: 's10', emoji: '🍷', name: 'Cero alcohol' },
];

const MIN = 4;
const MAX = 5;

export default function Onboarding() {
	const { me, myPlan, saveMyHabits } = useStore();
	const [step, setStep] = useState(0);
	const [chosen, setChosen] = useState<Habit[]>([]);
	const [custom, setCustom] = useState('');
	const [customEmoji, setCustomEmoji] = useState('✅');
	const [goal, setGoal] = useState(myPlan?.habits.goal ?? '');
	const firstName = me!.name.split(' ')[0];

	// Datos de ejemplo para las ilustraciones (no son del atleta)
	const demo = useMemo(() => {
		const habits = SUGGESTED_HABITS.slice(0, 5);
		const now = new Date();
		const logs: HabitLog[] = [];
		for (let d = 1; d <= now.getDate(); d++)
			logs.push({ userId: 'demo', date: toISO(new Date(now.getFullYear(), now.getMonth(), d)), done: habits.filter((_, i) => (d * 7 + i * 3) % 10 < 7 - i).map((h) => h.id) });
		return monthStats(habits, logs, now.getFullYear(), now.getMonth(), now);
	}, []);

	const isChosen = (h: Habit) => chosen.some((c) => c.name === h.name);
	const toggle = (h: Habit) =>
		setChosen((c) => (isChosen(h) ? c.filter((x) => x.name !== h.name) : c.length < MAX ? [...c, h] : c));
	const addCustom = () => {
		const name = custom.trim();
		if (!name || chosen.length >= MAX || chosen.some((c) => c.name.toLowerCase() === name.toLowerCase())) return;
		setChosen((c) => [...c, { id: 'c', emoji: customEmoji.trim() || '✅', name }]);
		setCustom('');
		setCustomEmoji('✅');
	};
	const customs = chosen.filter((c) => !SUGGESTED_HABITS.some((s) => s.name === c.name));

	function finish() {
		saveMyHabits({ goal: goal.trim(), onboarded: true, items: chosen.map((h, i) => ({ id: uid(`h${i + 1}`), emoji: h.emoji, name: h.name })) });
	}

	const slides = [
		{
			title: `Hola, ${firstName} 👋`,
			body: (
				<>
					<p>
						Además del entreno, en FitCoach vas a cuidar <b>4 o 5 hábitos diarios</b>. Son pequeñas acciones que, repetidas cada día, marcan la diferencia en tus
						resultados.
					</p>
					<p>
						Se cumplen <b>los 7 días de la semana</b>, entrenes o no.
					</p>
				</>
			),
			art: <div style={{ fontSize: 72, textAlign: 'center' }}>🎯</div>,
		},
		{
			title: 'Márcalos cada día',
			body: (
				<p>
					En <b>Inicio</b> verás tus hábitos de hoy. Toca cada uno cuando lo cumplas. Cada hábito tiene su anillo, que se va llenando a lo largo del mes, y si
					encadenas días seguidos verás tu racha 🔥.
				</p>
			),
			art: (
				<div style={{ display: 'flex', justifyContent: 'center' }}>
					<HabitRings stats={demo} size={170} />
				</div>
			),
		},
		{
			title: 'Tu rueda del mes',
			body: (
				<p>
					En <b>Progreso › Hábitos</b> tienes la rueda del mes: cada casilla es un día y cada anillo un hábito. Si un día se te olvidó marcar algo, tócalo ahí. Debajo ves
					tu porcentaje y tus rachas.
				</p>
			),
			art: (
				<div className="onb-wheel" aria-hidden>
					{Array.from({ length: 5 }, (_, r) => (
						<div key={r} className="onb-row">
							{Array.from({ length: 14 }, (_, d) => (
								<span key={d} style={{ background: (d * 5 + r * 3) % 7 < 5 - (r % 2) ? HABIT_COLORS[r] : '#3a3a3a' }} />
							))}
						</div>
					))}
				</div>
			),
		},
	];

	const pickStep = slides.length;
	const goalStep = slides.length + 1;
	const total = slides.length + 2;
	const canContinue = step !== pickStep || (chosen.length >= MIN && chosen.length <= MAX);

	return (
		<div className="onb">
			<div className="onb-dots">
				{Array.from({ length: total }, (_, i) => (
					<span key={i} className={i === step ? 'on' : i < step ? 'done' : ''} />
				))}
			</div>

			{step < slides.length && (
				<div className="onb-slide">
					<div className="onb-art">{slides[step].art}</div>
					<h1>{slides[step].title}</h1>
					<div className="onb-body">{slides[step].body}</div>
				</div>
			)}

			{step === pickStep && (
				<div className="onb-slide">
					<h1>Elige tus hábitos</h1>
					<p className="onb-body" style={{ marginTop: 0 }}>
						Escoge <b>entre {MIN} y {MAX}</b>. Puedes usar los nuestros o escribir los tuyos.
					</p>
					<div className="onb-count">
						<b>{chosen.length}</b>/{MAX} elegidos
					</div>
					<div className="onb-list">
						{SUGGESTED_HABITS.map((h) => {
							const on = isChosen(h);
							const idx = chosen.findIndex((c) => c.name === h.name);
							return (
								<button
									key={h.id}
									className={`habit-btn ${on ? 'on' : ''}`}
									style={{ ['--c' as string]: on ? HABIT_COLORS[idx % HABIT_COLORS.length] : '#555' }}
									onClick={() => toggle(h)}
									disabled={!on && chosen.length >= MAX}
									aria-pressed={on}
								>
									<span className="check">{on ? '✓' : ''}</span>
									<span className="txt">
										{h.emoji} {h.name}
									</span>
								</button>
							);
						})}
						{customs.map((h) => {
							const idx = chosen.findIndex((c) => c.name === h.name);
							return (
								<button key={h.name} className="habit-btn on" style={{ ['--c' as string]: HABIT_COLORS[idx % HABIT_COLORS.length] }} onClick={() => toggle(h)} aria-pressed>
									<span className="check">✓</span>
									<span className="txt">
										{h.emoji} {h.name}
									</span>
									<span style={{ fontSize: 11, color: 'var(--on-dark-2)' }}>tuyo</span>
								</button>
							);
						})}
					</div>
					<div className="onb-custom">
						<input value={customEmoji} onChange={(e) => setCustomEmoji(e.target.value)} aria-label="Emoji" style={{ width: 54, textAlign: 'center' }} />
						<input
							value={custom}
							onChange={(e) => setCustom(e.target.value)}
							onKeyDown={(e) => e.key === 'Enter' && addCustom()}
							placeholder="Escribe un hábito tuyo…"
							disabled={chosen.length >= MAX}
						/>
						<button className="btn sm" onClick={addCustom} disabled={!custom.trim() || chosen.length >= MAX}>
							Añadir
						</button>
					</div>
					{chosen.length >= MAX && <p className="dark-muted">Ya tienes {MAX}. Quita uno si quieres cambiarlo.</p>}
				</div>
			)}

			{step === goalStep && (
				<div className="onb-slide">
					<div className="onb-art" style={{ fontSize: 64, textAlign: 'center' }}>
						🏁
					</div>
					<h1>¿Para qué lo haces?</h1>
					<p className="onb-body">Escribe tu objetivo en una frase. Lo verás cada día junto a tus hábitos. Es opcional.</p>
					<input className="input" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Ej.: tener más energía y dormir mejor" />
					<div className="onb-summary">
						{chosen.map((h, i) => (
							<div key={h.name}>
								<span className="dot" style={{ background: HABIT_COLORS[i % HABIT_COLORS.length] }} />
								{h.emoji} {h.name}
							</div>
						))}
					</div>
				</div>
			)}

			<div className="spacer" />
			<div className="btn-row">
				{step > 0 && (
					<button className="btn secondary" onClick={() => setStep(step - 1)}>
						Atrás
					</button>
				)}
				{step < goalStep ? (
					<button className="btn" style={{ flex: 2 }} disabled={!canContinue} onClick={() => setStep(step + 1)}>
						{step === pickStep ? (chosen.length < MIN ? `Elige ${MIN - chosen.length} más` : 'Continuar') : 'Siguiente'}
					</button>
				) : (
					<button className="btn" style={{ flex: 2 }} onClick={finish}>
						Empezar 💪
					</button>
				)}
			</div>
			{step < pickStep && (
				<button className="back" style={{ alignSelf: 'center', marginTop: 8 }} onClick={() => setStep(pickStep)}>
					Saltar explicación
				</button>
			)}
		</div>
	);
}
