---
trigger: always_on
---

Esta aplicación está bajo git. Deben hacerse commits y pulls cada vez que una tarea esté satisfecha, se alcance un hito o se complete una fase. El mensaje del commit, a pesar de ser breve, debe resumir de manera comprensiva el cambio efectuado. 

Cuando el usuario diga "haz commit" se hará tanto add, commit y pull sobre la rama actual, asegurándose de no enviar archivos de uso temporal, como pruebas o logs temporales que ya no estén en uso. 

El mensaje del commit irá en español, precedido por un prefijo que indique la naturaleza del cambio, como docs:, test:, refactor:, fix:, chore:, feat: o similar. 

Deberás asegurarte de que no hay conflictos o problemas. Si los hay, detenerte y avisar, indicando al usuario el problema y sugiriendo la acción.