/**
 * Cola de guardado: cada cambio se guarda primero en el móvil y se envía a
 * Supabase; si no hay conexión (o la sesión caducó) se reintenta más tarde,
 * aunque se cierre la app. Así un entreno nunca se pierde por falta de cobertura.
 */
import type { SupabaseClient } from '@supabase/supabase-js';

type Row = Record<string, unknown>;

export interface Op {
	key: string; // identifica el registro: un cambio nuevo sobre el mismo registro sustituye al anterior
	table: string;
	kind: 'upsert' | 'delete' | 'update' | 'invoke'; // invoke: llama a la Edge Function `table` con `row`
	row?: Row;
	match?: Record<string, string>;
	at: number;
}

const KEY = 'gym-outbox.v1';

export function readOutbox(): Op[] {
	try {
		return JSON.parse(localStorage.getItem(KEY) || '[]') as Op[];
	} catch {
		return [];
	}
}

function write(ops: Op[]) {
	try {
		localStorage.setItem(KEY, JSON.stringify(ops));
	} catch {
		/* sin almacenamiento: la cola vive solo en memoria */
	}
}

let memory: Op[] = readOutbox();

export function enqueue(op: Omit<Op, 'at'>) {
	memory = [...memory.filter((o) => o.key !== op.key), { ...op, at: Date.now() }];
	write(memory);
}

export const pending = () => memory;

interface Failure {
	message?: string;
	code?: string;
}

/** ¿Merece la pena reintentar? (sin red, sesión caducada, servidor caído) */
function retryable(err: Failure | null, status: number) {
	if (status === 0 || status === 401 || status >= 500 || status === 408 || status === 429) return true;
	const m = `${err?.message ?? ''} ${err?.code ?? ''}`;
	return /fetch|network|load failed|timed out|jwt|PGRST301|PGRST303/i.test(m);
}

let flushing: Promise<{ dropped: string[] }> | null = null;

/** Envía lo pendiente en orden. Devuelve los errores definitivos (los que no se van a reintentar). */
export function flush(sb: SupabaseClient): Promise<{ dropped: string[] }> {
	if (flushing) return flushing;
	flushing = (async () => {
		const dropped: string[] = [];
		let refreshed = false;
		for (const op of [...memory]) {
			let res: { error: Failure | null; status: number };
			try {
				if (op.kind === 'invoke') {
					const r = await sb.functions.invoke(op.table, { body: op.row });
					if (!r.error && !r.data?.error) res = { error: null, status: 200 };
					else {
						const ctx = (r.error as { context?: Response } | null)?.context;
						let message = r.data?.error ?? r.error?.message ?? 'Error';
						try {
							if (ctx && typeof ctx.json === 'function') message = (await ctx.clone().json())?.error ?? message;
						} catch {
							/* respuesta sin JSON */
						}
						res = { error: { message }, status: ctx?.status ?? (r.data?.error ? 400 : 0) };
					}
				} else if (op.kind === 'update') {
					// Un update que la seguridad (RLS) no deja hacer no da error: devuelve 0 filas.
					const r = await sb.from(op.table).update(op.row!).match(op.match!).select();
					res = !r.error && (!r.data || r.data.length === 0) ? { error: { message: 'No tienes permiso para guardar este cambio' }, status: 403 } : r;
				} else
					res =
						op.kind === 'upsert'
							? await sb.from(op.table).upsert(op.row!)
							: await sb.from(op.table).delete().match(op.match!);
			} catch (e) {
				res = { error: { message: String(e) }, status: 0 };
			}
			if (!res.error) {
				memory = memory.filter((o) => !(o.key === op.key && o.at === op.at));
				write(memory);
				continue;
			}
			if (retryable(res.error, res.status)) {
				if ((res.status === 401 || /jwt/i.test(res.error.message ?? '')) && !refreshed) {
					refreshed = true;
					await sb.auth.refreshSession().catch(() => undefined);
				}
				break; // se reintentará más tarde, manteniendo el orden
			}
			dropped.push(res.error.message ?? 'Error desconocido');
			memory = memory.filter((o) => !(o.key === op.key && o.at === op.at));
			write(memory);
		}
		return { dropped };
	})().finally(() => {
		flushing = null;
	});
	return flushing;
}
