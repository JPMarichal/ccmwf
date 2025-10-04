---
trigger: always_on
---

El trabajo en un issue comienza cuando el usuario dice algo como "Comienza a trabajar con el issue XX", donde XX representa el número de issue en github. Previamente, el usuario ha abierto ese issue en github y ha creado la rama correspondiente, con un nombre como JPMarichal/issueXX . 

Lo primero que procede es leer el issue en github y, entonces, hacer un análisis suficiente para generar, a continuación, el plan de trabajo a seguir, dividido en pasos funcionales, criterios de aceptación propios y entregables. Después de obtener la aprobación del usuario sobre ese plan, se debe seguir paso a paso, en forma ininterrumpida y, hasta donde sea posible, desatendida, solicitando la atención del usuario solamente en puntos críticos. 

El trabajo termina cuando todo el plan se ha seguido, los criterios de aceptación se han cumplido, todo ha sido probado y documentado, se ha dado un reporte final y se ha validado que no hay pendientes. Una vez obtenida la aprobación del usuario, se procede a crear el pull request en github, con el usuario JPMarichal como asignado y los tags que correspondan. 

Tan pronto el usuario confirme que se ha hecho merge del pull request en github, debes cerrar el issue en github, antes de regresar a la rama main tanto en remoto como en local. Una vez en main se hace git fetch y git pull en la rama main para traer los últimos cambios. Se eliminan ramas locales innecesarias, considerando innecesarias aquellas que tienen muy poca probabilidad de utilizarse nuevamente. Con esto se concluye el trabajo con el issue.