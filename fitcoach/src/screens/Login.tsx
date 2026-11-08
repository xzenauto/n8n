import { useState, type FormEvent } from 'react';
import { useStore } from '../data/store';

export default function Login() {
	const { login } = useStore();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState<string | null>(null);
	const [busy, setBusy] = useState(false);

	async function submit(e: FormEvent) {
		e.preventDefault();
		setBusy(true);
		setError(await login(email, password));
		setBusy(false);
	}

	return (
		<div className="login">
			<img className="brand-logo" src="img/logo.png" alt="" />
			<p className="brand">
				Axis <b>Athlete</b>
			</p>
			<p className="dark-muted" style={{ marginTop: 4, marginBottom: 24 }}>
				Entreno y dieta en un solo sitio
			</p>
			<form className="card" onSubmit={submit}>
				<div className="card-head">Iniciar sesión</div>
				<div className="card-body">
					{error && <div className="error">{error}</div>}
					<label className="field">
						<span>Email</span>
						<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
					</label>
					<label className="field">
						<span>Contraseña</span>
						<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
					</label>
					<button className="btn" disabled={busy}>
						Entrar
					</button>
				</div>
			</form>
			<p className="dark-muted" style={{ textAlign: 'center' }}>
				¿No tienes cuenta? Pídesela a tu entrenador.
			</p>
		</div>
	);
}
