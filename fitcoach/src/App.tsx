import { useState } from 'react';
import { AskHost, Icon } from './components/ui';
import { useStore } from './data/store';
import Admin from './screens/Admin';
import DietScreen from './screens/Diet';
import Home from './screens/Home';
import Login from './screens/Login';
import Profile from './screens/Profile';
import Progress from './screens/Progress';
import Trainings from './screens/Trainings';
import Workout from './screens/Workout';

export type Tab = 'home' | 'train' | 'diet' | 'progress' | 'profile' | 'admin';

export default function App() {
	const { me } = useStore();
	const [tab, setTab] = useState<Tab>('home');
	const [openDay, setOpenDay] = useState<string | null>(null);
	const [running, setRunning] = useState<string | null>(null);

	if (!me) return <Login />;

	if (running)
		return (
			<div className="app" style={{ paddingBottom: 24 }}>
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
		{ id: 'diet', label: 'Dieta', icon: 'food' },
		{ id: 'progress', label: 'Progreso', icon: 'chart' },
		{ id: 'profile', label: 'Perfil', icon: 'user' },
	];
	if (me.isAdmin) items.push({ id: 'admin', label: 'Admin', icon: 'shield' });

	return (
		<>
			<div className="app">
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
