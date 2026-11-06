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
	useEffect(() => {
		pushEnabled().then(setOn).catch(() => setOn(false));
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
				{needsInstall ? (
					<div className="ok" style={{ background: '#fff4cc', color: '#5c4a00', marginBottom: 0 }}>
						En iPhone primero añade FitCoach a la pantalla de inicio: en Safari toca <b>Compartir</b> › <b>Añadir a pantalla de inicio</b>. Ábrela desde ese icono y
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
			</div>
		</div>
	);
}
