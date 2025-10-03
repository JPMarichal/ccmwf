---
trigger: always_on
description: Esta regla debe aplicarse al dar por cerrado un problema, cuando no haya más tareas pendientes
---

Para el pull request, proporciona una descripción de lo que se hizo respondiendo a las siguientes tres preguntas en formato markdown: ¿Cuál fue el problema? ¿Cuál era la causa raíz? ¿Qué se hizo para resolverlo?. La descripción debe estar sola, lista para copiar y pegar, sin comentarios o descripciones adicionales.

El pull request debe ser asignado al usuario JPMarichal (el único existente) y taggeado de manera apropiada.

El usuario puede solicitar el merge del pull request a main. Antes de mergear, asegúrate que no hay archivos por commitear ni tareas pendientes. Una vez que el pull request ha sido mergeado, cierra el item en github y cambia la rama a main en remoto y en local. Una vez en main, haz fetch y pull para asegurar que está actualizado. 