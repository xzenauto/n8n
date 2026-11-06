import type { Tab } from '../App';
import { EditHabitsButton } from '../components/EditHabits';
import { NotificationsCard } from '../components/Notifications';
import { HabitRings, MONTHS, monthStats } from '../components/Habits';
import { useStore } from '../data/store';
import { dayFor, formatLong, getFood, macrosOf, nextMeal, nextTrainingFrom, sessionsFor, toISO, WEEKDAYS, WEEKDAYS_SHORT, weekdayIndex } from '../data/util';

export default function Home({ onOpenDay, onGo }: { onOpenDay: (id: string) => void; onGo: (t: Tab) => void }) {
	const { me, myPlan, db } = useStore();
	const now = new Date();
	const today = dayFor(myPlan?.program, now);
	const next = nextTrainingFrom(myPlan?.program, now);
	const mySessions = sessionsFor(db.sessions, me!.id);
	const doneToday = mySessions.find((s) => s.date === toISO(now));
	const meal = myPlan ? nextMeal(myPlan.diet.meals, now) : null;
	const firstName = me!.name.split(' ')[0];

	// Semana actual (lunes a domingo)
	const monday = new Date(now);
	monday.setDate(now.getDate() - weekdayIndex(now));
	const week = Array.from({ length: 7 }, (_, i) => {
		const d = new Date(monday);
		d.setDate(monday.getDate() + i);
		const iso = toISO(d);
		const td = dayFor(myPlan?.program, d);
		return { i, iso, td, done: mySessions.some((s) => s.date === iso) };
	});

	if (!myPlan) {
		return (
			<>
				<Header name={firstName} now={now} />
				<div className="card">
					<div className="card-body">
						<p className="card-title">Sin plan asignado</p>
						<p className="muted">
							{me!.isAdmin ? 'Esta cuenta es solo de administración. Ve a Admin para gestionar atletas.' : 'Tu entrenador todavía no te ha asignado entreno ni dieta.'}
						</p>
						{me!.isAdmin && (
							<button className="btn" onClick={() => onGo('admin')}>
								Ir a Admin
							</button>
						)}
					</div>
				</div>
			</>
		);
	}

	const hasDiet = myPlan.diet.kcal > 0 || myPlan.diet.meals.length > 0;
	const option = meal?.meal.options[0];
	const optMacros = option ? macrosOf(option.items) : null;

	return (
		<>
			<Header name={firstName} now={now} />

			<div className="hero">
				<div className="hero-top">
					<div className="date">Te toca hoy</div>
					<h2>{today ? today.name : 'Descanso'}</h2>
					<div style={{ color: '#bbb', fontSize: 13 }}>
						{today ? `${today.exercises.length} ejercicios · ${today.warmup}` : 'Recupera, camina y cumple tus pasos'}
					</div>
				</div>
				<div className="card-body">
					{today ? (
						doneToday ? (
							<div className="btn-row">
								<span className="pill green" style={{ justifyContent: 'center', padding: 12 }}>
									✓ Entreno completado
								</span>
								<button className="btn ghost sm" onClick={() => onOpenDay(today.id)}>
									Ver entreno
								</button>
							</div>
						) : (
							<button className="btn" onClick={() => onOpenDay(today.id)}>
								Ver entreno de hoy
							</button>
						)
					) : (
						next && (
							<p className="muted" style={{ margin: 0 }}>
								Próximo: <b style={{ color: 'var(--ink)' }}>{next.day.name}</b> · {WEEKDAYS[weekdayIndex(next.date)]}
							</p>
						)
					)}
				</div>
				<div className="week">
					{week.map((w) => (
						<div key={w.i} className={`${w.td ? '' : 'rest'} ${w.done ? 'done' : ''} ${w.iso === toISO(now) ? 'today' : ''}`}>
							{WEEKDAYS_SHORT[w.i]}
							<small>{w.td ? `D${myPlan.program.days.indexOf(w.td) + 1}` : '—'}</small>
						</div>
					))}
				</div>
			</div>

			{myPlan.habits?.items.length > 0 && <HabitsWidget onGo={onGo} />}
			{myPlan.habits?.items.length > 0 && <NotificationsCard compact />}

			{meal && option && (
				<div className="card">
					<div className="card-head">
						Próxima comida
						<span className="pill yellow">
							{meal.tomorrow ? 'Mañana ' : ''}
							{meal.meal.time}
						</span>
					</div>
					<div className="card-body" style={{ paddingBottom: 6 }}>
						<p className="card-title">{meal.meal.name}</p>
						<p className="muted" style={{ margin: 0 }}>
							{option.name}
							{meal.meal.note ? ` · ${meal.meal.note}` : ''}
						</p>
					</div>
					{option.items.map((it, i) => (
						<div className="food-row" key={i}>
							<span className="grams">{it.grams} g</span>
							<span>{getFood(it.foodId)?.name ?? it.foodId}</span>
						</div>
					))}
					{optMacros && (
						<div className="macro-bar">
							<span className="pill">{optMacros.kcal} kcal</span>
							<span className="pill">P {optMacros.p} g</span>
							<span className="pill">H {optMacros.c} g</span>
							<span className="pill">G {optMacros.f} g</span>
						</div>
					)}
					<div className="card-body">
						<button className="btn ghost" onClick={() => onGo('diet')}>
							Ver dieta completa
						</button>
					</div>
				</div>
			)}

			{(hasDiet || myPlan.program.cardio.length > 0) && (
			<div className="card">
				<div className="card-head">{hasDiet ? 'Objetivos diarios' : 'Cardio y pasos'}</div>
				{hasDiet && (
				<div className="stats">
					<div>
						<b>{myPlan.diet.kcal}</b>
						<span>kcal</span>
					</div>
					<div>
						<b>{myPlan.diet.protein}</b>
						<span>Prot</span>
					</div>
					<div>
						<b>{myPlan.diet.carbs}</b>
						<span>Hidr</span>
					</div>
					<div>
						<b>{myPlan.diet.fat}</b>
						<span>Grasa</span>
					</div>
				</div>
				)}
				{myPlan.program.cardio.map((c) => (
					<div className="row" key={c.id}>
						<div className="grow">
							<div className="name">{c.name}</div>
							<div className="muted">{c.notes}</div>
						</div>
						<span className="pill yellow">{c.dose}</span>
					</div>
				))}
			</div>
			)}
		</>
	);
}

function Header({ name, now }: { name: string; now: Date }) {
	return (
		<div className="topbar">
			<div>
				<div className="sub">{formatLong(now)}</div>
				<h1>Hola, {name}</h1>
			</div>
		</div>
	);
}

function HabitsWidget({ onGo }: { onGo: (t: Tab) => void }) {
	const { me, myPlan, db, toggleHabit } = useStore();
	const now = new Date();
	const today = toISO(now);
	const habits = myPlan!.habits.items;
	const logs = db.habitLogs.filter((l) => l.userId === me!.id);
	const stats = monthStats(habits, logs, now.getFullYear(), now.getMonth(), now);
	const doneToday = logs.find((l) => l.date === today)?.done ?? [];
	const countToday = habits.filter((h) => doneToday.includes(h.id)).length;

	return (
		<div className="rings-card">
			<div className="head">
				<b>Hábitos · {MONTHS[now.getMonth()]}</b>
				<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
					<span className="dark-muted">
						Hoy {countToday}/{habits.length}
					</span>
					<EditHabitsButton userId={me!.id} dark />
				</span>
			</div>
			<div className="rings-top" onClick={() => onGo('progress')} style={{ cursor: 'pointer' }}>
				<HabitRings stats={stats} size={150} />
				<div className="rings-legend">
					{stats.map((st) => (
						<div key={st.habit.id}>
							<span className="dot" style={{ background: st.color }} />
							<span className="lbl">{st.habit.name}</span>
							<span className="val" style={{ color: st.color }}>
								{st.done}/{st.elapsed}
							</span>
						</div>
					))}
				</div>
			</div>
			{myPlan!.habits.goal && (
				<p className="dark-muted" style={{ margin: '12px 0 0' }}>
					🎯 {myPlan!.habits.goal}
				</p>
			)}
			<div className="habit-today">
				{stats.map((st) => {
					const on = doneToday.includes(st.habit.id);
					return (
						<button
							key={st.habit.id}
							className={`habit-btn ${on ? 'on' : ''}`}
							style={{ ['--c' as string]: st.color }}
							onClick={() => toggleHabit(me!.id, today, st.habit.id)}
							aria-pressed={on}
						>
							<span className="check">{on ? '✓' : ''}</span>
							<span className="txt">
								{st.habit.emoji} {st.habit.name}
							</span>
							{st.streak > 1 && <span style={{ fontSize: 12, color: st.color, fontWeight: 800 }}>🔥 {st.streak}</span>}
						</button>
					);
				})}
			</div>
		</div>
	);
}
