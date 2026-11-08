// Catálogo de vídeos de ejercicios (Google Sheet de vídeos, «Hoja 1» A:B).
// Para añadir uno nuevo: una línea más con [nombre, enlace].
export const EXERCISE_VIDEOS: [string, string][] = [
	["Fortalecimiento lumbar", "https://www.youtube.com/watch?v=wnG25yYt4cM"],
	["Peso muerto piernas rígidas", "https://www.youtube.com/watch?v=S83jJKd_5WI"],
	["Calentamiento torso", "https://www.youtube.com/watch?v=IcgIvQWbH7Q"],
	["Calentamiento pierna", "https://www.youtube.com/watch?v=wdLX2QjXbKQ"],
	["Hip thrust", "https://www.youtube.com/watch?v=jG5kzgPpJ_0"],
	["Press en multipower", "https://www.youtube.com/watch?v=q5XCsArqdqI"],
	["Crunch en polea", "https://www.youtube.com/watch?v=gtn9lRlxAVk"],
	["Crunch en máquina", "https://www.youtube.com/watch?v=gtn9lRlxAVk"],
	["Tríceps overhead en banco", "https://youtube.com/shorts/02gpovpT6Gg"],
	["Aperturas al medio en polea", "https://youtube.com/shorts/hDnD9OtN7eU"],
	["Aperturas ascendentes con banco", "https://youtube.com/shorts/mr2_DXCKf18"],
	["Aperturas ascendentes de pie", "https://youtube.com/shorts/mr2_DXCKf18"],
	["Press en polea", "https://youtube.com/shorts/RaN_7ACh8Nk"],
	["Press vertical en polea", "https://youtube.com/shorts/0kTrra2hNEY"],
	["Press around unilateral", "https://youtube.com/shorts/6ZM5tXfWgwM"],
	["Femoral tumbado", "https://youtube.com/shorts/Vq1xHIt--JY"],
	["Remo en multipower + banco", "https://youtube.com/shorts/MhNFLksg6l0"],
	["Remo en multipower", "https://youtube.com/shorts/K0rAJP8cGyY"],
	["Jalón polea + banco", "https://youtube.com/shorts/OsP-nTAOQKo"],
	["Remo con barra", "https://youtube.com/shorts/G11HprjeZpk"],
	["Sentadilla en multipower", "https://youtube.com/shorts/WmRitMgPjV0"],
	["Curl femoral de pie", "https://youtube.com/shorts/COzZB6AltVQ"],
	["Prensa 45º", "https://youtube.com/shorts/3KO8iAp2sq8"],
	["Remo bajo en máquina", "https://youtube.com/shorts/D21rFjlpL6E"],
	["Peso muerto rumano", "https://youtube.com/shorts/vZAAZmzcfYc"],
	["Hiperextensiones para glúteo", "https://youtube.com/shorts/59v1oZlKF3w"],
	["Extensiones lumbares", "https://youtube.com/shorts/Ce5-VJGAHiM"],
	["Sentadilla búlgara en multipower", "https://youtube.com/shorts/9hHO9L163fo"],
	["Sentadilla búlgara con mancuerna", "https://youtube.com/shorts/ZK2ReGUNaWg"],
	["Step up", "https://youtube.com/shorts/O0hA9lM9PHQ"],
	["Patada de glúteo en polea", "https://youtube.com/shorts/B7yxIVX5WIc"],
	["Patada de glúteo en banco", "https://youtube.com/shorts/N6xk-aGEebY"],
	["Gemelo en prensa", "https://youtube.com/shorts/PYOhcrJ6HLo"],
	["Aductor en máquina", "https://youtube.com/shorts/5SRaUfjPydQ"],
	["Extensión de cuádriceps", "https://youtube.com/shorts/6MkluKB7bEM"],
	["Femoral sentado", "https://youtube.com/shorts/XhY7n1PSOwI"],
	["Prensa pendular unilateral", "https://youtube.com/shorts/PjHmGiV8vmQ"],
	["Elevaciones laterales con mancuerna", "https://youtube.com/shorts/rKpfAbGNSp0"],
	["Curl martillo con mancuernas", "https://youtube.com/shorts/UKuXYPCYwQc"],
	["Curl de bíceps alterno", "https://youtube.com/shorts/gS0mWMLUogI"],
	["Curl mancuerna + banco", "https://youtube.com/shorts/I4fnbtACu0Q"],
	["Abd en máquina", "https://youtube.com/shorts/mEI3h4NrwzU"],
	["Remo semiamplio", "https://youtube.com/shorts/MiPHKGI33zo"],
	["Remo gironda", "https://youtube.com/shorts/ZSWjbPQ_NVs"],
	["Remo gironda unilateral", "https://youtube.com/shorts/B38JVxM1JWI"],
	["Jalón al pecho (dorsal)", "https://youtube.com/shorts/7yi7itOSk0g"],
	["Jalón espalda alta", "https://youtube.com/shorts/nb0qYGg-TgM"],
	["Jalón caballero", "https://youtube.com/shorts/5xmJ5m7y9HI"],
	["Tríceps unilateral", "https://youtube.com/shorts/eYlvZAyb07k"],
	["Tríceps katana", "https://youtube.com/shorts/fW0glCNSNM8"],
	["Tríceps overhead", "https://youtube.com/shorts/NMmm8ZmqLnM"],
	["Jm Press", "https://youtube.com/shorts/JPZ06LCOhd8"],
	["Press neutro", "https://youtube.com/shorts/tNrEPyS-5Kk"],
	["Press con mancuernas", "https://youtube.com/shorts/j1yhi4vb_X8"],
	["Press en máquina de pie", "https://youtube.com/shorts/nP1uEm3QgtA"],
	["Dominadas libres", "https://youtube.com/shorts/CWOIzA0OU0c"],
	["Dominadas asistidas", "https://youtube.com/shorts/CWOIzA0OU0c"],
	["Fondos asistidos", "https://youtube.com/shorts/fFn_En3zj4k"],
	["Elevación de piernas", "https://youtube.com/shorts/eAnfliKzoGA"],
	["Crunch con peso", "https://youtube.com/shorts/w6sG6ahpA3s"],
	["Press en máquina de placas", "https://youtube.com/shorts/EuVp-OpGcmY"],
	["Remo dorian unilateral", "https://youtube.com/shorts/TC8U6Xuej0c"],
	["Remo alto en máquina", "https://youtube.com/shorts/sSlnh0wOd2E"],
	["Press militar", "https://youtube.com/shorts/kJUgsoec9PQ"],
	["Laterales en polea", "https://youtube.com/shorts/BkcBYHwzZzI"],
	["Curl de bíceps en polea", "https://youtube.com/shorts/u5z8VWFNd6c"],
	["Curl bayesian", "https://youtube.com/shorts/nf8oUPBuxc0"],
	["Curl martillo en polea", "https://youtube.com/shorts/BamIpV0o9fQ"],
	["Curl inclinado con apoyos", "https://youtube.com/shorts/2V-7oswXR28"],
	["Jalón en máquina", "https://youtube.com/shorts/nkPkUxN--H4"],
	["Remo T", "https://youtube.com/shorts/1szsRnFCFuA"],
	["Gemelo de pie", "https://youtube.com/shorts/ZF68fcrDzvY"],
	["Seal Row", "https://youtube.com/shorts/3VPScw66e7Q"],
	["Pull over", "https://youtube.com/shorts/QgmPsvPX0V4"],
	["Rack chins", "https://youtube.com/shorts/CW00A7BqeaE"],
	["Curl en máquina", "https://youtube.com/shorts/Spg-FDWjcZM"],
	["Pec deck", "https://youtube.com/shorts/TTuMRyV8Btw"],
	["Laterales en máquina de pie", "https://youtube.com/shorts/9tQgB-QuH1E"],
	["Laterales en máquina sentado", "https://youtube.com/shorts/EnR9ME2v9TU"],
	["Press pallof", "https://youtube.com/shorts/r2mb2QbpcRo"],
	["Hack squat", "https://youtube.com/shorts/-dn_qyia0hE"],
	["Kelsu Shrugs", "https://youtube.com/shorts/XufkdexhxNk"],
	["Sentadilla + press", "https://youtube.com/shorts/trDliNKEJyM?feature=share"],
	["Deadbug", "https://youtube.com/shorts/Nzx87gJr_3s?feature=share"],
	["Birdog dinámico", "https://youtube.com/shorts/ga_oIyzLIVA?feature=share"],
	["Plancha dinámica", "https://youtube.com/shorts/Q7md02TQpD4?feature=share"],
	["Plancha abdominal", "https://youtube.com/shorts/2MbeleQqfHk?feature=share"],
	["Hip thrust a 1 pierna", "https://youtube.com/shorts/2fQbabsckqs?feature=share"],
	["Flexiones", "https://youtube.com/shorts/WPaYdMrIHfQ"],
];

/** Nombres de los planes que no coinciden letra a letra con el catálogo → nombre del catálogo. */
const ALIASES: Record<string, string> = {
	'peck deck': 'Pec deck',
	'hip thrust en smith': 'Hip thrust',
	'bulgaras con mancuernas': 'Sentadilla búlgara con mancuerna',
	'bulgaras con mancuerna (pesada)': 'Sentadilla búlgara con mancuerna',
	'laterales con mancuernas': 'Elevaciones laterales con mancuerna',
	'laterales en polea a la altura de la cadera': 'Laterales en polea',
	'biceps martillo con mancuerna': 'Curl martillo con mancuernas',
	'prensa': 'Prensa 45º',
	'press inclinado con mancuernas': 'Press con mancuernas',
};

const norm = (s: string) =>
	s
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase()
		.replace(/\s+/g, ' ')
		.trim();

const byName = new Map(EXERCISE_VIDEOS.map(([n, url]) => [norm(n), url]));

/** Vídeo del catálogo para un nombre de ejercicio (o undefined si no está). */
export function catalogVideo(name: string): string | undefined {
	const k = norm(name);
	return byName.get(k) ?? (ALIASES[k] ? byName.get(norm(ALIASES[k])) : undefined);
}

/** Vídeo a mostrar: el que puso el entrenador en el plan o, si no hay, el del catálogo. */
export const videoFor = (ex: { name: string; video?: string }) => ex.video?.trim() || catalogVideo(ex.name);

export const CATALOG_NAMES = EXERCISE_VIDEOS.map(([n]) => n).sort((a, b) => a.localeCompare(b, 'es'));
