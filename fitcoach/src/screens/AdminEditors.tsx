import { ask } from '../components/ui';
import { useState } from 'react';
import { FOODS, GROUP_LABEL, type FoodGroup } from '../data/foods';
import { HABIT_COLORS } from '../components/Habits';
import { CATALOG_NAMES, catalogVideo, videoFor } from '../data/videos';
import type { Diet, EquivalenceGroup, Exercise, Habit, Habits, MealItem, Program, TrainingDay } from '../data/types';
import { getFood, macrosOf, uid, WEEKDAYS_SHORT } from '../data/util';

function move<T>(arr: T[], i: number, d: number): T[] {
	const j = i + d;
	if (j < 0 || j >= arr.length) return arr;
	const a = [...arr];
	[a[i], a[j]] = [a[j], a[i]];
	return a;
}

// ---------------- Entreno ----------------

export function ProgramEditor({ value, onChange }: { value: Program; onChange: (p: Program) => void }) {
	const [open, setOpen] = useState<string | null>(value.days[0]?.id ?? null);
	const setDay = (id: string, patch: Partial<TrainingDay>) => onChange({ ...value, days: value.days.map((d) => (d.id === id ? { ...d, ...patch } : d)) });

	return (
		<>
			<datalist id="catalogo-ejercicios">
				{CATALOG_NAMES.map((n) => (
					<option key={n} value={n} />
				))}
			</datalist>
			<div className="card">
				<div className="card-head">Programa</div>
				<div className="card-body">
					<label className="field">
						<span>Nombre del programa</span>
						<input value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} />
					</label>
					<div className="field" style={{ marginBottom: 0 }}>
						<span>Qué día toca cada día de la semana</span>
						<div className="sched">
							{WEEKDAYS_SHORT.map((w, i) => (
								<label key={i}>
									{w}
									<select
										value={value.schedule[i] ?? ''}
										onChange={(e) => {
											const s = [...value.schedule];
											s[i] = e.target.value || null;
											onChange({ ...value, schedule: s });
										}}
									>
										<option value="">—</option>
										{value.days.map((d, di) => (
											<option key={d.id} value={d.id}>
												D{di + 1}
											</option>
										))}
									</select>
								</label>
							))}
						</div>
					</div>
				</div>
			</div>

			{value.days.map((d, di) => (
				<div className="card" key={d.id}>
					<div className="card-head" style={{ cursor: 'pointer' }} onClick={() => setOpen(open === d.id ? null : d.id)}>
						<span>
							D{di + 1} · {d.name || 'Sin nombre'}
						</span>
						<span className="pill">{d.exercises.length} ej. {open === d.id ? '▲' : '▼'}</span>
					</div>
					{open === d.id && (
						<div className="card-body">
							<label className="field">
								<span>Nombre del día</span>
								<input value={d.name} onChange={(e) => setDay(d.id, { name: e.target.value })} />
							</label>
							<div className="grid-2">
								<label className="field">
									<span>Calentamiento</span>
									<input value={d.warmup} onChange={(e) => setDay(d.id, { warmup: e.target.value })} />
								</label>
								<label className="field">
									<span>Descanso</span>
									<input value={d.rest} onChange={(e) => setDay(d.id, { rest: e.target.value })} />
								</label>
							</div>
							{d.exercises.map((ex, i) => (
								<ExerciseEditor
									key={ex.id}
									ex={ex}
									onChange={(n) => setDay(d.id, { exercises: d.exercises.map((x) => (x.id === ex.id ? n : x)) })}
									onRemove={() => setDay(d.id, { exercises: d.exercises.filter((x) => x.id !== ex.id) })}
									onMove={(dir) => setDay(d.id, { exercises: move(d.exercises, i, dir) })}
								/>
							))}
							<div className="btn-row">
								<button
									className="btn ghost sm"
									onClick={() =>
										setDay(d.id, {
											exercises: [...d.exercises, { id: uid('e'), name: 'Nuevo ejercicio', note: '', video: '', sets: 3, reps: '8 - 10', rir: '1' }],
										})
									}
								>
									+ Ejercicio
								</button>
								<button
									className="btn danger sm"
									onClick={async () => {
										if (!(await ask(`¿Eliminar ${d.name}?`))) return;
										onChange({
											...value,
											days: value.days.filter((x) => x.id !== d.id),
											schedule: value.schedule.map((s) => (s === d.id ? null : s)),
										});
									}}
								>
									Eliminar día
								</button>
							</div>
						</div>
					)}
				</div>
			))}

			<button
				className="btn secondary"
				style={{ marginBottom: 14 }}
				onClick={() => {
					const id = uid('d');
					onChange({ ...value, days: [...value.days, { id, name: `Día ${value.days.length + 1}`, warmup: '', rest: "2 - 3'", exercises: [] }] });
					setOpen(id);
				}}
			>
				+ Añadir día de entreno
			</button>

			<div className="card">
				<div className="card-head">Cardio / pasos</div>
				<div className="card-body">
					{value.cardio.map((c) => (
						<div className="editor-ex" key={c.id}>
							<div className="head">
								<input value={c.name} onChange={(e) => onChange({ ...value, cardio: value.cardio.map((x) => (x.id === c.id ? { ...x, name: e.target.value } : x)) })} />
								<button className="icon-btn" onClick={() => onChange({ ...value, cardio: value.cardio.filter((x) => x.id !== c.id) })}>
									✕
								</button>
							</div>
							<div className="grid-2" style={{ marginTop: 6 }}>
								<label className="full">
									<span>Dosis</span>
									<input value={c.dose} onChange={(e) => onChange({ ...value, cardio: value.cardio.map((x) => (x.id === c.id ? { ...x, dose: e.target.value } : x)) })} />
								</label>
								<label className="full">
									<span>Indicaciones</span>
									<input value={c.notes} onChange={(e) => onChange({ ...value, cardio: value.cardio.map((x) => (x.id === c.id ? { ...x, notes: e.target.value } : x)) })} />
								</label>
							</div>
						</div>
					))}
					<button className="btn ghost sm" onClick={() => onChange({ ...value, cardio: [...value.cardio, { id: uid('c'), name: 'Cardio', dose: '', notes: '' }] })}>
						+ Cardio
					</button>
				</div>
			</div>
		</>
	);
}

function ExerciseEditor({ ex, onChange, onRemove, onMove }: { ex: Exercise; onChange: (e: Exercise) => void; onRemove: () => void; onMove: (d: number) => void }) {
	const set = (patch: Partial<Exercise>) => onChange({ ...ex, ...patch });
	return (
		<div className="editor-ex">
			<div className="head">
				<input
					value={ex.name}
					list="catalogo-ejercicios"
					onChange={(e) => {
						const name = e.target.value;
						// Si el nombre está en el catálogo y no hay vídeo propio, se pone el del catálogo
						const auto = catalogVideo(name);
						set(auto && (!ex.video || ex.video === catalogVideo(ex.name)) ? { name, video: auto } : { name });
					}}
					placeholder="Escribe o elige del catálogo"
				/>
				<button className="icon-btn" onClick={() => onMove(-1)} aria-label="Subir">
					↑
				</button>
				<button className="icon-btn" onClick={() => onMove(1)} aria-label="Bajar">
					↓
				</button>
				<button className="icon-btn" onClick={async () => (await ask('¿Quitar ejercicio?')) && onRemove()} aria-label="Quitar">
					✕
				</button>
			</div>
			<div className="mini">
				<label>
					<span>Series</span>
					<select value={ex.sets} onChange={(e) => set({ sets: Number(e.target.value) })}>
						{[1, 2, 3, 4, 5, 6].map((n) => (
							<option key={n}>{n}</option>
						))}
					</select>
				</label>
				<label>
					<span>Reps</span>
					<input value={ex.reps} onChange={(e) => set({ reps: e.target.value })} />
				</label>
				<label>
					<span>RIR</span>
					<input value={ex.rir} onChange={(e) => set({ rir: e.target.value })} />
				</label>
			</div>
			<label className="full">
				<span>Indicación</span>
				<input value={ex.note} onChange={(e) => set({ note: e.target.value })} placeholder="Ej.: banco 45º" />
			</label>
			<label className="full">
				<span>
					Enlace al vídeo{' '}
					{videoFor(ex) && (
						<a href={videoFor(ex)} target="_blank" rel="noreferrer" style={{ textTransform: 'none' }}>
							▶ ver
						</a>
					)}
				</span>
				<input value={ex.video} onChange={(e) => set({ video: e.target.value })} placeholder={catalogVideo(ex.name) ? 'Del catálogo (se usa automáticamente)' : 'https://…'} />
			</label>
		</div>
	);
}

// ---------------- Dieta ----------------

export function FoodSelect({ value, onChange }: { value: string; onChange: (id: string) => void }) {
	const groups = Object.keys(GROUP_LABEL) as FoodGroup[];
	return (
		<select value={value} onChange={(e) => onChange(e.target.value)}>
			{!value && <option value="">Elige alimento…</option>}
			{groups.map((g) => (
				<optgroup key={g} label={GROUP_LABEL[g]}>
					{FOODS.filter((f) => f.group === g)
						.sort((a, b) => a.name.localeCompare(b.name))
						.map((f) => (
							<option key={f.id} value={f.id}>
								{f.name}
							</option>
						))}
				</optgroup>
			))}
		</select>
	);
}

function ItemsEditor({ items, onChange }: { items: MealItem[]; onChange: (i: MealItem[]) => void }) {
	return (
		<>
			{items.map((it, i) => (
				<div key={i} style={{ display: 'flex', gap: 6, marginTop: 6, alignItems: 'center' }}>
					<div style={{ flex: 1, minWidth: 0 }}>
						<FoodSelect value={it.foodId} onChange={(id) => onChange(items.map((x, j) => (j === i ? { ...x, foodId: id } : x)))} />
					</div>
					<input
						style={{ width: 70 }}
						inputMode="decimal"
						value={it.grams}
						onChange={(e) => onChange(items.map((x, j) => (j === i ? { ...x, grams: Number(e.target.value.replace(',', '.')) || 0 } : x)))}
					/>
					<span className="muted">g</span>
					<button className="icon-btn" onClick={() => onChange(items.filter((_, j) => j !== i))}>
						✕
					</button>
				</div>
			))}
			<button className="btn ghost sm" style={{ marginTop: 8 }} onClick={() => onChange([...items, { foodId: '', grams: 100 }])}>
				+ Alimento
			</button>
		</>
	);
}

export function DietEditor({ value, onChange }: { value: Diet; onChange: (d: Diet) => void }) {
	const setMeal = (id: string, patch: Partial<Diet['meals'][number]>) => onChange({ ...value, meals: value.meals.map((m) => (m.id === id ? { ...m, ...patch } : m)) });
	return (
		<>
			<div className="card">
				<div className="card-head">Objetivos diarios</div>
				<div className="card-body">
					<div className="grid-2">
						{(
							[
								['kcal', 'Calorías'],
								['protein', 'Proteína (g)'],
								['carbs', 'Hidratos (g)'],
								['fat', 'Grasas (g)'],
							] as const
						).map(([k, l]) => (
							<label className="field" key={k}>
								<span>{l}</span>
								<input inputMode="numeric" value={value[k]} onChange={(e) => onChange({ ...value, [k]: Number(e.target.value) || 0 })} />
							</label>
						))}
					</div>
				</div>
			</div>

			{value.meals.map((m, mi) => (
				<div className="card" key={m.id}>
					<div className="card-head">
						{m.name || 'Comida'}
						<span>
							<button className="icon-btn" style={{ color: '#fff' }} onClick={() => onChange({ ...value, meals: move(value.meals, mi, -1) })}>
								↑
							</button>
							<button className="icon-btn" style={{ color: '#fff' }} onClick={() => onChange({ ...value, meals: move(value.meals, mi, 1) })}>
								↓
							</button>
							<button className="icon-btn" style={{ color: '#fff' }} onClick={async () => (await ask(`¿Eliminar ${m.name}?`)) && onChange({ ...value, meals: value.meals.filter((x) => x.id !== m.id) })}>
								✕
							</button>
						</span>
					</div>
					<div className="card-body">
						<div className="grid-2">
							<label className="field">
								<span>Nombre</span>
								<input value={m.name} onChange={(e) => setMeal(m.id, { name: e.target.value })} />
							</label>
							<label className="field">
								<span>Hora</span>
								<input type="time" value={m.time} onChange={(e) => setMeal(m.id, { time: e.target.value })} />
							</label>
						</div>
						<label className="field">
							<span>Indicación</span>
							<input value={m.note} onChange={(e) => setMeal(m.id, { note: e.target.value })} />
						</label>
						{m.options.map((o) => {
							const mac = macrosOf(o.items);
							return (
								<div className="editor-ex" key={o.id}>
									<div className="head">
										<input value={o.name} onChange={(e) => setMeal(m.id, { options: m.options.map((x) => (x.id === o.id ? { ...x, name: e.target.value } : x)) })} />
										<button className="icon-btn" onClick={async () => (await ask('¿Quitar opción?')) && setMeal(m.id, { options: m.options.filter((x) => x.id !== o.id) })}>
											✕
										</button>
									</div>
									<ItemsEditor items={o.items} onChange={(items) => setMeal(m.id, { options: m.options.map((x) => (x.id === o.id ? { ...x, items } : x)) })} />
									<div className="muted" style={{ marginTop: 6 }}>
										{mac.kcal} kcal · P {mac.p} · H {mac.c} · G {mac.f}
									</div>
								</div>
							);
						})}
						<button className="btn ghost sm" onClick={() => setMeal(m.id, { options: [...m.options, { id: uid('o'), name: `Opción ${m.options.length + 1}`, items: [] }] })}>
							+ Opción
						</button>
					</div>
				</div>
			))}
			<button
				className="btn secondary"
				style={{ marginBottom: 14 }}
				onClick={() => onChange({ ...value, meals: [...value.meals, { id: uid('m'), name: 'Nueva comida', time: '12:00', note: '', options: [{ id: uid('o'), name: 'Opción 1', items: [] }] }] })}
			>
				+ Añadir comida
			</button>
		</>
	);
}

// ---------------- Equivalencias ----------------

export function EquivalencesEditor({ value, onChange }: { value: EquivalenceGroup[]; onChange: (g: EquivalenceGroup[]) => void }) {
	return (
		<>
			<p className="dark-muted">
				Cada grupo dice qué cantidades son equivalentes entre sí (p. ej. 30 g arroz = 50 g cereales). Si un cambio no está en la tabla, la app lo calcula
				automáticamente con el macro principal del alimento.
			</p>
			{value.map((g) => (
				<div className="card" key={g.id}>
					<div className="card-body">
						<div className="editor-ex" style={{ margin: 0 }}>
							<div className="head">
								<input value={g.name} onChange={(e) => onChange(value.map((x) => (x.id === g.id ? { ...x, name: e.target.value } : x)))} />
								<button className="icon-btn" onClick={async () => (await ask('¿Borrar grupo?')) && onChange(value.filter((x) => x.id !== g.id))}>
									✕
								</button>
							</div>
							<ItemsEditor items={g.items} onChange={(items) => onChange(value.map((x) => (x.id === g.id ? { ...x, items } : x)))} />
							<div className="muted" style={{ marginTop: 6 }}>
								{g.items
									.filter((i) => i.foodId)
									.map((i) => `${i.grams} g ${getFood(i.foodId)?.name ?? ''}`)
									.join(' = ')}
							</div>
						</div>
					</div>
				</div>
			))}
			<button className="btn secondary" onClick={() => onChange([...value, { id: uid('q'), name: `Grupo ${value.length + 1}`, items: [] }])}>
				+ Nuevo grupo de equivalencias
			</button>
		</>
	);
}

// ---------------- Hábitos ----------------

export function HabitsEditor({ value, onChange }: { value: Habits; onChange: (h: Habits) => void }) {
	const set = (id: string, patch: Partial<Habit>) => onChange({ ...value, items: value.items.map((h) => (h.id === id ? { ...h, ...patch } : h)) });
	return (
		<>
			<div className="card">
				<div className="card-head">Objetivo</div>
				<div className="card-body">
					<label className="field" style={{ margin: 0 }}>
						<span>Lo que persigue el atleta con estos hábitos</span>
						<input value={value.goal} onChange={(e) => onChange({ ...value, goal: e.target.value })} placeholder="Ej.: dormir mejor y reducir el móvil" />
					</label>
				</div>
			</div>
			<div className="card">
				<div className="card-head">
					Hábitos diarios
					<span className="pill">{value.items.length}/5</span>
				</div>
				<div className="card-body">
					{value.items.map((h, i) => (
						<div className="editor-ex" key={h.id} style={{ borderLeft: `6px solid ${HABIT_COLORS[i % HABIT_COLORS.length]}` }}>
							<div className="head">
								<input value={h.emoji} onChange={(e) => set(h.id, { emoji: e.target.value })} style={{ flex: 'none', width: 52, textAlign: 'center' }} aria-label="Emoji" />
								<span style={{ flex: 1 }} className="muted">
									Hábito {i + 1}
								</span>
								<button className="icon-btn" onClick={() => onChange({ ...value, items: move(value.items, i, -1) })} aria-label="Subir">
									↑
								</button>
								<button className="icon-btn" onClick={() => onChange({ ...value, items: move(value.items, i, 1) })} aria-label="Bajar">
									↓
								</button>
								<button className="icon-btn" onClick={async () => (await ask('¿Quitar este hábito? Sus marcas antiguas dejarán de contar.')) && onChange({ ...value, items: value.items.filter((x) => x.id !== h.id) })} aria-label="Quitar">
									✕
								</button>
							</div>
							<textarea
								rows={2}
								value={h.name}
								onChange={(e) => set(h.id, { name: e.target.value.replace(/\n/g, ' ') })}
								placeholder="Nombre del hábito"
								style={{ width: '100%', marginTop: 6, border: '1px solid var(--line)', borderRadius: 8, padding: 8, fontWeight: 700, resize: 'none', background: '#fff', color: 'var(--ink)' }}
							/>
						</div>
					))}
					{value.items.length < 5 && (
						<button className="btn ghost sm" onClick={() => onChange({ ...value, items: [...value.items, { id: uid('h'), emoji: '✅', name: '' }] })}>
							+ Hábito
						</button>
					)}
					<p className="muted" style={{ marginBottom: 0 }}>
						El orden decide el color y el anillo: el primero va por fuera.
					</p>
				</div>
			</div>
		</>
	);
}
