/** Suscripción a notificaciones push (Web Push). En iPhone solo funciona con la app añadida a la pantalla de inicio. */
import { sb } from './store';

export const pushSupported = () => typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
export const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
export const isStandalone = () =>
	window.matchMedia?.('(display-mode: standalone)').matches || (navigator as unknown as { standalone?: boolean }).standalone === true;

function keyToBytes(base64: string) {
	const pad = '='.repeat((4 - (base64.length % 4)) % 4);
	const raw = atob((base64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
	return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

async function registration() {
	const reg = (await navigator.serviceWorker.getRegistration()) ?? (await navigator.serviceWorker.register(`./sw.js?b=${__BUILD__}`, { updateViaCache: 'none' }));
	await navigator.serviceWorker.ready;
	return reg;
}

export async function pushEnabled(): Promise<boolean> {
	if (!pushSupported() || Notification.permission !== 'granted') return false;
	const reg = await navigator.serviceWorker.getRegistration();
	return !!(await reg?.pushManager.getSubscription());
}

/** Pide permiso y guarda la suscripción. Devuelve un error legible o null. */
export async function enablePush(userId: string): Promise<string | null> {
	if (!pushSupported()) return isIOS() ? 'Añade la app a la pantalla de inicio para poder recibir notificaciones.' : 'Este navegador no admite notificaciones.';
	const perm = await Notification.requestPermission();
	if (perm !== 'granted') return 'No has dado permiso. Puedes activarlo en Ajustes › Notificaciones › Axis Athlete.';
	try {
		const { data: key, error } = await sb.rpc('padel_vapid');
		if (error || !key) return 'No se pudo preparar el servicio de notificaciones.';
		const reg = await registration();
		const sub = (await reg.pushManager.getSubscription()) ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyToBytes(String(key)) }));
		const j = sub.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
		const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Atlantic/Canary';
		const { error: e2 } = await sb.from('gym_push_subs').upsert({ user_id: userId, endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth, tz }, { onConflict: 'endpoint' });
		return e2 ? `No se pudo guardar: ${e2.message}` : null;
	} catch (e) {
		return `No se pudieron activar: ${e instanceof Error ? e.message : String(e)}`;
	}
}

export async function disablePush(): Promise<void> {
	const reg = await navigator.serviceWorker.getRegistration();
	const sub = await reg?.pushManager.getSubscription();
	if (!sub) return;
	await sb.from('gym_push_subs').delete().eq('endpoint', sub.endpoint);
	await sub.unsubscribe();
}

export async function testPush(): Promise<string | null> {
	const { data, error } = await sb.functions.invoke('gym-push', { body: { action: 'test' } });
	if (error) return error.message;
	return data?.enviados ? null : 'No hay ningún dispositivo activado.';
}
