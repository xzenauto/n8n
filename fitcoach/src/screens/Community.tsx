import { useEffect, useState } from 'react';
import { ask, Sheet, TopBar } from '../components/ui';
import { useStore } from '../data/store';
import { toISO, weekdayIndex } from '../data/util';

type Row = { userId: string; name: string; pct: number; streak: number; habits: number };

export default function Community() {
	const { db, me, ranking, deleteAnnouncement } = useStore();
	const [period, setPeriod] = useState<'week' | 'month'>('week');
	const [rows, setRows] = useState<Row[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [writing, setWriting] = useState(false);

	useEffect(() => {
		const today = new Date();
		const from = new Date(today);
		if (period === 'week') from.setDate(today.getDate() - weekdayIndex(today));
		else from.setDate(1);
		setRows(null);
		setError(null);
		ranking(toISO(from), toISO(today)).then((r) => {
			if (typeof r === 'string') setError(r);
			else setRows([...r].sort((a, b) => b.pct - a.pct || b.streak - a.streak || a.name.localeCompare(b.name)));
		});
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [period, db.habitLogs.length]);

	const nameOf = (id: string | null) => db.users.find((u) => u.id === id)?.name.split(' ')[0] ?? 'Entrenador';
	const medal = (i: number) => ['🥇', '🥈', '🥉'][i] ?? `${i + 1}`;

	return (
		<>
			<TopBar title="Comunidad" sub="Quién está cumpliendo sus hábitos" />

			<div className="section-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
				<span>Avisos</span>
				{me?.isAdmin && (
					<button className="btn sm" onClick={() => setWriting(true)}>
						+ Aviso
					</button>
				)}
			</div>
			{db.announcements.length === 0 ? (
				<div className="card">
					<div className="empty">{me?.isAdmin ? 'Publica un aviso para toda la comunidad: clases, horarios, días que no estarás…' : 'No hay avisos por ahora.'}</div>
				</div>
			) : (
				<div className="card">
					{db.announcements.map((a) => (
						<div className="row" key={a.id} style={{ alignItems: 'flex-start' }}>
							<span style={{ fontSize: 20 }}>📣</span>
							<div className="grow">
								<div className="name">{a.title}</div>
								{a.body && <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, marginTop: 2 }}>{a.body}</div>}
								<div className="muted" style={{ marginTop: 4 }}>
									{nameOf(a.authorId)} · {new Date(a.createdAt).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}
								</div>
							</div>
							{me?.isAdmin && (
								<button className="icon-btn" aria-label="Borrar aviso" onClick={async () => (await ask('¿Borrar este aviso?')) && deleteAnnouncement(a.id)}>
									🗑
								</button>
							)}
						</div>
					))}
				</div>
			)}

			<div className="section-label">Ranking de hábitos</div>
			<div className="tabs">
				<button className={period === 'week' ? 'on' : ''} onClick={() => setPeriod('week')}>
					Esta semana
				</button>
				<button className={period === 'month' ? 'on' : ''} onClick={() => setPeriod('month')}>
					Este mes
				</button>
			</div>
			<div className="card">
				{error && <div className="empty">No se pudo cargar el ranking: {error}</div>}
				{!error && rows === null && <div className="empty">Cargando…</div>}
				{rows?.length === 0 && <div className="empty">Todavía nadie tiene hábitos asignados.</div>}
				{rows?.map((r, i) => {
					const mine = r.userId === me?.id;
					return (
						<div className="rank-row" key={r.userId} style={mine ? { background: '#fff8dc' } : undefined}>
							<span className="rank-pos">{medal(i)}</span>
							<div className="grow" style={{ minWidth: 0 }}>
								<div className="name">
									{r.name}
									{mine && <span className="muted"> · tú</span>}
								</div>
								<div className="bar">
									<div style={{ width: `${Math.min(100, r.pct)}%`, background: i === 0 ? 'var(--green)' : 'var(--yellow-2)' }} />
								</div>
							</div>
							<div style={{ textAlign: 'right' }}>
								<b style={{ fontSize: 18, fontVariantNumeric: 'tabular-nums' }}>{Math.round(r.pct)}%</b>
								<div className="muted" style={{ fontSize: 12 }}>{r.streak > 0 ? `🔥 ${r.streak} ${r.streak === 1 ? 'día' : 'días'}` : 'sin racha'}</div>
							</div>
						</div>
					);
				})}
			</div>
			<p className="dark-muted" style={{ marginTop: -4 }}>
				Cuenta el porcentaje de hábitos cumplidos cada día sobre los tuyos: con 4 hábitos cada uno vale un 25 % y con 5, un 20 %. La racha son los días seguidos al 100 %.
			</p>

			{writing && <NewAnnouncement onClose={() => setWriting(false)} />}
		</>
	);
}

function NewAnnouncement({ onClose }: { onClose: () => void }) {
	const { addAnnouncement } = useStore();
	const [title, setTitle] = useState('');
	const [body, setBody] = useState('');
	return (
		<Sheet title="Nuevo aviso" onClose={onClose}>
			<label className="field">
				<span>Título</span>
				<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ej.: Esta semana no estaré el jueves" />
			</label>
			<label className="field">
				<span>Mensaje (opcional)</span>
				<textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Detalles, horario, enlace…" />
			</label>
			<button
				className="btn"
				disabled={!title.trim()}
				onClick={() => {
					addAnnouncement({ title: title.trim(), body: body.trim() });
					onClose();
				}}
			>
				Publicar para todos
			</button>
		</Sheet>
	);
}
