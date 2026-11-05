import { useEffect, useState, type ReactNode } from 'react';

export function Icon({ name }: { name: 'home' | 'dumbbell' | 'food' | 'chart' | 'user' | 'shield' }) {
	const p = {
		fill: 'none',
		stroke: 'currentColor',
		strokeWidth: 2,
		strokeLinecap: 'round' as const,
		strokeLinejoin: 'round' as const,
	};
	switch (name) {
		case 'home':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z" />
				</svg>
			);
		case 'dumbbell':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<path d="M6 7v10M3 9.5v5M18 7v10M21 9.5v5M6 12h12" />
				</svg>
			);
		case 'food':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<path d="M4 3v8a3 3 0 0 0 3 3v7M7 3v8M10 3v8a3 3 0 0 1-3 3M17 21V3c-2 1-3 4-3 7s1 4 3 4" />
				</svg>
			);
		case 'chart':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<path d="M3 3v18h18M7 15l4-4 3 3 5-6" />
				</svg>
			);
		case 'user':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<circle cx="12" cy="8" r="4" />
					<path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
				</svg>
			);
		case 'shield':
			return (
				<svg viewBox="0 0 24 24" {...p}>
					<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />
					<path d="m9 12 2 2 4-4" />
				</svg>
			);
	}
}

export function TopBar({ title, sub, onBack, right }: { title: string; sub?: string; onBack?: () => void; right?: ReactNode }) {
	return (
		<div>
			{onBack && (
				<button className="back" onClick={onBack} style={{ paddingTop: 'calc(14px + env(safe-area-inset-top))' }}>
					‹ Volver
				</button>
			)}
			<div className="topbar" style={onBack ? { paddingTop: 4 } : undefined}>
				<div>
					<h1>{title}</h1>
					{sub && <div className="sub">{sub}</div>}
				</div>
				{right}
			</div>
		</div>
	);
}

export function Scale({ value, onChange }: { value: number | null; onChange: (n: number) => void }) {
	return (
		<div className="scale">
			{Array.from({ length: 11 }, (_, i) => (
				<button key={i} className={value === i ? 'on' : ''} onClick={() => onChange(i)}>
					{i}
				</button>
			))}
		</div>
	);
}

export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
	return (
		<div className="sheet-backdrop" onClick={onClose}>
			<div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
					<h3>{title}</h3>
					<button className="icon-btn" onClick={onClose} aria-label="Cerrar">
						✕
					</button>
				</div>
				{children}
			</div>
		</div>
	);
}

export function useToast(): [ReactNode, (msg: string) => void] {
	const [msg, setMsg] = useState<string | null>(null);
	useEffect(() => {
		if (!msg) return;
		const t = setTimeout(() => setMsg(null), 1800);
		return () => clearTimeout(t);
	}, [msg]);
	return [msg ? <div className="toast">{msg}</div> : null, setMsg];
}

export interface Point {
	label: string;
	value: number;
}

/** Gráfica de línea simple en SVG. */
export function LineChart({ points, unit = '' }: { points: Point[]; unit?: string }) {
	if (points.length === 0) return <div className="empty">Aún no hay datos</div>;
	const W = 340,
		H = 170,
		pl = 36,
		pr = 12,
		pt = 14,
		pb = 26;
	const vals = points.map((p) => p.value);
	let min = Math.min(...vals),
		max = Math.max(...vals);
	if (min === max) {
		min -= 1;
		max += 1;
	}
	const pad = (max - min) * 0.15;
	min -= pad;
	max += pad;
	const x = (i: number) => (points.length === 1 ? (pl + W - pr) / 2 : pl + (i * (W - pl - pr)) / (points.length - 1));
	const y = (v: number) => pt + ((max - v) * (H - pt - pb)) / (max - min);
	const ticks = [0, 0.5, 1].map((t) => min + (max - min) * t);
	const bestIdx = vals.indexOf(Math.max(...vals));
	const step = Math.max(1, Math.ceil(points.length / 5));
	return (
		<svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img">
			<g className="grid">
				{ticks.map((t, i) => (
					<g key={i}>
						<line x1={pl} x2={W - pr} y1={y(t)} y2={y(t)} />
						<text x={pl - 6} y={y(t) + 3} textAnchor="end">
							{fmt(t)}
						</text>
					</g>
				))}
			</g>
			<path className="line" d={points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.value)}`).join(' ')} />
			{points.map((p, i) => (
				<g key={i}>
					<circle className={`dot ${i === bestIdx ? 'best' : ''}`} cx={x(i)} cy={y(p.value)} r={4.5}>
						<title>
							{p.label}: {fmt(p.value)}
							{unit}
						</title>
					</circle>
					{(i % step === 0 || i === points.length - 1) && (
						<text x={x(i)} y={H - 8} textAnchor="middle">
							{p.label}
						</text>
					)}
				</g>
			))}
		</svg>
	);
}

const fmt = (n: number) => (Math.abs(n) >= 100 ? Math.round(n).toString() : (Math.round(n * 10) / 10).toString());

// ---------- Confirmación propia (los diálogos nativos pueden estar bloqueados) ----------
type AskReq = { msg: string; resolve: (ok: boolean) => void };
let pushAsk: ((r: AskReq) => void) | null = null;

export function ask(msg: string): Promise<boolean> {
	return new Promise((resolve) => (pushAsk ? pushAsk({ msg, resolve }) : resolve(true)));
}

export function AskHost() {
	const [req, setReq] = useState<AskReq | null>(null);
	useEffect(() => {
		pushAsk = setReq;
		return () => {
			pushAsk = null;
		};
	}, []);
	if (!req) return null;
	const done = (ok: boolean) => {
		req.resolve(ok);
		setReq(null);
	};
	return (
		<Sheet title="¿Seguro?" onClose={() => done(false)}>
			<p style={{ marginTop: 0 }}>{req.msg}</p>
			<div className="btn-row">
				<button className="btn ghost" onClick={() => done(false)}>
					Cancelar
				</button>
				<button className="btn dark" onClick={() => done(true)}>
					Aceptar
				</button>
			</div>
		</Sheet>
	);
}
