import { useEffect, useState } from 'react';
import { disablePush, enablePush, isIOS, isStandalone, pushEnabled, pushSupported, testPush } from '../data/push';
import { useStore } from '../data/store';

const DISMISS = 'gym-push-dismissed.v1';

/** Tarjeta para activar los recordatorios (8:00 frase del día, 21:00 hábitos). */
export function NotificationsCard({ compact }: { compact?: boolean }) {
	const { me } = useStore();
	const [on, setOn] = useState<boolean | null>(null);
	const [busy, setBusy] = useState(false);
	const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
	const [hidden, setHidden] = useState(() => {
		try {
			return compact && localStorage.getItem(DISMISS) === '1';
		} catch {
			return false;
		}
	});
	const [swVersion, setSwVersion] = useState<string | null>(null);
	const [received, setReceived] = useState<string | null>(null);
	useEffect(() => {
		pushEnabled().then(setOn).catch(() => setOn(false));
		if (!('serviceWorker' in navigator)) return;
		// Diagnóstico: versión del service worker y notificaciones que llegan con la app abierta
		navigator.serviceWorker.getRegistration().then((reg) => {
			const sw = reg?.active;
			if (!sw) return setSwVersion('ninguno');
			const ch = new MessageChannel();
			ch.port1.onmessage = (e) => setSwVersion(String(e.data));
			sw.postMessage({ type: 'version' }, [ch.port2]);
			setTimeout(() => setSwVersion((v) => v ?? 'antiguo (sin versión)'), 1500);
		});
		const onMsg = (e: MessageEvent) => {
			if (e.data?.type === 'push') setReceived(`${e.data.title ?? ''} · ${e.data.body ?? ''}`);
		};
		navigator.serviceWorker.addEventListener('message', onMsg);
		return () => navigator.serviceWorker.removeEventListener('message', onMsg);
	}, []);

	const needsInstall = isIOS() && !isStandalone();
	if (compact && (hidden || on !== false)) return null;

	const enable = async () => {
		setBusy(true);
		const err = await enablePush(me!.id);
		setBusy(false);
		if (err) setMsg({ ok: false, text: err });
		else {
			setOn(true);
			setMsg({ ok: true, text: 'Notificaciones activadas.' });
		}
	};

	return (
		<div className="card">
			<div className="card-head">
				🔔 Recordatorios
				{compact && (
					<button
						className="icon-btn"
						style={{ color: '#fff' }}
						aria-label="Ocultar"
						onClick={() => {
							try {
								localStorage.setItem(DISMISS, '1');
							} catch {
								/* sin almacenamiento */
							}
							setHidden(true);
						}}
					>
						✕
					</button>
				)}
			</div>
			<div className="card-body">
				<p className="muted" style={{ marginTop: 0 }}>
					<b style={{ color: 'var(--ink)' }}>8:00</b> una frase para empezar el día · <b style={{ color: 'var(--ink)' }}>21:00</b> aviso si te queda algún hábito por marcar.
				</p>
				{msg && <div className={msg.ok ? 'ok' : 'error'}>{msg.text}</div>}
				{received && <div className="ok">📩 Recibida en este móvil: {received}</div>}
				{needsInstall ? (
					<div className="ok" style={{ background: '#fff4cc', color: '#5c4a00', marginBottom: 0 }}>
						En iPhone primero añade Axis Athlete a la pantalla de inicio: en Safari toca <b>Compartir</b> › <b>Añadir a pantalla de inicio</b>. Ábrela desde ese icono y
						vuelve aquí para activarlas.
					</div>
				) : !pushSupported() ? (
					<p className="muted" style={{ marginBottom: 0 }}>
						Este navegador no admite notificaciones.
					</p>
				) : on ? (
					<div className="btn-row">
						<button
							className="btn ghost sm"
							disabled={busy}
							onClick={async () => {
								setBusy(true);
								const err = await testPush();
								setBusy(false);
								setMsg(err ? { ok: false, text: err } : { ok: true, text: 'Enviada. Te llegará en unos segundos.' });
							}}
						>
							Enviar una de prueba
						</button>
						<button
							className="btn danger sm"
							disabled={busy}
							onClick={async () => {
								setBusy(true);
								await disablePush().catch(() => undefined);
								setBusy(false);
								setOn(false);
								setMsg({ ok: true, text: 'Notificaciones desactivadas en este dispositivo.' });
							}}
						>
							Desactivar
						</button>
					</div>
				) : (
					<button className="btn" disabled={busy} onClick={enable}>
						{busy ? 'Activando…' : 'Activar notificaciones'}
					</button>
				)}
				{!compact && swVersion && (
					<p className="muted" style={{ margin: '10px 0 0', fontSize: 11 }}>
						Servicio de notificaciones: {swVersion}
					</p>
				)}
			</div>
		</div>
	);
}
