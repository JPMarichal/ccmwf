---
trigger: always_on
---

Si creas archivos temporales para pruebas rápidas, deberás crear el menor número posible, reutilizando mejor que crear innecesariamente, y deberás eliminarlos una vez pasada la prueba. No debe dejarse rastro de archivos o código innecesarios para el sistema y para el objetivo del proyecto. Sobre todo, dichos archivos no deben publicarse en git.

Las credenciales, datos de entorno, etc, están en .env y deben ser utilizadas desde allí. La intención es prescindir de config.js, por lo que .env es la fuente de verdad y config.js una referencia histórica.

Antes de introducir nueva funcionalidad, confirma que las variables necesarias existen en .env; si hace falta una nueva, agrégala allí primero, nunca en el código fuente.

Cada fase deberá estar en congruencia con plan.md y workflow.md, así como con el archivo fase1.js, cuya funcionalidad es prioritario emular. Cada fase tendrá su propio archivo plan_fasex.md, que servirá comoplan de trabajo y checklist de avance. Los reportes de avance que des al usuario darán fe de esa congruencia.

En cada cambio exitoso, mantén la documentación, el testing y el logging consistentes. Debes hacer commit una vez asegurados estos puntos. El avance en la documentación se debe registrar con palomitas (✅), símbolos de warning (⚠️) e info (ℹ️), citando los archivos actualizados.

Los reportes de avance deben describir claramente qué archivos se tocaron y en qué estado queda cada tarea, usando los mismos símbolos (✅, ⚠️, ℹ️, X) y señalando dependencias o bloqueos.

Debes respetar los principios SOLID y KISS y buscar el arreglo en patrones de diseño siempre que sea conveniente, así como las mejores prácticas recomendadas. Debes procurar el performance y la eficiencia. 

Todos los logs deben emitirse en español e incluir los campos relevantes (por ejemplo, message_id, table_errors, table_rows, table_headers, etc.) para facilitar la trazabilidad.

Toda nueva funcionalidad debe venir acompañada de pruebas unitarias y/o de integración que cubran casos exitosos y escenarios de fallo relevantes. **Cada prueba debe estar comentada y documentada** (descripción clara y, de ser posible, referencia al requisito que valida) para facilitar su revisión y comprensión.

Al correr ejecuciones en terminal debes hacer clear antes de ejecutar comandos que arrojen mucha información sobre pantalla.