import { useStore } from '../data/store';
import { getDraft, loggedSets, setDraft } from '../data/draft';
import { ask } from './ui';

/** Tarjeta "Entreno a medias" con Continuar / Descartar. */
export function DraftBanner({ onResume, onChanged }: { onResume: (dayId: string) => void; onChanged?: () => void }) {
	const { me, myPlan } = useStore();
	const d = me ? getDraft(me.id) : null;
	if (!d || !myPlan) return null;
	const day = myPlan.program.days.find((x) => x.id === d.dayId);
	const n = loggedSets(d);
	const discard = async () => {
		if (await ask(`¿Descartar lo apuntado en «${day?.name ?? 'el entreno'}»? ${n ? `Se perderán ${n} ${n === 1 ? 'serie' : 'series'}.` : ''}`, { ok: 'Descartar', cancel: 'No' })) {
			setDraft(me!.id, null);
			onChanged?.();
		}
	};
	return (
		<div className="card" style={{ border: '2px solid var(--yellow)' }}>
			<div className="card-head">
				⏸ Entreno a medias
				<span className="pill yellow">
					{n} {n === 1 ? 'serie apuntada' : 'series apuntadas'}
				</span>
			</div>
			<div className="card-body">
				<p className="card-title" style={{ marginBottom: 10 }}>
					{day?.name ?? 'Un día que ya no está en tu plan'}
				</p>
				<div className="btn-row">
					<button className="btn ghost sm" onClick={discard}>
						Descartar
					</button>
					{day && (
						<button className="btn" style={{ flex: 2 }} onClick={() => onResume(day.id)}>
							Continuar entreno ›
						</button>
					)}
				</div>
			</div>
		</div>
	);
}
