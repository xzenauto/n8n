import type { Exercise, Plan, Session, SetLog, TrainingDay } from './types';

// Datos iniciales tomados de la hoja "Reset" y "🥗 Dieta Base" de Carlos.
// Ya están cargados en Supabase; se conservan como referencia y para crear planes vacíos.

const ex = (
	id: string,
	name: string,
	sets: number,
	reps: string,
	rir: string,
	note = '',
): Exercise => ({ id, name, sets, reps, rir, note, video: '' });

const CARLOS_ID = 'u_carlos';

const days: TrainingDay[] = [
	{
		id: 'd1',
		name: 'Día 1 · Anterior',
		warmup: 'Calentamiento torso',
		rest: "2 - 3'",
		exercises: [
			ex('d1e1', 'Elevaciones laterales con mancuerna', 3, '8 - 11', 'F'),
			ex('d1e2', 'Aperturas ascendentes con banco', 3, '7 - 9', '1 - 0'),
			ex('d1e3', 'Laterales en polea', 3, '7 - 10', 'F', 'Altura de cadera'),
			ex('d1e4', 'Press en máquina de placas', 3, '6 - 8', '0'),
			ex('d1e5', 'Extensión de cuádriceps', 3, '7 - 9', 'F'),
		],
	},
	{
		id: 'd2',
		name: 'Día 2 · Espalda + Brazo A',
		warmup: 'Calentamiento torso',
		rest: "2 - 3'",
		exercises: [
			ex('d2e1', 'Dominadas libres', 3, '6 - 8', '1'),
			ex('d2e2', 'Remo gironda', 2, '7 - 9', '0', 'Agarres independientes'),
			ex('d2e3', 'Curl en máquina', 3, '8 - 10', '0'),
			ex('d2e4', 'Tríceps unilateral', 2, '8 - 11', 'F'),
			ex('d2e5', 'Remo T', 2, '6 - 8', '0', 'Usa la nueva'),
			ex('d2e6', 'Tríceps katana', 2, '7 - 10', 'F'),
		],
	},
	{
		id: 'd3',
		name: 'Día 3 · Pectoral + Hombro',
		warmup: 'Calentamiento pierna',
		rest: "2 - 3'",
		exercises: [
			ex('d3e1', 'Laterales en máquina sentado', 3, '8 - 11', 'F'),
			ex('d3e2', 'Press militar', 2, '7 - 9', '1', 'Smith'),
			ex('d3e3', 'Press con mancuernas', 2, '6 - 8', '1', 'Banco 45º'),
			ex('d3e4', 'Aperturas al medio en polea', 3, '7 - 10', '0'),
			ex('d3e5', 'Laterales en polea', 2, '7 - 10', 'F', 'Abajo del todo'),
			ex('d3e6', 'Crunch en polea', 3, '8 - 11', '0'),
		],
	},
	{
		id: 'd4',
		name: 'Día 4 · Pierna',
		warmup: 'Calentamiento torso',
		rest: "2 - 3'",
		exercises: [
			ex('d4e1', 'Aductor en máquina', 3, '7 - 10', 'F'),
			ex('d4e2', 'Extensión de cuádriceps', 3, '7 - 10', 'F'),
			ex('d4e3', 'Sentadilla en multipower', 2, '6 - 8', '2', 'Apoya cada repe en seguros'),
			ex('d4e4', 'Hip thrust', 2, '7 - 9', '1'),
			ex('d4e5', 'Hiperextensiones para glúteo', 2, '8 - 10', '0'),
		],
	},
	{
		id: 'd5',
		name: 'Día 5 · Espalda + Brazo B',
		warmup: 'Calentamiento torso',
		rest: "2 - 3'",
		exercises: [
			ex('d5e1', 'Remo máquina de pie', 3, '7 - 9', '1 - 0'),
			ex('d5e2', 'Jalón caballero', 2, '7 - 9', '0'),
			ex('d5e3', 'Pull over', 3, '8 - 11', 'F'),
			ex('d5e4', 'Curl mancuerna + banco', 2, '7 - 10', '0'),
			ex('d5e5', 'Tríceps unilateral', 3, '8 - 11', 'F'),
			ex('d5e6', 'Curl inclinado con apoyos', 2, '7 - 10', '0'),
		],
	},
];

export const carlosPlan: Plan = {
	userId: CARLOS_ID,
	habits: { goal: '', items: [] },
	program: {
		name: 'Reset metabólico',
		days,
		schedule: ['d1', 'd2', 'd3', 'd4', 'd5', null, null],
		cardio: [
			{
				id: 'c1',
				name: 'Objetivo de pasos',
				dose: '15 mil',
				notes: 'Recomiendo hacerlo por tramos, buscando una estructura que te funcione',
			},
			{
				id: 'c2',
				name: 'Cardio zona 2 post entreno',
				dose: '10 min',
				notes: 'Máx. inclinación · velocidad 5,8 - 6',
			},
		],
	},
	diet: {
		kcal: 2019,
		protein: 105,
		carbs: 281,
		fat: 39,
		meals: [
			{
				id: 'm1',
				name: 'Desayuno',
				time: '08:00',
				note: '',
				options: [
					{
						id: 'm1o1',
						name: 'Opción 1',
						items: [
							{ foodId: 'F0188', grams: 100 },
							{ foodId: 'F0255', grams: 85 },
							{ foodId: 'F0247', grams: 100 },
						],
					},
				],
			},
			{
				id: 'm2',
				name: 'Post entreno',
				time: '14:00',
				note: 'Elige 1 hidrato',
				options: [
					{
						id: 'm2o1',
						name: 'Opción 1',
						items: [
							{ foodId: 'F0021', grams: 200 },
							{ foodId: 'F0014', grams: 60 },
							{ foodId: 'F0115', grams: 15 },
							{ foodId: 'F0079', grams: 15 },
						],
					},
				],
			},
			{
				id: 'm3',
				name: 'Merienda / Postre',
				time: '18:00',
				note: '',
				options: [
					{
						id: 'm3o1',
						name: 'Pudding de avena y prote',
						items: [
							{ foodId: 'F0160', grams: 20 },
							{ foodId: 'F0058', grams: 60 },
							{ foodId: 'F0247', grams: 100 },
							{ foodId: 'F0188', grams: 100 },
							{ foodId: 'F0075', grams: 10 },
						],
					},
				],
			},
			{
				id: 'm4',
				name: 'Cena',
				time: '21:30',
				note: '2 horas antes de irte a la cama',
				options: [
					{
						id: 'm4o1',
						name: 'Opción 1',
						items: [
							{ foodId: 'F0021', grams: 200 },
							{ foodId: 'F0014', grams: 60 },
							{ foodId: 'F0115', grams: 15 },
							{ foodId: 'F0079', grams: 20 },
						],
					},
				],
			},
		],
	},
};

// Historial: semanas 1 y 2 tal como están en la hoja.
type S = [number, string, string];
const sets = (...s: S[]): SetLog[] => s.map(([reps, kg, rir]) => ({ reps: String(reps), kg, rir }));

function session(
	id: string,
	dayId: string,
	date: string,
	readiness: number,
	fatigue: number,
	logs: SetLog[][],
	note = '',
): Session {
	const day = days.find((d) => d.id === dayId)!;
	return {
		id,
		userId: CARLOS_ID,
		dayId,
		dayName: day.name,
		date,
		readiness,
		fatigue,
		note,
		entries: day.exercises.map((e, i) => ({ exerciseId: e.id, name: e.name, sets: logs[i] ?? [] })),
	};
}

export const carlosSessions: Session[] = [
	session('s_w1d1', 'd1', '2026-10-26', 8, 7, [
		sets([11, '12.5', 'F'], [10, '12.5', 'F']),
		sets([9, '24', '1'], [9, '24', '0'], [8, '24', '0']),
		sets([8, '27.5', 'F'], [8, '27.5', 'F'], [7, '27.5', 'F']),
		sets([9, '88', '0'], [8, '88', '0'], [7, '88', '0']),
		sets([12, '100', 'F'], [11, '100', 'F'], [9, '100', 'F']),
	]),
	session('s_w1d2', 'd2', '2026-10-27', 8, 7, [
		sets([10, '0', '1'], [8, '0', '1'], [7, '0', '1']),
		sets([9, '160', '0'], [8, '160', '0']),
		sets([8, '54', '0'], [9, '50', '0'], [8, '50', '0']),
		sets([10, '47.5', 'F'], [9, '47.5', 'F']),
		sets([7, '1.5', '0'], [6, '1.5', '0']),
		sets([9, '47.5', 'F'], [8, '47.5', 'F']),
	]),
	session('s_w1d3', 'd3', '2026-10-28', 8, 7, [
		sets([11, '22.5', 'F'], [10, '22.5', 'F'], [9, '22.5', 'F']),
		sets([6, '1.75', '0'], [5, '1.75', '0']),
		sets([6, '35', '1'], [6, '32.5', '1']),
		sets([9, '42.5', '0'], [7, '42.5', '0'], [7, '39', '0']),
		sets([9, '19', 'F'], [8, '19', 'F']),
		sets([14, '125', '0'], [13, '125', '0'], [12, '125', '0']),
	]),
	session('s_w1d4', 'd4', '2026-10-29', 9, 8, [
		sets([10, '13*10', 'F'], [9, '13*10', 'F'], [7, '13*10', 'F']),
		sets([12, '104', 'F'], [12, '104', 'F'], [11, '104', 'F']),
		sets([8, '1.5', '2'], [8, '1.5', '2']),
		sets([9, '4', '1'], [8, '4', '1']),
		sets([12, '2*35', '0'], [10, '2*35', '0']),
	]),
	session(
		's_w1d5',
		'd5',
		'2026-10-30',
		7,
		9,
		[
			sets([8, '2*25', '1'], [8, '2*25', '0'], [8, '2*25', '0']),
			sets([9, '180', '0'], [8, '180', '0']),
			sets([9, '32.5', 'F'], [8, '32.5', 'F'], [8, '32.5', 'F']),
			sets([7, '17.5', '0'], [9, '15', '0']),
			sets([10, '47.5', 'F'], [9, '47.5', 'F'], [8, '47.5', 'F']),
			sets([9, '17.5', '0'], [8, '17.5', '0']),
		],
		'Este día es top',
	),
	session('s_w2d1', 'd1', '2026-11-02', 6, 7, [
		sets([11, '12.5', 'F'], [10, '12.5', 'F'], [9, '12.5', 'F']),
		sets([8, '27.5', '1'], [8, '27.5', '0'], [7, '27.5', '0']),
		sets([8, '22.5', 'F'], [7, '22.5', 'F']),
		sets([8, '88', '0'], [7, '88', '0']),
		sets([12, '100', 'F'], [11, '100', 'F']),
	], 'Laterales en polea sin muñequera'),
	session('s_w2d2', 'd2', '2026-11-03', 7, 7, [
		sets([11, '0', '1'], [9, '0', '1'], [8, '0', '1']),
		sets([9, '160', '0'], [8, '160', '0']),
		sets([8, '54', '0'], [9, '50', '0'], [7, '50', '0']),
		sets([11, '47.5', 'F'], [10, '47.5', 'F']),
		sets([8, '1.5', '0'], [7, '1.5', '0']),
		sets([10, '47.5', 'F'], [8, '47.5', 'F']),
	]),
];

export function emptyPlan(userId: string): Plan {
	return {
		userId,
		program: {
			name: 'Nuevo programa',
			days: [],
			schedule: [null, null, null, null, null, null, null],
			cardio: [],
		},
		diet: { kcal: 0, protein: 0, carbs: 0, fat: 0, meals: [] },
		habits: { goal: '', items: [] },
	};
}

