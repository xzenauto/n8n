import { useState } from 'react';
import { AskHost, Icon } from './components/ui';
import { useStore } from './data/store';
import Admin from './screens/Admin';
import Community from './screens/Community';
import DietScreen from './screens/Diet';
import Home from './screens/Home';
import Login from './screens/Login';
import Onboarding from './screens/Onboarding';
import Profile from './screens/Profile';
import Progress from './screens/Progress';
import Trainings from './screens/Trainings';
import Workout from './screens/Workout';

export type Tab = 'home' | 'train' | 'diet' | 'progress' | 'community' | 'profile' | 'admin';

function SaveError({ msg, onClose }: { msg: string; onClose: () => void }) {
	return (
		<div className="error" style={{ position: 'sticky', top: 'env(safe-area-inset-top, 0px)', zIndex: 30, marginTop: 8, display: 'flex', gap: 8 }}>
			<span style={{ flex: 1 }}>{msg}</span>
			<button className="icon-btn" onClick={onClose} aria-label="Cerrar aviso">
				✕
			</button>
		</div>
	);
}

export default function App() {
	const { me, myPlan, status, saveError, clearSaveError, logout, pendingCount } = useStore();
	const [tab, setTab] = useState<Tab>('home');
	const [openDay, setOpenDay] = useState<string | null>(null);
	const [running, setRunning] = useState<string | null>(null);

	if (status === 'loading')
		return (
			<div className="login">
				<p className="brand">
					Axis <b>Athlete</b>
				</p>
				<p className="dark-muted">Cargando…</p>
			</div>
		);
	if (status === 'noAccess')
		return (
			<div className="login">
				<p className="brand">
					Axis <b>Athlete</b>
				</p>
				<div className="card">
					<div className="card-body">
						<p className="card-title">Tu cuenta no tiene acceso</p>
						<p className="muted">Esta cuenta existe, pero no está dada de alta en Axis Athlete. Pide a tu entrenador que te cree el acceso.</p>
						<button className="btn dark" onClick={logout}>
							Cerrar sesión
						</button>
					</div>
				</div>
			</div>
		);
	if (!me) return <Login />;

	const banner = (saveError || pendingCount > 0) && (
		<>
			{pendingCount > 0 && (
				<div className="ok" style={{ position: 'sticky', top: 'env(safe-area-inset-top, 0px)', zIndex: 30, marginTop: 8, background: '#fff4cc', color: '#5c4a00' }}>
					⏳ {pendingCount === 1 ? '1 cambio guardado en el móvil' : `${pendingCount} cambios guardados en el móvil`}, enviando al servidor… Se envía solo en cuanto haya conexión.
				</div>
			)}
			{saveError && <SaveError msg={saveError} onClose={clearSaveError} />}
		</>
	);

	// Primera vez: bienvenida de hábitos para atletas que aún no tienen ninguno
	if (me.isAthlete && myPlan && !myPlan.habits?.onboarded && !(myPlan.habits?.items.length > 0))
		return (
			<div className="app" style={{ paddingBottom: 0 }}>
				{banner}
				<Onboarding />
				<AskHost />
			</div>
		);

	if (running)
		return (
			<div className="app" style={{ paddingBottom: 24 }}>
				{banner}
				<Workout dayId={running} onExit={() => setRunning(null)} />
				<AskHost />
			</div>
		);

	const go = (t: Tab) => {
		setTab(t);
		setOpenDay(null);
		window.scrollTo(0, 0);
	};

	const items: { id: Tab; label: string; icon: Parameters<typeof Icon>[0]['name'] }[] = [
		{ id: 'home', label: 'Inicio', icon: 'home' },
		{ id: 'train', label: 'Entrenos', icon: 'dumbbell' },
		{ id: 'progress', label: 'Progreso', icon: 'chart' },
		{ id: 'community', label: 'Comunidad', icon: 'users' },
		{ id: 'profile', label: 'Perfil', icon: 'user' },
	];
	// La pestaña Dieta solo aparece si el atleta tiene dieta asignada (los admin la ven siempre)
	const hasDiet = !!myPlan && (myPlan.diet.kcal > 0 || myPlan.diet.meals.length > 0);
	if (hasDiet || me.isAdmin) items.splice(2, 0, { id: 'diet', label: 'Dieta', icon: 'food' });
	if (me.isAdmin) items.push({ id: 'admin', label: 'Admin', icon: 'shield' });

	return (
		<>
			<div className="app">
				{banner}
				{tab === 'home' && (
					<Home
						onOpenDay={(id) => {
							setTab('train');
							setOpenDay(id);
						}}
						onGo={go}
					/>
				)}
				{tab === 'train' && <Trainings openDay={openDay} setOpenDay={setOpenDay} onStart={setRunning} />}
				{tab === 'diet' && <DietScreen />}
				{tab === 'progress' && <Progress />}
				{tab === 'community' && <Community />}
				{tab === 'profile' && <Profile />}
				{tab === 'admin' && me.isAdmin && <Admin />}
			</div>
			<nav className="nav">
				<div className="nav-inner">
					{items.map((it) => (
						<button key={it.id} className={tab === it.id ? 'active' : ''} onClick={() => go(it.id)}>
							<Icon name={it.icon} />
							{it.label}
						</button>
					))}
				</div>
			</nav>
			<AskHost />
		</>
	);
}
