import { useState } from 'react';
import { ask, Sheet, TopBar, useToast } from '../components/ui';
import { useStore } from '../data/store';
import type { LibraryExercise, Program } from '../data/types';
import { ProgramEditor } from './AdminEditors';

const emptyProgram = (name: string): Program => ({ name, days: [], schedule: [null, null, null, null, null, null, null], cardio: [] });
const daysText = (p: Program) => `${p.days.length} ${p.days.length === 1 ? 'día' : 'días'} · ${p.days.reduce((a, d) => a + d.exercises.length, 0)} ejercicios`;

// ---------------- Plantillas ----------------

export function Templates({ onBack, onOpen }: { onBack: () => void; onOpen: (id: string) => void }) {
	const { db } = useStore();
	const [creating, setCreating] = useState(false);
	return (
		<>
			<TopBar
				title="Plantillas"
				sub="Rutinas base para nuevos atletas"
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
				{db.templates.length === 0 && <div className="empty">Aún no hay plantillas. Crea una o guarda el entreno de un atleta como plantilla.</div>}
				{db.templates.map((t) => (
					<div className="row clickable" key={t.id} onClick={() => onOpen(t.id)}>
						<div className="grow">
							<div className="name">{t.name}</div>
							<div className="muted">{daysText(t.program)}</div>
						</div>
						<span className="chev">›</span>
					</div>
				))}
			</div>
			{creating && <NewTemplate onClose={() => setCreating(false)} onCreated={(id) => onOpen(id)} />}
		</>
	);
}

function NewTemplate({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
	const { db, saveTemplate } = useStore();
	const [name, setName] = useState('');
	const [from, setFrom] = useState('');
	const athletes = db.users.filter((u) => db.plans.some((p) => p.userId === u.id && p.program.days.length));
	return (
		<Sheet title="Nueva plantilla" onClose={onClose}>
			<label className="field">
				<span>Nombre</span>
				<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Mujer · glúteo · 4 días" />
			</label>
			<label className="field">
				<span>Empezar desde</span>
				<select value={from} onChange={(e) => setFrom(e.target.value)}>
					<option value="">En blanco</option>
					{db.templates.length > 0 && (
						<optgroup label="Duplicar plantilla">
							{db.templates.map((t) => (
								<option key={t.id} value={`tpl:${t.id}`}>
									{t.name}
								</option>
							))}
						</optgroup>
					)}
					<optgroup label="Entreno de un atleta">
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
					const [kind, ref] = from.split(':');
					const base = kind === 'tpl' ? db.templates.find((t) => t.id === ref)?.program : kind === 'user' ? db.plans.find((p) => p.userId === ref)?.program : undefined;
					const id = crypto.randomUUID();
					saveTemplate({ id, name: name.trim(), program: base ? { ...structuredClone(base), name: name.trim() } : emptyProgram(name.trim()) });
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
	const [dirty, setDirty] = useState(false);
	const [toast, show] = useToast();
	if (!tpl) return null;
	return (
		<>
			<TopBar title={tpl.name} sub={`Plantilla · ${daysText(program)}`} onBack={onBack} />
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
			<ProgramEditor
				value={program}
				onChange={(p) => {
					setProgram(p);
					setDirty(true);
				}}
			/>
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
							saveTemplate({ id: tpl.id, name: name.trim(), program });
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

/** Guardar un entreno (el de un atleta) como plantilla nueva o sustituyendo una existente. */
export function SaveAsTemplate({ program, suggestedName, onClose }: { program: Program; suggestedName: string; onClose: () => void }) {
	const { db, saveTemplate } = useStore();
	const [name, setName] = useState(suggestedName);
	const [target, setTarget] = useState('new');
	const [toast, show] = useToast();
	const [done, setDone] = useState(false);
	return (
		<Sheet title="Guardar como plantilla" onClose={onClose}>
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
							{db.templates.map((t) => (
								<option key={t.id} value={t.id}>
									Sustituir «{t.name}»
								</option>
							))}
						</select>
					</label>
					{target === 'new' && (
						<label className="field">
							<span>Nombre</span>
							<input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Mujer · glúteo · 4 días" />
						</label>
					)}
					<button
						className="btn"
						disabled={target === 'new' && !name.trim()}
						onClick={async () => {
							const existing = db.templates.find((t) => t.id === target);
							if (existing && !(await ask(`Se sustituirá el contenido de «${existing.name}». ¿Seguir?`))) return;
							const finalName = existing ? existing.name : name.trim();
							saveTemplate({ id: existing?.id ?? crypto.randomUUID(), name: finalName, program: { ...structuredClone(program), name: finalName } });
							setDone(true);
							show('Plantilla guardada');
						}}
					>
						Guardar plantilla
					</button>
					<p className="muted" style={{ marginBottom: 0 }}>
						Guarda la versión que ves ahora en pantalla (aunque no hayas pulsado «Guardar cambios» del atleta).
					</p>
				</>
			)}
			{toast}
		</Sheet>
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
