import { useEffect, useState, type ReactNode } from 'react';
import { ask, Sheet, TopBar, useToast } from '../components/ui';
import { emptyPlan } from '../data/seed';
import { useStore } from '../data/store';
import type { Diet, EquivalenceGroup, Habits, Program, User } from '../data/types';
import { ApplyTemplate, ExerciseLibrary, SaveAsTemplate, TemplateEditor, Templates } from './AdminTemplates';
import { formatShort, sessionsFor } from '../data/util';
import { DietEditor, EquivalencesEditor, HabitsEditor, ProgramEditor } from './AdminEditors';
import Progress from './Progress';

type View = { kind: 'list' } | { kind: 'user'; id: string } | { kind: 'equiv' } | { kind: 'templates'; tkind: 'program' | 'diet' } | { kind: 'template'; id: string } | { kind: 'library' };

export default function Admin() {
	const { db } = useStore();
	const [view, setView] = useState<View>({ kind: 'list' });
	const [creating, setCreating] = useState(false);
	const [q, setQ] = useState('');

	if (view.kind === 'user') return <UserDetail id={view.id} onBack={() => setView({ kind: 'list' })} />;
	if (view.kind === 'equiv') return <Equivalences onBack={() => setView({ kind: 'list' })} />;
	if (view.kind === 'templates') return <Templates kind={view.tkind} onBack={() => setView({ kind: 'list' })} onOpen={(id) => setView({ kind: 'template', id })} />;
	if (view.kind === 'template')
		return <TemplateEditor id={view.id} onBack={() => setView({ kind: 'templates', tkind: db.templates.find((t) => t.id === view.id)?.kind ?? 'program' })} />;
	if (view.kind === 'library') return <ExerciseLibrary onBack={() => setView({ kind: 'list' })} />;

	const users = db.users.filter((u) => `${u.name} ${u.email}`.toLowerCase().includes(q.toLowerCase())).sort((a, b) => a.name.localeCompare(b.name));

	return (
		<>
			<TopBar
				title="Administración"
				sub={`${db.users.filter((u) => u.isAthlete).length} atletas`}
				right={
					<button className="btn sm" onClick={() => setCreating(true)}>
						+ Usuario
					</button>
				}
			/>
			<input className="input" placeholder="Buscar usuario…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 12 }} />
			<div className="card">
				{users.map((u) => {
					const last = sessionsFor(db.sessions, u.id)[0];
					return (
						<div className="row clickable" key={u.id} onClick={() => setView({ kind: 'user', id: u.id })}>
							<div className="grow">
								<div className="name">{u.name}</div>
								<div className="muted">
									{u.email}
									{last ? ` · último entreno ${formatShort(last.date)}` : ''}
								</div>
							</div>
							{u.isAthlete && <span className="pill yellow">Atleta</span>}
							{u.isAdmin && <span className="pill dark">Admin</span>}
							<span className="chev">›</span>
						</div>
					);
				})}
			</div>

			<div className="section-label">Entreno</div>
			<div className="card">
				<div className="row clickable" onClick={() => setView({ kind: 'templates', tkind: 'program' })}>
					<div className="grow">
						<div className="name">Plantillas de entreno</div>
						<div className="muted">{db.templates.filter((t) => t.kind === 'program').length} guardadas · se asignan al dar de alta o cambiar el plan</div>
					</div>
					<span className="chev">›</span>
				</div>
				<div className="row clickable" onClick={() => setView({ kind: 'library' })}>
					<div className="grow">
						<div className="name">Biblioteca de ejercicios</div>
						<div className="muted">{db.exercises.length} ejercicios con su vídeo</div>
					</div>
					<span className="chev">›</span>
				</div>
			</div>

			<div className="section-label">Dieta</div>
			<div className="card">
				<div className="row clickable" onClick={() => setView({ kind: 'templates', tkind: 'diet' })}>
					<div className="grow">
						<div className="name">Plantillas de dieta</div>
						<div className="muted">{db.templates.filter((t) => t.kind === 'diet').length} guardadas · dietas base para asignar</div>
					</div>
					<span className="chev">›</span>
				</div>
				<div className="row clickable" onClick={() => setView({ kind: 'equiv' })}>
					<div className="grow">
						<div className="name">Tabla de equivalencias de alimentos</div>
						<div className="muted">{db.equivalences.length} grupos definidos</div>
					</div>
					<span className="chev">›</span>
				</div>
			</div>

			{creating && <CreateUser onClose={() => setCreating(false)} onCreated={() => setCreating(false)} />}
		</>
	);
}

function CreateUser({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
	const { createUser, db } = useStore();
	const athletesWithPlan = db.users.filter((u) => db.plans.some((p) => p.userId === u.id));
	const [f, setF] = useState({ name: '', email: '', phone: '', password: '', isAdmin: false, isAthlete: true, copyFrom: '', dietFrom: '' });
	const programTpls = db.templates.filter((t) => t.kind === 'program');
	const dietTpls = db.templates.filter((t) => t.kind === 'diet');
	const withDiet = db.users.filter((u) => db.plans.some((p) => p.userId === u.id && p.diet.meals.length));
	const [error, setError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);

	async function submit() {
		setBusy(true);
		const [kind, ref] = f.copyFrom.split(':');
		const err = await createUser({ ...f, copyFrom: kind === 'user' ? ref : undefined, templateId: kind === 'tpl' ? ref : undefined, dietFrom: f.dietFrom || undefined });
		setBusy(false);
		if (err) setError(err);
		else onCreated();
	}

	return (
		<Sheet title="Nuevo usuario" onClose={onClose}>
			{error && <div className="error">{error}</div>}
			<label className="field">
				<span>Nombre completo</span>
				<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
			</label>
			<label className="field">
				<span>Email (usuario)</span>
				<input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
			</label>
			<div className="grid-2">
				<label className="field">
					<span>Teléfono</span>
					<input type="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
				</label>
				<label className="field">
					<span>Contraseña inicial</span>
					<input value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} placeholder="mín. 6" />
				</label>
			</div>
			<label className="check">
				<input type="checkbox" checked={f.isAthlete} onChange={(e) => setF({ ...f, isAthlete: e.target.checked })} /> Es atleta (tiene entreno y dieta)
			</label>
			<label className="check">
				<input type="checkbox" checked={f.isAdmin} onChange={(e) => setF({ ...f, isAdmin: e.target.checked })} /> Es administrador
			</label>
			{f.isAthlete && (
				<label className="field" style={{ marginTop: 8 }}>
					<span>Entreno inicial</span>
					<select value={f.copyFrom} onChange={(e) => setF({ ...f, copyFrom: e.target.value })}>
						<option value="">Plan vacío</option>
						{programTpls.length > 0 && (
							<optgroup label="Plantillas de entreno">
								{programTpls.map((t) => (
									<option key={t.id} value={`tpl:${t.id}`}>
										{t.name}
									</option>
								))}
							</optgroup>
						)}
						<optgroup label="Copiar el plan de otro atleta">
							{athletesWithPlan.map((u) => (
								<option key={u.id} value={`user:${u.id}`}>
									{u.name}
								</option>
							))}
						</optgroup>
					</select>
				</label>
			)}
			{f.isAthlete && (
				<label className="field">
					<span>Dieta inicial</span>
					<select value={f.dietFrom} onChange={(e) => setF({ ...f, dietFrom: e.target.value })}>
						<option value="">{f.copyFrom.startsWith('user:') ? 'La del atleta copiado' : 'Sin dieta'}</option>
						{dietTpls.length > 0 && (
							<optgroup label="Plantillas de dieta">
								{dietTpls.map((t) => (
									<option key={t.id} value={`tpl:${t.id}`}>
										{t.name}
									</option>
								))}
							</optgroup>
						)}
						{withDiet.length > 0 && (
							<optgroup label="Copiar la dieta de otro atleta">
								{withDiet.map((u) => (
									<option key={u.id} value={`user:${u.id}`}>
										{u.name}
									</option>
								))}
							</optgroup>
						)}
					</select>
				</label>
			)}
			<button className="btn" onClick={submit} disabled={busy}>
				{busy ? 'Creando…' : 'Crear usuario'}
			</button>
		</Sheet>
	);
}

function UserDetail({ id, onBack }: { id: string; onBack: () => void }) {
	const store = useStore();
	const user = store.db.users.find((u) => u.id === id);
	const [tab, setTab] = useState<'data' | 'train' | 'diet' | 'habits' | 'history' | 'progress'>('data');
	const [version, setVersion] = useState(0);
	const [saveTpl, setSaveTpl] = useState<Program | null>(null);
	const [saveDietTpl, setSaveDietTpl] = useState<Diet | null>(null);
	if (!user) return null;
	const plan = store.planOf(id);

	return (
		<>
			<TopBar title={user.name} sub={user.email} onBack={onBack} />
			<div className="tabs">
				{(
					[
						['data', 'Datos'],
						['train', 'Entreno'],
						['diet', 'Dieta'],
						['habits', 'Hábitos'],
						['history', 'Historial'],
						['progress', 'Progreso'],
					] as const
				).map(([k, l]) => (
					<button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>
						{l}
					</button>
				))}
			</div>
			{tab === 'data' && <UserData user={user} onDeleted={onBack} />}
			{(tab === 'train' || tab === 'diet' || tab === 'habits') &&
				(plan ? (
					tab === 'habits' ? (
						<PlanPart<Habits> key={`h${id}`} initial={plan.habits ?? { goal: '', items: [] }} onSave={(habits) => store.savePlan({ ...store.planOf(id)!, habits })} Editor={HabitsEditor} />
					) : tab === 'train' ? (
						<>
							<ApplyTemplate
								kind="program"
								userId={id}
								onApplied={(program) => {
									store.savePlan({ ...store.planOf(id)!, program: program as Program });
									setVersion((v) => v + 1);
								}}
							/>
							<PlanPart<Program>
								key={`t${id}-${version}`}
								initial={plan.program}
								onSave={(program) => store.savePlan({ ...store.planOf(id)!, program })}
								Editor={ProgramEditor}
								footer={(draft) => (
									<button className="btn secondary" style={{ marginBottom: 14 }} onClick={() => setSaveTpl(draft)}>
										⧉ Guardar este entreno también como plantilla
									</button>
								)}
							/>
							{saveTpl && <SaveAsTemplate kind="program" program={saveTpl} suggestedName={saveTpl.name} onClose={() => setSaveTpl(null)} />}
						</>
					) : (
						<>
							<ApplyTemplate
								kind="diet"
								userId={id}
								onApplied={(diet) => {
									store.savePlan({ ...store.planOf(id)!, diet: diet as Diet });
									setVersion((v) => v + 1);
								}}
							/>
							<PlanPart<Diet>
								key={`d${id}-${version}`}
								initial={plan.diet}
								onSave={(diet) => store.savePlan({ ...store.planOf(id)!, diet })}
								Editor={DietEditor}
								footer={(draft) => (
									<button className="btn secondary" style={{ marginBottom: 14 }} onClick={() => setSaveDietTpl(draft)}>
										⧉ Guardar esta dieta también como plantilla
									</button>
								)}
							/>
							{saveDietTpl && (
								<SaveAsTemplate kind="diet" diet={saveDietTpl} suggestedName={`${user.name.split(' ')[0]} · ${saveDietTpl.kcal} kcal`} onClose={() => setSaveDietTpl(null)} />
							)}
						</>
					)
				) : (
					<div className="card">
						<div className="card-body">
							<p className="muted">Este usuario no tiene plan.</p>
							<button
								className="btn"
								onClick={() => {
									store.updateUser(id, { isAthlete: true });
									store.savePlan(emptyPlan(id));
								}}
							>
								Crear plan de atleta
							</button>
						</div>
					</div>
				))}
			{tab === 'history' && <History userId={id} />}
			{tab === 'progress' && <Progress userId={id} />}
		</>
	);
}

function PlanPart<T>({
	initial,
	onSave,
	Editor,
	footer,
}: {
	initial: T;
	onSave: (v: T) => void;
	Editor: (p: { value: T; onChange: (v: T) => void }) => ReactNode;
	footer?: (draft: T) => ReactNode;
}) {
	const [draft, setDraft] = useState<T>(() => structuredClone(initial));
	const [dirty, setDirty] = useState(false);
	const [toast, show] = useToast();
	return (
		<>
			<Editor
				value={draft}
				onChange={(v) => {
					setDraft(v);
					setDirty(true);
				}}
			/>
			{footer?.(draft)}
			{dirty && <div style={{ position: 'sticky', bottom: 'calc(var(--nav-h) + 10px + env(safe-area-inset-bottom))', zIndex: 5 }}>
				<button
					className="btn"
					disabled={!dirty}
					onClick={() => {
						onSave(draft);
						setDirty(false);
						show('Cambios guardados');
					}}
				>
					Guardar cambios
				</button>
			</div>}
			{toast}
		</>
	);
}

function UserData({ user, onDeleted }: { user: User; onDeleted: () => void }) {
	const { updateUser, setUserPassword, deleteUser, me } = useStore();
	const [f, setF] = useState(user);
	const [pw, setPw] = useState('');
	const [msg, setMsg] = useState<string | null>(null);
	const [toast, show] = useToast();
	useEffect(() => {
		setF(user);
	}, [user]);

	return (
		<>
			{msg && <div className="error">{msg}</div>}
			<div className="card">
				<div className="card-head">Datos</div>
				<div className="card-body">
					<label className="field">
						<span>Nombre</span>
						<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
					</label>
					<label className="field">
						<span>Email</span>
						<input value={f.email} disabled />
					</label>
					<label className="field">
						<span>Teléfono</span>
						<input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
					</label>
					<label className="check">
						<input type="checkbox" checked={f.isAthlete} onChange={(e) => setF({ ...f, isAthlete: e.target.checked })} /> Atleta
					</label>
					<label className="check">
						<input type="checkbox" checked={f.isAdmin} disabled={user.id === me!.id} onChange={(e) => setF({ ...f, isAdmin: e.target.checked })} /> Administrador
					</label>
					<button
						className="btn dark"
						style={{ marginTop: 8 }}
						onClick={() => {
							updateUser(user.id, { name: f.name, phone: f.phone, isAdmin: f.isAdmin, isAthlete: f.isAthlete });
							show('Guardado');
						}}
					>
						Guardar
					</button>
				</div>
			</div>
			<div className="card">
				<div className="card-head">Restablecer contraseña</div>
				<div className="card-body">
					<label className="field">
						<span>Nueva contraseña</span>
						<input value={pw} onChange={(e) => setPw(e.target.value)} placeholder="mín. 6 caracteres" />
					</label>
					<button
						className="btn dark"
						disabled={pw.length < 6}
						onClick={async () => {
							const err = await setUserPassword(user.id, pw);
							if (err) return setMsg(err);
							setMsg(null);
							setPw('');
							show('Contraseña cambiada');
						}}
					>
						Cambiar contraseña
					</button>
				</div>
			</div>
			{user.id !== me!.id && (
				<button
					className="btn danger"
					onClick={async () => {
						if (await ask(`¿Eliminar a ${user.name} y todos sus datos?`)) {
							const err = await deleteUser(user.id);
							if (err) setMsg(err);
							else onDeleted();
						}
					}}
				>
					Eliminar usuario
				</button>
			)}
			{toast}
		</>
	);
}

function History({ userId }: { userId: string }) {
	const { db, deleteSession } = useStore();
	const list = sessionsFor(db.sessions, userId);
	return (
		<div className="card">
			{list.length === 0 && <div className="empty">Sin entrenos registrados</div>}
			{list.map((s) => (
				<details key={s.id} className="row" style={{ display: 'block' }}>
					<summary style={{ cursor: 'pointer', display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
						<b style={{ flex: 1 }}>
							{formatShort(s.date)} · {s.dayName}
						</b>
						{s.readiness != null && <span className="pill">R {s.readiness}</span>}
						{s.fatigue != null && <span className="pill dark">F {s.fatigue}</span>}
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
						<button className="btn danger sm" onClick={async () => (await ask('¿Borrar este entreno?')) && deleteSession(s.id)}>
							Borrar entreno
						</button>
					</div>
				</details>
			))}
		</div>
	);
}

function Equivalences({ onBack }: { onBack: () => void }) {
	const { db, saveEquivalences } = useStore();
	return (
		<>
			<TopBar title="Equivalencias" onBack={onBack} />
			<PlanPart<EquivalenceGroup[]> initial={db.equivalences} onSave={saveEquivalences} Editor={EquivalencesEditor} />
		</>
	);
}
