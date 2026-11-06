import { useEffect, useState } from 'react';

/** Estado del cronómetro: se guarda en el borrador del entreno para sobrevivir a recargas. */
export interface RestState {
	startedAt: number | null; // marca de tiempo si está en marcha
	accum: number; // ms acumulados en tramos anteriores (al pausar)
	between?: boolean; // descanso entre ejercicios (no entre series)
}

/** Descanso entre ejercicios: 4 minutos (se pone en rojo pasado 1 minuto más). */
export const BETWEEN_EXERCISES = { min: 240, max: 300 };

export const restIdle: RestState = { startedAt: null, accum: 0 };
export const restStart = (between = false): RestState => ({ startedAt: Date.now(), accum: 0, between });

const elapsedMs = (s: RestState) => s.accum + (s.startedAt ? Date.now() - s.startedAt : 0);

/** "2 - 3'" → 120-180 s · "90"" → 90 s · "1:30" → 90 s. Sin dato: null. */
export function parseRest(rest: string): { min: number; max: number } | null {
	const t = rest.trim();
	if (!t) return null;
	const mmss = t.match(/(\d+):(\d{2})/g);
	if (mmss) {
		const secs = mmss.map((x) => {
			const [m, s] = x.split(':').map(Number);
			return m * 60 + s;
		});
		return { min: Math.min(...secs), max: Math.max(...secs) };
	}
	const nums = (t.match(/\d+(?:[.,]\d+)?/g) ?? []).map((n) => Number(n.replace(',', '.')));
	if (!nums.length) return null;
	const seconds = /"|''|seg|\bs\b/i.test(t) || (!/'|min/i.test(t) && Math.max(...nums) > 10);
	const f = seconds ? 1 : 60;
	return { min: Math.min(...nums) * f, max: Math.max(...nums) * f };
}

const fmt = (ms: number) => {
	const s = Math.floor(ms / 1000);
	return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

export function RestTimer({ state, onChange, rest }: { state: RestState; onChange: (s: RestState) => void; rest: string }) {
	const [, tick] = useState(0);
	const running = state.startedAt != null;
	useEffect(() => {
		if (!running) return;
		const t = setInterval(() => tick((n) => n + 1), 250);
		return () => clearInterval(t);
	}, [running]);

	const ms = elapsedMs(state);
	const range = state.between ? BETWEEN_EXERCISES : parseRest(rest);
	const sec = ms / 1000;
	const phase = !range || ms === 0 ? 'idle' : sec < range.min ? 'rest' : sec <= range.max ? 'ready' : 'over';
	const pct = range ? Math.min(100, (sec / range.max) * 100) : 0;

	// Aviso (vibración donde el móvil lo permita) al llegar al descanso mínimo
	const [notified, setNotified] = useState(false);
	useEffect(() => {
		if (phase === 'ready' && !notified) {
			setNotified(true);
			try {
				navigator.vibrate?.([200, 100, 200]);
			} catch {
				/* sin vibración */
			}
		}
		if (phase === 'idle' || phase === 'rest') setNotified(false);
	}, [phase, notified]);

	const label =
		!running && ms > 0
			? 'En pausa'
			: phase === 'ready'
				? '¡Listo para la siguiente serie!'
				: phase === 'over'
					? 'Te estás pasando de descanso'
					: running
						? 'Descansando…'
						: 'Descanso';
	const rangeText = !range
		? ''
		: state.between
			? '4 min entre ejercicios'
			: range.min % 60 === 0 && range.max % 60 === 0
			? `${range.min / 60}${range.max !== range.min ? `-${range.max / 60}` : ''} min`
			: `${range.min}${range.max !== range.min ? `-${range.max}` : ''} s`;

	return (
		<div className={`rest rest-${phase}`}>
			<div className="rest-main">
				<span className="rest-time">{fmt(ms)}</span>
				<span className="rest-info">
					<b>{label}</b>
					{range && <small>Descanso: {rangeText}</small>}
				</span>
				<span className="rest-btns">
					{running ? (
						<button onClick={() => onChange({ ...state, startedAt: null, accum: ms })} aria-label="Pausar cronómetro">
							⏸
						</button>
					) : (
						<button onClick={() => onChange({ ...state, startedAt: Date.now(), accum: ms })} aria-label={ms > 0 ? 'Reanudar cronómetro' : 'Iniciar cronómetro'}>
							▶
						</button>
					)}
					<button onClick={() => onChange(running ? restStart(state.between) : { ...restIdle, between: state.between })} aria-label="Reiniciar cronómetro" disabled={ms === 0}>
						↺
					</button>
				</span>
			</div>
			{range && (
				<div className="rest-bar">
					<div style={{ width: `${pct}%` }} />
					<i style={{ left: `${(range.min / range.max) * 100}%` }} />
				</div>
			)}
		</div>
	);
}
