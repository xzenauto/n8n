# FitCoach

App móvil (PWA) de **entreno y dieta** para atletas, con panel de **administrador**.

## Pantallas

| Menú | Qué hay |
| --- | --- |
| **Inicio** | Fecha, entreno que toca hoy, semana (días hechos en verde), próxima comida con sus macros, objetivos diarios y cardio/pasos. |
| **Entrenos** | "Te toca hoy", "Lo siguiente" y todos los días. Dentro de un día: tabla de ejercicios (series, reps, RIR, indicación, vídeo), cardio e historial. **Iniciar entreno**: readiness (0-10), luego pantalla por serie (Serie 1 de 3…) con lo de la semana pasada (reps, kg, RIR) frente al objetivo de esta semana, y campos en amarillo para apuntar kg, reps y RIR. "Siguiente serie" pasa a "Próximo ejercicio" en la última serie. Al acabar: fatiga (0-10), observaciones y resumen. Si sales a mitad, el entreno se guarda y se retoma. |
| **Dieta** | Objetivos (kcal, P, H, G), cada comida con sus opciones y macros. Botón ⇄ en cada alimento para cambiarlo por otro con la cantidad equivalente, y una calculadora de equivalencias. |
| **Progreso** | Peso; medidas (pecho, brazo, abdomen alto, abdomen bajo, pierna) con gráfica; progreso por ejercicio (mejor serie por sesión, subidas y bajadas de kg). |
| **Perfil** | Nombre, teléfono, cambiar contraseña, cerrar sesión. |
| **Admin** (solo administradores) | Alta de usuarios (atleta y/o admin, se puede copiar el plan de otro atleta), editar datos, restablecer contraseña, borrar. Editor completo de entreno (días, ejercicios, series, reps, RIR, notas, vídeo, qué día toca cada día de la semana, cardio) y de dieta (macros, comidas, horas, opciones, alimentos y gramos). Historial y progreso de cada atleta. Tabla de equivalencias de alimentos. |

### Equivalencias de alimentos
1. Si el entrenador definió un grupo en **Admin › Tabla de equivalencias** (p. ej. `30 g arroz = 50 g cereales`), se usa esa proporción (80 g arroz → 133 g cereales).
2. Si no, se calcula con el macro principal del alimento (hidratos, proteína o grasa) usando la base de alimentos importada de la hoja `DB_FOODS`.

## Cuentas iniciales

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| `carlos@fitcoach.app` | `Carlos1234` | Atleta + administrador (Carlos Artiles, con el plan "Reset metabólico" y las semanas 1-2 de la hoja) |
| `admin@fitcoach.app` | `Admin1234` | Solo administrador |

Cámbialas desde Perfil la primera vez.

## Datos: estado actual

Ahora mismo todo se guarda **en el navegador del dispositivo** (`localStorage`), toda la capa de datos está en
`src/data/store.tsx`. Sirve para probar la app completa, pero los usuarios que cree el admin solo existen
en ese dispositivo. Para usarla con varios atletas, cada uno desde su móvil, hay que conectarla a
Supabase: el esquema con seguridad por filas está en `supabase/schema.sql` y solo hay que cambiar `store.tsx`.

## Desarrollo

```bash
cd fitcoach
npm install
npm run dev            # http://localhost:5173
npm run build          # dist/ (para Vercel, Netlify, etc.)
npm run build:single   # dist-single/index.html, un único archivo
```
