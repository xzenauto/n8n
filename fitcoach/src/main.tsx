import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { StoreProvider } from './data/store';
import './styles.css';

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<StoreProvider>
			<App />
		</StoreProvider>
	</StrictMode>,
);

if ('serviceWorker' in navigator && import.meta.env.PROD) {
	window.addEventListener('load', () => navigator.serviceWorker.register('./sw.js').catch(() => {}));
}

// Safari en iPhone ignora user-scalable=no: bloquea el gesto de pellizcar.
// (El zoom con doble toque ya lo impide touch-action en styles.css.)
document.addEventListener('gesturestart', (e) => e.preventDefault());
