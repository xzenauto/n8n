export interface User {
	id: string;
	email: string;
	name: string;
	phone: string;
	isAdmin: boolean;
	isAthlete: boolean;
	createdAt: string;
}

export interface Exercise {
	id: string;
	name: string;
	note: string;
	video: string;
	sets: number;
	reps: string; // rango objetivo, p.ej. "8 - 11"
	rir: string; // objetivo, p.ej. "F" (fallo), "1 - 0"
}

export interface TrainingDay {
	id: string;
	name: string;
	warmup: string;
	rest: string;
	exercises: Exercise[];
}

export interface CardioItem {
	id: string;
	name: string;
	dose: string;
	notes: string;
}

export interface Program {
	name: string;
	days: TrainingDay[];
	/** Índice 0 = lunes … 6 = domingo. null = descanso */
	schedule: (string | null)[];
	cardio: CardioItem[];
}

export interface MealItem {
	foodId: string;
	grams: number;
}

export interface MealOption {
	id: string;
	name: string;
	items: MealItem[];
}

export interface Meal {
	id: string;
	name: string;
	time: string; // "HH:MM"
	note: string;
	options: MealOption[];
}

export interface Diet {
	kcal: number;
	protein: number;
	carbs: number;
	fat: number;
	meals: Meal[];
}

export interface Habit {
	id: string;
	emoji: string;
	name: string;
}

export interface Habits {
	goal: string;
	items: Habit[]; // máximo 5
	/** true cuando el atleta ya ha visto la bienvenida de hábitos */
	onboarded?: boolean;
}

export interface Plan {
	userId: string;
	program: Program;
	diet: Diet;
	habits: Habits;
}

export interface HabitLog {
	userId: string;
	date: string; // yyyy-mm-dd
	done: string[]; // ids de hábitos cumplidos
}

export interface SetLog {
	reps: string;
	kg: string;
	rir: string;
}

export interface ExerciseLog {
	exerciseId: string;
	name: string;
	sets: SetLog[];
}

export interface Session {
	id: string;
	userId: string;
	dayId: string;
	dayName: string;
	date: string; // ISO yyyy-mm-dd
	readiness: number | null;
	fatigue: number | null;
	note: string;
	entries: ExerciseLog[];
}

export interface Measurement {
	id: string;
	userId: string;
	date: string;
	weight?: number;
	chest?: number;
	arm?: number;
	absHigh?: number;
	absLow?: number;
	leg?: number;
}

export interface EquivalenceGroup {
	id: string;
	name: string;
	items: MealItem[];
}

/** Plantilla de entreno (program) o de dieta (diet). Se guardan en la misma tabla gym_templates. */
export interface Template {
	id: string;
	name: string;
	kind: 'program' | 'diet';
	program?: Program;
	diet?: Diet;
}

export interface LibraryExercise {
	id: string;
	name: string;
	video: string;
}

export interface Announcement {
	id: string;
	title: string;
	body: string;
	authorId: string | null;
	createdAt: string;
}

export interface DB {
	users: User[];
	plans: Plan[];
	sessions: Session[];
	measurements: Measurement[];
	equivalences: EquivalenceGroup[];
	habitLogs: HabitLog[];
	templates: Template[];
	exercises: LibraryExercise[];
	announcements: Announcement[];
}
