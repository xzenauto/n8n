import { useMemo, useState } from 'react';
import { Sheet, TopBar } from '../components/ui';
import { FOODS, GROUP_LABEL, type FoodGroup } from '../data/foods';
import { useStore } from '../data/store';
import type { MealItem } from '../data/types';
import { equivalent, getFood, macrosOf, nextMeal } from '../data/util';

export default function DietScreen() {
	const { myPlan } = useStore();
	const [swap, setSwap] = useState<MealItem | null>(null);
	const [calc, setCalc] = useState(false);
	const meals = useMemo(() => [...(myPlan?.diet.meals ?? [])].sort((a, b) => a.time.localeCompare(b.time)), [myPlan]);
	const current = nextMeal(meals, new Date())?.meal.id;
	const [tab, setTab] = useState<string>('all');

	if (!myPlan || meals.length === 0)
		return (
			<>
				<TopBar title="Dieta" />
				<div className="card">
					<div className="empty">Todavía no tienes dieta asignada.</div>
				</div>
			</>
		);

	const d = myPlan.diet;
	const shown = tab === 'all' ? meals : meals.filter((m) => m.id === tab);

	return (
		<>
			<TopBar
				title="Dieta"
				sub="Dieta diaria"
				right={
					<button className="btn sm" onClick={() => setCalc(true)}>
						⇄ Equivalencias
					</button>
				}
			/>

			<div className="card">
				<div className="stats">
					<div>
						<b>{d.kcal}</b>
						<span>kcal</span>
					</div>
					<div>
						<b>{d.protein}</b>
						<span>Prot</span>
					</div>
					<div>
						<b>{d.carbs}</b>
						<span>Hidr</span>
					</div>
					<div>
						<b>{d.fat}</b>
						<span>Grasa</span>
					</div>
				</div>
			</div>

			<div className="tabs">
				<button className={tab === 'all' ? 'on' : ''} onClick={() => setTab('all')}>
					Todo el día
				</button>
				{meals.map((m) => (
					<button key={m.id} className={tab === m.id ? 'on' : ''} onClick={() => setTab(m.id)}>
						{m.name}
					</button>
				))}
			</div>

			{shown.map((m) => (
				<div key={m.id}>
					<div className="section-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
						<span>
							{m.name} · {m.time}
						</span>
						{m.id === current && <span style={{ color: 'var(--yellow)' }}>Próxima</span>}
					</div>
					{m.note && (
						<p className="dark-muted" style={{ margin: '-4px 2px 8px' }}>
							{m.note}
						</p>
					)}
					{m.options.map((o) => {
						const mac = macrosOf(o.items);
						return (
							<div className="card" key={o.id}>
								<div className="card-head">{o.name}</div>
								{o.items.map((it, i) => (
									<div className="food-row" key={i}>
										<span className="grams">{it.grams} g</span>
										<span style={{ flex: 1 }}>{getFood(it.foodId)?.name ?? it.foodId}</span>
										<button className="btn ghost sm" onClick={() => setSwap(it)} aria-label="Cambiar alimento">
											⇄
										</button>
									</div>
								))}
								<div className="macro-bar">
									<span className="pill">{mac.kcal} kcal</span>
									<span className="pill">P {mac.p} g</span>
									<span className="pill">H {mac.c} g</span>
									<span className="pill">G {mac.f} g</span>
								</div>
							</div>
						);
					})}
				</div>
			))}

			{swap && <SwapSheet item={swap} onClose={() => setSwap(null)} />}
			{calc && <CalcSheet onClose={() => setCalc(false)} />}
		</>
	);
}

function SwapSheet({ item, onClose }: { item: MealItem; onClose: () => void }) {
	const { db } = useStore();
	const from = getFood(item.foodId);
	const [q, setQ] = useState('');
	const [allGroups, setAllGroups] = useState(false);
	if (!from) return null;

	// Alimentos de la tabla del entrenador primero, luego por grupo.
	const tableIds = new Set(db.equivalences.filter((g) => g.items.some((i) => i.foodId === from.id)).flatMap((g) => g.items.map((i) => i.foodId)));
	const list = FOODS.filter((f) => f.id !== from.id && (allGroups || f.group === from.group || tableIds.has(f.id)))
		.filter((f) => f.name.toLowerCase().includes(q.toLowerCase()))
		.sort((a, b) => Number(tableIds.has(b.id)) - Number(tableIds.has(a.id)) || a.name.localeCompare(b.name));

	return (
		<Sheet title="Cambiar alimento" onClose={onClose}>
			<p className="muted" style={{ marginTop: -6 }}>
				Te toca <b style={{ color: 'var(--ink)' }}>{item.grams} g de {from.name}</b>. Si no lo tienes, elige otro y te digo la cantidad equivalente.
			</p>
			<input className="input" placeholder="Buscar alimento…" value={q} onChange={(e) => setQ(e.target.value)} />
			<label className="check">
				<input type="checkbox" checked={allGroups} onChange={(e) => setAllGroups(e.target.checked)} /> Mostrar todos los grupos
			</label>
			<div className="card" style={{ background: '#fff', marginTop: 6 }}>
				{list.slice(0, 60).map((f) => {
					const r = equivalent(from.id, item.grams, f.id, db.equivalences);
					return (
						<div className="food-row" key={f.id}>
							<span className="grams">{r ? `${r.grams} g` : '–'}</span>
							<span style={{ flex: 1 }}>
								{f.name}
								{r && (
									<span className="muted" style={{ display: 'block', fontSize: 11 }}>
										{r.method === 'tabla' ? '★ Tabla del entrenador · ' : ''}
										{r.detail}
									</span>
								)}
							</span>
						</div>
					);
				})}
				{list.length === 0 && <div className="empty">Sin resultados</div>}
			</div>
		</Sheet>
	);
}

function CalcSheet({ onClose }: { onClose: () => void }) {
	const { db } = useStore();
	const [group, setGroup] = useState<FoodGroup>('H');
	const foods = FOODS.filter((f) => f.group === group).sort((a, b) => a.name.localeCompare(b.name));
	const [from, setFrom] = useState(foods[0]?.id ?? '');
	const [to, setTo] = useState(foods[1]?.id ?? '');
	const [grams, setGrams] = useState('80');
	const r = from && to ? equivalent(from, Number(grams) || 0, to, db.equivalences) : null;

	const changeGroup = (g: FoodGroup) => {
		setGroup(g);
		const fs = FOODS.filter((f) => f.group === g).sort((a, b) => a.name.localeCompare(b.name));
		setFrom(fs[0]?.id ?? '');
		setTo(fs[1]?.id ?? '');
	};

	return (
		<Sheet title="Calculadora de equivalencias" onClose={onClose}>
			<div className="tabs">
				{(Object.keys(GROUP_LABEL) as FoodGroup[]).map((g) => (
					<button key={g} className={g === group ? 'on' : ''} onClick={() => changeGroup(g)} style={g === group ? undefined : { background: 'var(--cell)', color: 'var(--ink)' }}>
						{GROUP_LABEL[g]}
					</button>
				))}
			</div>
			<div className="grid-2">
				<label className="field">
					<span>Me toca (g)</span>
					<input inputMode="decimal" value={grams} onChange={(e) => setGrams(e.target.value)} />
				</label>
				<label className="field">
					<span>De</span>
					<select value={from} onChange={(e) => setFrom(e.target.value)}>
						{foods.map((f) => (
							<option key={f.id} value={f.id}>
								{f.name}
							</option>
						))}
					</select>
				</label>
			</div>
			<label className="field">
				<span>Lo cambio por</span>
				<select value={to} onChange={(e) => setTo(e.target.value)}>
					{foods.map((f) => (
						<option key={f.id} value={f.id}>
							{f.name}
						</option>
					))}
				</select>
			</label>
			<div className="card" style={{ background: 'var(--head)', color: '#fff', textAlign: 'center', padding: 18 }}>
				<div style={{ fontSize: 13, color: '#bbb' }}>Equivale a</div>
				<div style={{ fontSize: 34, fontWeight: 900, color: 'var(--yellow)' }}>{r ? `${r.grams} g` : '–'}</div>
				<div style={{ fontSize: 13 }}>{getFood(to)?.name}</div>
				{r && <div style={{ fontSize: 12, color: '#bbb', marginTop: 6 }}>{r.method === 'tabla' ? `★ Tabla del entrenador: ${r.detail}` : r.detail}</div>}
			</div>
		</Sheet>
	);
}
