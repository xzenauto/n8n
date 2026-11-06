import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
	plugins: [react()],
	base: './',
	// Marca de la compilación: el service worker se registra como sw.js?b=<marca> para que
	// el móvil instale siempre el de la última versión (iOS se quedaba con uno antiguo).
	define: { __BUILD__: JSON.stringify(String(Date.now())) },
});
