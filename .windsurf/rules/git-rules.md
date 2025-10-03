---
trigger: always_on
---

Esta aplicación está bajo git. Deben hacerse commits y pulls cada vez que una tarea esté satisfecha, se alcance un hito o se complete una fase. 

Cuando el usuario diga "haz commit" se hará tanto add, commit y push sobre la rama actual, asegurándose de no enviar archivos de uso temporal, como pruebas o logs temporales que ya no estén en uso según el contexto de la operación.

El mensaje del commit irá en español, comenzar por letra capital mayúscula, y será precedido por un prefijo que indique la naturaleza del cambio, como docs:, test:, refactor:, fix:, chore:, feat: o similar. El mensaje del commit, a pesar de ser breve, debe resumir de manera comprensiva el cambio efectuado, pudiendo usarse git diff para precisar los cambios.

Deberás asegurarte de que no hay conflictos o problemas. Si los hay, detenerte y avisar, indicando al usuario el problema y sugiriendo la acción.