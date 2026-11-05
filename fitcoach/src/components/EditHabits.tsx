import { useState } from 'react';
import { useStore } from '../data/store';
import type { Habits } from '../data/types';
import { HabitsEditor } from '../screens/AdminEditors';
import { Sheet } from './ui';

/** Hoja para editar el objetivo y los hábitos de un atleta (solo administradores). */
export function EditHabitsSheet({ userId, onClose }: { userId: string; onClose: () => void }) {
	const { planOf, savePlan } = useStore();
	const plan = planOf(userId);
	const [draft, setDraft] = useState<Habits>(() => structuredClone(plan?.habits ?? { goal: '', items: [] }));
	if (!plan) return null;
	return (
		<Sheet title="Editar hábitos y objetivo" onClose={onClose}>
			<div style={{ background: 'var(--bg)', margin: '0 -16px', padding: '12px 16px 4px' }}>
				<HabitsEditor value={draft} onChange={setDraft} />
			</div>
			<button
				className="btn"
				style={{ marginTop: 12 }}
				disabled={draft.items.some((h) => !h.name.trim())}
				onClick={() => {
					savePlan({ ...plan, habits: { goal: draft.goal.trim(), items: draft.items.map((h) => ({ ...h, name: h.name.trim() })) } });
					onClose();
				}}
			>
				Guardar hábitos
			</button>
			{draft.items.some((h) => !h.name.trim()) && (
				<p className="muted" style={{ textAlign: 'center' }}>
					Pon nombre a todos los hábitos para guardar.
				</p>
			)}
		</Sheet>
	);
}

/** Botón "Editar" que solo ve un administrador. */
export function EditHabitsButton({ userId, dark }: { userId: string; dark?: boolean }) {
	const { me } = useStore();
	const [open, setOpen] = useState(false);
	if (!me?.isAdmin) return null;
	return (
		<>
			<button
				className="btn sm"
				style={dark ? { background: '#2a2a2a', color: 'var(--on-dark)', padding: '6px 10px' } : { padding: '6px 10px' }}
				onClick={(e) => {
					e.stopPropagation();
					setOpen(true);
				}}
			>
				✏️ Editar
			</button>
			{open && <EditHabitsSheet userId={userId} onClose={() => setOpen(false)} />}
		</>
	);
}
