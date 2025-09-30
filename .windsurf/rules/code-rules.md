---
trigger: always_on
---

Si creas archivos temporales para pruebas rápidas, deberás crear el menor número posible, reutilizando mejor que crear innecesariamente, y deberás eliminarlos una vez pasada la prueba. No debe dejarse rastro de archivos o código innecesarios para el sistema y para el objetivo del proyecto. Sobre todo, dichos archivos no deben publicarse en git.

Cada fase deberá estar en congruencia con plan.md y workflow.md, así como con el archivo fase1.js, cuya funcionalidad es prioritario emular. Cada fase tendrá su propio archivo plan_fasex.md, que servirá comoplan de trabajo y checklist de avance. 

En cada cambio exitoso, mantén la documentación, el testing y el logging consistentes. Debes hacer commit una vez asegurados estos puntos.

Debes respetar los principios SOLID y KISS y buscar el arreglo en patrones de diseño siempre que sea conveniente, así como las mejores prácticas recomendadas. Debes procurar el performance y la eficiencia. 

Al correr ejecuciones en terminal debes hacer clear antes de ejecutar comandos que arrojen mucha información sobre pantalla.