import { useState } from 'react';
import { TopBar, useToast } from '../components/ui';
import { useStore } from '../data/store';

export default function Profile() {
	const { me, updateUser, changePassword, logout, myPlan } = useStore();
	const [name, setName] = useState(me!.name);
	const [phone, setPhone] = useState(me!.phone);
	const [cur, setCur] = useState('');
	const [next, setNext] = useState('');
	const [next2, setNext2] = useState('');
	const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
	const [toast, show] = useToast();

	async function savePw() {
		if (next !== next2) return setPwMsg({ ok: false, text: 'Las contraseñas nuevas no coinciden' });
		const err = await changePassword(cur, next);
		if (err) setPwMsg({ ok: false, text: err });
		else {
			setPwMsg({ ok: true, text: 'Contraseña actualizada' });
			setCur('');
			setNext('');
			setNext2('');
		}
	}

	const initials = me!.name
		.split(' ')
		.map((w) => w[0])
		.slice(0, 2)
		.join('')
		.toUpperCase();

	return (
		<>
			<TopBar title="Perfil" />
			<div className="card">
				<div className="row">
					<div
						style={{
							width: 56,
							height: 56,
							borderRadius: '50%',
							background: 'var(--yellow)',
							display: 'grid',
							placeItems: 'center',
							fontWeight: 900,
							fontSize: 20,
						}}
					>
						{initials}
					</div>
					<div className="grow">
						<div className="card-title" style={{ margin: 0 }}>
							{me!.name}
						</div>
						<div className="muted">{me!.email}</div>
						<div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
							{me!.isAthlete && <span className="pill yellow">Atleta</span>}
							{me!.isAdmin && <span className="pill dark">Administrador</span>}
						</div>
					</div>
				</div>
				{myPlan && (
					<div className="row">
						<div className="grow muted">Programa actual</div>
						<b>{myPlan.program.name}</b>
					</div>
				)}
			</div>

			<div className="card">
				<div className="card-head">Mis datos</div>
				<div className="card-body">
					<label className="field">
						<span>Nombre</span>
						<input value={name} onChange={(e) => setName(e.target.value)} />
					</label>
					<label className="field">
						<span>Teléfono</span>
						<input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+34 600 000 000" />
					</label>
					<button
						className="btn dark"
						onClick={() => {
							updateUser(me!.id, { name: name.trim() || me!.name, phone: phone.trim() });
							show('Datos guardados');
						}}
					>
						Guardar
					</button>
				</div>
			</div>

			<div className="card">
				<div className="card-head">Cambiar contraseña</div>
				<div className="card-body">
					{pwMsg && <div className={pwMsg.ok ? 'ok' : 'error'}>{pwMsg.text}</div>}
					<label className="field">
						<span>Contraseña actual</span>
						<input type="password" value={cur} onChange={(e) => setCur(e.target.value)} autoComplete="current-password" />
					</label>
					<label className="field">
						<span>Nueva contraseña</span>
						<input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
					</label>
					<label className="field">
						<span>Repite la nueva</span>
						<input type="password" value={next2} onChange={(e) => setNext2(e.target.value)} autoComplete="new-password" />
					</label>
					<button className="btn dark" onClick={savePw} disabled={!cur || !next}>
						Cambiar contraseña
					</button>
				</div>
			</div>

			<button className="btn danger" onClick={logout}>
				Cerrar sesión
			</button>
			{toast}
		</>
	);
}
