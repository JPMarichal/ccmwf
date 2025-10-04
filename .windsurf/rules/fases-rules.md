---
trigger: always_on
---

Las fases 1-4 han sido completadas. Toma ahora como base los scripts de la carpeta /scripts_google como los scripts de google que deben ser emulados en las fases siguientes. Estos scripts ya realizaban con éxito muchas de las tareas que ahora deben desarrollarse en python. Deberás conocer bien esta carpeta y sus scripts para poder planificar los reportes.

Las credenciales y otros datos que anteriormente se tomaban de config.js, se deberán tomar de .env . No debe crearse .env.example.

El archivo .env incluye una variable para la rama actual (RAMA_ACTUAL), que es la rama que se usará para los reportes, los cuales ignorarán la información de todas las demás ramas para enfocarse en ésta. 

Cada reporte debe tener su propio endpoint y ser capaz de ser ejecutado en forma independiente. Se debe pensar en términos de patrones de diseño y SOLID al momento de planificar, diseñar y desarrollar estos reportes, para asegurar escalabilidad, performance y consistencia.