import { useState } from 'react';
import { ask, Sheet, TopBar, useToast } from '../components/ui';
import { useStore } from '../data/store';
import type { Diet, LibraryExercise, Program, Template } from '../data/types';
import { DietEditor, ProgramEditor } from './AdminEditors';

export type TemplateKind = Template['kind'];

const emptyProgram = (name: string): Program => ({ name, days: [], schedule: [null, null, null, null, null, null, null], cardio: [] });
const emptyDiet = (): Diet => ({ kcal: 0, protein: 0, carbs: 0, fat: 0, meals: [] });
const summary = (t: Pick<Template, 'kind' | 'program' | 'diet'>) =>
	t.kind === 'diet'
		? `${t.diet?.kcal ?? 0} kcal · ${t.diet?.meals.length ?? 0} comidas`
		: `${t.program?.days.length ?? 0} ${t.program?.days.length === 1 ? 'día' : 'días'} · ${t.program?.days.reduce((a, d) => a + d.exercises.length, 0) ?? 0} ejercicios`;

export const KIND_TEXT: Record<TemplateKind, { title: string; one: string; example: string }> = {
	program: { title: 'Plantillas de entreno', one: 'entreno', example: 'Ej.: Mujer · glúteo · 4 días' },
	diet: { title: 'Plantillas de dieta', one: 'dieta', example: 'Ej.: Mujer · 1800 kcal' },
};

/** Plan de un atleta según el tipo de plantilla. */
const fromPlan = (kind: TemplateKind, p?: { program: Program; diet: Diet }) => (kind === 'diet' ? p?.diet : p?.program);
const hasContent = (kind: TemplateKind, p: { program: Program; diet: Diet }) => (kind === 'diet' ? p.diet.meals.length > 0 : p.program.days.length > 0);

// ---------------- Plantillas ----------------

export function Templates({ kind, onBack, onOpen }: { kind: TemplateKind; onBack: () => void; onOpen: (id: string) => void }) {
	const { db } = useStore();
	const [creating, setCreating] = useState(false);
	const list = db.templates.filter((t) => t.kind === kind);
	return (
		<>
			<TopBar
				title={KIND_TEXT[kind].title}
				sub={kind === 'diet' ? 'Dietas base para nuevos atletas' : 'Rutinas base para nuevos atletas'}
				onBack={onBack}
				right={
					<button className="btn sm" onClick={() => setCreating(true)}>
						+ Plantilla
					</button>
				}
			/>
			<p className="dark-muted" style={{ marginTop: 0 }}>
				Una plantilla es el punto de partida: al asignarla a un atleta se le copia, y lo que cambies después en ese atleta no afecta a la plantilla ni a nadie más.
			</p>
			<div className="card">
				{list.length === 0 && <div className="empty">Aún no hay plantillas. Crea una o guarda la {KIND_TEXT[kind].one} de un atleta como plantilla.</div>}
				{list.map((t) => (
					<div className="row clickable" key={t.id} onClick={() => onOpen(t.id)}>
						<div className="grow">
							<div className="name">{t.name}</div>
							<div className="muted">{summary(t)}</div>
						</div>
						<span className="chev">›</span>
					</div>
				))}
			</div>
			{creating && <NewTemplate kind={kind} onClose={() => setCreating(false)} onCreated={(id) => onOpen(id)} />}
		</>
	);
}

function NewTemplate({ kind, onClose, onCreated }: { kind: TemplateKind; onClose: () => void; onCreated: (id: string) => void }) {
	const { db, saveTemplate } = useStore();
	const [name, setName] = useState('');
	const [from, setFrom] = useState('');
	const athletes = db.users.filter((u) => db.plans.some((p) => p.userId === u.id && hasContent(kind, p)));
	const same = db.templates.filter((t) => t.kind === kind);
	return (
		<Sheet title={`Nueva plantilla de ${KIND_TEXT[kind].one}`} onClose={onClose}>
			<label className="field">
				<span>Nombre</span>
				<input value={name} onChange={(e) => setName(e.target.value)} placeholder={KIND_TEXT[kind].example} />
			</label>
			<label className="field">
				<span>Empezar desde</span>
				<select value={from} onChange={(e) => setFrom(e.target.value)}>
					<option value="">En blanco</option>
					{same.length > 0 && (
						<optgroup label="Duplicar plantilla">
							{same.map((t) => (
								<option key={t.id} value={`tpl:${t.id}`}>
									{t.name}
								</option>
							))}
						</optgroup>
					)}
					<optgroup label={`${kind === 'diet' ? 'Dieta' : 'Entreno'} de un atleta`}>
						{athletes.map((u) => (
							<option key={u.id} value={`user:${u.id}`}>
								{u.name}
							</option>
						))}
					</optgroup>
				</select>
			</label>
			<button
				className="btn"
				disabled={!name.trim()}
				onClick={() => {
					const [k, ref] = from.split(':');
					const tpl = k === 'tpl' ? db.templates.find((t) => t.id === ref) : undefined;
					const plan = k === 'user' ? db.plans.find((p) => p.userId === ref) : undefined;
					const id = crypto.randomUUID();
					const n = name.trim();
					if (kind === 'diet') {
						const base = tpl?.diet ?? plan?.diet;
						saveTemplate({ id, name: n, kind, diet: base ? structuredClone(base) : emptyDiet() });
					} else {
						const base = tpl?.program ?? plan?.program;
						saveTemplate({ id, name: n, kind, program: base ? { ...structuredClone(base), name: n } : emptyProgram(n) });
					}
					onClose();
					onCreated(id);
				}}
			>
				Crear y editar
			</button>
		</Sheet>
	);
}

export function TemplateEditor({ id, onBack }: { id: string; onBack: () => void }) {
	const { db, saveTemplate, deleteTemplate } = useStore();
	const tpl = db.templates.find((t) => t.id === id);
	const [name, setName] = useState(tpl?.name ?? '');
	const [program, setProgram] = useState<Program>(() => structuredClone(tpl?.program ?? emptyProgram('')));
	const [diet, setDiet] = useState<Diet>(() => structuredClone(tpl?.diet ?? emptyDiet()));
	const [dirty, setDirty] = useState(false);
	const [toast, show] = useToast();
	if (!tpl) return null;
	const kind = tpl.kind;
	return (
		<>
			<TopBar title={tpl.name} sub={`Plantilla de ${KIND_TEXT[kind].one} · ${summary({ kind, program, diet })}`} onBack={onBack} />
			<div className="card">
				<div className="card-body">
					<label className="field" style={{ margin: 0 }}>
						<span>Nombre de la plantilla</span>
						<input
							value={name}
							onChange={(e) => {
								setName(e.target.value);
								setDirty(true);
							}}
						/>
					</label>
				</div>
			</div>
			{kind === 'diet' ? (
				<DietEditor
					value={diet}
					onChange={(d) => {
						setDiet(d);
						setDirty(true);
					}}
				/>
			) : (
				<ProgramEditor
					value={program}
					onChange={(p) => {
						setProgram(p);
						setDirty(true);
					}}
				/>
			)}
			<button
				className="btn danger"
				style={{ marginBottom: 14 }}
				onClick={async () => {
					if (await ask(`¿Eliminar la plantilla «${tpl.name}»? Los atletas que la usan no cambian.`)) {
						deleteTemplate(tpl.id);
						onBack();
					}
				}}
			>
				Eliminar plantilla
			</button>
			{dirty && (
				<div style={{ position: 'sticky', bottom: 'calc(var(--nav-h) + 10px + env(safe-area-inset-bottom))', zIndex: 5 }}>
					<button
						className="btn"
						disabled={!name.trim()}
						onClick={() => {
							saveTemplate(kind === 'diet' ? { id: tpl.id, name: name.trim(), kind, diet } : { id: tpl.id, name: name.trim(), kind, program });
							setDirty(false);
							show('Plantilla guardada');
						}}
					>
						Guardar plantilla
					</button>
				</div>
			)}
			{toast}
		</>
	);
}

/** Guardar el entreno o la dieta de un atleta como plantilla nueva o sustituyendo una existente. */
export function SaveAsTemplate({ kind, program, diet, suggestedName, onClose }: { kind: TemplateKind; program?: Program; diet?: Diet; suggestedName: string; onClose: () => void }) {
	const { db, saveTemplate } = useStore();
	const [name, setName] = useState(suggestedName);
	const [target, setTarget] = useState('new');
	const [done, setDone] = useState(false);
	const same = db.templates.filter((t) => t.kind === kind);
	return (
		<Sheet title={`Guardar como plantilla de ${KIND_TEXT[kind].one}`} onClose={onClose}>
			{done ? (
				<>
					<div className="ok">Plantilla guardada. Ya puedes elegirla al dar de alta un atleta o al cambiar su plan.</div>
					<button className="btn" onClick={onClose}>
						Listo
					</button>
				</>
			) : (
				<>
					<label className="field">
						<span>Guardar en</span>
						<select value={target} onChange={(e) => setTarget(e.target.value)}>
							<option value="new">Plantilla nueva</option>
							{same.map((t) => (
								<option key={t.id} value={t.id}>
									Sustituir «{t.name}»
								</option>
							))}
						</select>
					</label>
					{target === 'new' && (
						<label className="field">
							<span>Nombre</span>
							<input value={name} onChange={(e) => setName(e.target.value)} placeholder={KIND_TEXT[kind].example} />
						</label>
					)}
					<button
						className="btn"
						disabled={target === 'new' && !name.trim()}
						onClick={async () => {
							const existing = same.find((t) => t.id === target);
							if (existing && !(await ask(`Se sustituirá el contenido de «${existing.name}». ¿Seguir?`))) return;
							const finalName = existing ? existing.name : name.trim();
							const id = existing?.id ?? crypto.randomUUID();
							if (kind === 'diet') saveTemplate({ id, name: finalName, kind, diet: structuredClone(diet!) });
							else saveTemplate({ id, name: finalName, kind, program: { ...structuredClone(program!), name: finalName } });
							setDone(true);
						}}
					>
						Guardar plantilla
					</button>
					<p className="muted" style={{ marginBottom: 0 }}>
						Guarda la versión que ves ahora en pantalla (aunque no hayas pulsado «Guardar cambios» del atleta).
					</p>
				</>
			)}
		</Sheet>
	);
}

/** Cambiar el entreno o la dieta de un atleta partiendo de una plantilla o del plan de otro atleta. */
export function ApplyTemplate({ kind, userId, onApplied }: { kind: TemplateKind; userId: string; onApplied: (v: Program | Diet) => void }) {
	const { db } = useStore();
	const [src, setSrc] = useState('');
	const [toast, show] = useToast();
	const same = db.templates.filter((t) => t.kind === kind);
	const others = db.users.filter((u) => u.id !== userId && db.plans.some((p) => p.userId === u.id && hasContent(kind, p)));
	const name = db.users.find((u) => u.id === userId)?.name ?? '';
	const apply = async () => {
		const [k, ref] = src.split(':');
		const value = k === 'tpl' ? (kind === 'diet' ? same.find((t) => t.id === ref)?.diet : same.find((t) => t.id === ref)?.program) : fromPlan(kind, db.plans.find((p) => p.userId === ref));
		if (!value) return;
		if (!(await ask(`Se sustituirá ${kind === 'diet' ? 'la dieta' : 'el entreno'} actual de ${name} por ${kind === 'diet' ? 'la elegida' : 'el elegido'}.${kind === 'program' ? ' Su historial no se borra.' : ''} ¿Seguir?`))) return;
		onApplied(structuredClone(value));
		setSrc('');
		show(kind === 'diet' ? 'Dieta cambiada' : 'Entreno cambiado');
	};
	return (
		<div className="card">
			<div className="card-head">Partir de una plantilla</div>
			<div className="card-body">
				<div style={{ display: 'flex', gap: 8 }}>
					<select className="input" value={src} onChange={(e) => setSrc(e.target.value)} style={{ flex: 1, minWidth: 0 }}>
						<option value="">Elige plantilla o atleta…</option>
						{same.length > 0 && (
							<optgroup label="Plantillas">
								{same.map((t) => (
									<option key={t.id} value={`tpl:${t.id}`}>
										{t.name}
									</option>
								))}
							</optgroup>
						)}
						{others.length > 0 && (
							<optgroup label="Copiar de otro atleta">
								{others.map((u) => (
									<option key={u.id} value={`user:${u.id}`}>
										{u.name}
									</option>
								))}
							</optgroup>
						)}
					</select>
					<button className="btn sm" disabled={!src} onClick={apply}>
						Aplicar
					</button>
				</div>
				<p className="muted" style={{ margin: '8px 0 0' }}>
					La plantilla es solo el punto de partida: lo que cambies después es solo de {name.split(' ')[0]}.
				</p>
			</div>
			{toast}
		</div>
	);
}

// ---------------- Biblioteca de ejercicios ----------------

export function ExerciseLibrary({ onBack }: { onBack: () => void }) {
	const { db } = useStore();
	const [q, setQ] = useState('');
	const [editing, setEditing] = useState<LibraryExercise | null>(null);
	const norm = (s: string) =>
		s
			.normalize('NFD')
			.replace(/[̀-ͯ]/g, '')
			.toLowerCase();
	const list = db.exercises.filter((e) => norm(e.name).includes(norm(q)));
	return (
		<>
			<TopBar
				title="Biblioteca"
				sub={`${db.exercises.length} ejercicios`}
				onBack={onBack}
				right={
					<button className="btn sm" onClick={() => setEditing({ id: '', name: q.trim(), video: '' })}>
						+ Ejercicio
					</button>
				}
			/>
			<input className="input" placeholder="Buscar ejercicio…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 12 }} />
			<div className="card">
				{list.length === 0 && (
					<div className="empty">
						No hay ningún ejercicio que se llame así.
						<div style={{ marginTop: 10 }}>
							<button className="btn sm" onClick={() => setEditing({ id: '', name: q.trim(), video: '' })}>
								Añadir «{q.trim() || 'nuevo'}»
							</button>
						</div>
					</div>
				)}
				{list.map((e) => (
					<div className="row clickable" key={e.id} onClick={() => setEditing(e)}>
						<div className="grow">
							<div className="name">{e.name}</div>
							<div className="muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
								{e.video || 'Sin vídeo'}
							</div>
						</div>
						{e.video && (
							<a href={e.video} target="_blank" rel="noreferrer" onClick={(ev) => ev.stopPropagation()} className="video-link" style={{ color: '#c62828', fontWeight: 700 }}>
								▶
							</a>
						)}
						<span className="chev">›</span>
					</div>
				))}
			</div>
			{editing && <EditExercise ex={editing} onClose={() => setEditing(null)} />}
		</>
	);
}

function EditExercise({ ex, onClose }: { ex: LibraryExercise; onClose: () => void }) {
	const { db, saveExercise, deleteExercise } = useStore();
	const [name, setName] = useState(ex.name);
	const [video, setVideo] = useState(ex.video);
	const duplicate = db.exercises.some((e) => e.id !== ex.id && e.name.trim().toLowerCase() === name.trim().toLowerCase());
	const validVideo = !video.trim() || /^https?:\/\//i.test(video.trim());
	return (
		<Sheet title={ex.id ? 'Editar ejercicio' : 'Nuevo ejercicio'} onClose={onClose}>
			{duplicate && <div className="error">Ya hay un ejercicio con ese nombre.</div>}
			<label className="field">
				<span>Nombre</span>
				<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Remo máquina de pie" />
			</label>
			<label className="field">
				<span>Enlace al vídeo (YouTube u otro)</span>
				<input value={video} onChange={(e) => setVideo(e.target.value)} placeholder="https://youtube.com/shorts/…" inputMode="url" />
			</label>
			{!validVideo && <div className="error">El enlace debe empezar por https://</div>}
			{video.trim() && validVideo && (
				<p style={{ marginTop: -4 }}>
					<a href={video.trim()} target="_blank" rel="noreferrer">
						▶ Probar el vídeo
					</a>
				</p>
			)}
			<button
				className="btn"
				disabled={!name.trim() || duplicate || !validVideo}
				onClick={() => {
					saveExercise({ id: ex.id || crypto.randomUUID(), name: name.trim(), video: video.trim() });
					onClose();
				}}
			>
				Guardar
			</button>
			<p className="muted">Los planes que usan este nombre de ejercicio mostrarán el vídeo nuevo automáticamente.</p>
			{ex.id && (
				<button
					className="btn danger"
					onClick={async () => {
						if (await ask(`¿Quitar «${ex.name}» de la biblioteca? Los planes que lo usan lo conservan, pero sin vídeo.`)) {
							deleteExercise(ex.id);
							onClose();
						}
					}}
				>
					Quitar de la biblioteca
				</button>
			)}
		</Sheet>
	);
}
