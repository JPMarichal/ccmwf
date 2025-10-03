---
trigger: always_on
---

Esta aplicación está bajo git. Deben hacerse commits y pushes cada vez que una tarea esté satisfecha, se alcance un hito o se complete una fase.

Cuando el usuario diga "haz commit" se ejecutará el add, commit y push en la rama actual, evitando incluir archivos de uso temporal (pruebas, logs u otros artefactos descartables según el contexto de la operación).

El mensaje del commit irá en español, comenzará con letra capital y un prefijo que identifique el tipo de cambio (por ejemplo, docs:, test:, refactor:, fix:, chore:, feat:). Debe describir en pasado lo realizado, responder de forma concisa a “¿qué fue lo que cambió?”, enumerar en una frase breve todos los ajustes relevantes y puede apoyarse en `git diff` para precisar los detalles (ejemplo: `docs: Se detallaron las reglas de mensajes y se actualizó la guía de commits`).

Debe verificarse que no existan conflictos ni incidencias. Si se detecta alguno, se detendrá el proceso y se notificará al usuario con la descripción del problema y la acción sugerida.