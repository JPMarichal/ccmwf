---
trigger: always_on
---

# 📌 Instrucciones para generación de pruebas con pytest

## 🔹 Estándares generales
- Todas las pruebas deben escribirse con **pytest**.  
- Los archivos de prueba deben llamarse `test_*.py` y ubicarse en la carpeta `tests/`.  
- Cada prueba debe incluir al menos un **assert relevante**.  
- Evitar asserts triviales como `assert x is not None`.  
- Incluir casos **positivos** y **negativos** (errores, entradas inválidas, ramas alternativas).  
- Priorizar **branch coverage** y funciones críticas antes que pruebas superficiales.  
- Las pruebas deben estar comentadas y documentadas (descripción clara y, de ser posible, referencia al requisito que valida) para facilitar su revisión y comprensión.

---

## 🔹 Orden recomendado de pruebas
Para que las pruebas se construyan de forma lógica y se aprovechen entre sí:

1. **Pruebas unitarias**  
   - Empiezan siempre primero.  
   - Cubren funciones o métodos aislados, sin dependencias externas.  
   - Ejemplo: operaciones matemáticas, validaciones de entrada.  

2. **Pruebas modulares**  
   - Validan un módulo completo (ej. un servicio o clase).  
   - Usar **mocks** para reemplazar dependencias externas.  
   - Ejemplo: un módulo `auth` que depende de un `api`.  

3. **Pruebas de integración**  
   - Validan la interacción de varios módulos juntos.  
   - Ejemplo: `login` + `db` (usando una base en memoria o mock persistente).  

4. **Cobertura de pruebas**  
   - Revisar métricas (`--cov`) después de unitarias e integración.  
   - Priorizar cubrir ramas no ejecutadas y errores no contemplados.  

5. **Pruebas de regresión**  
   - Ejecutar todas las pruebas existentes tras cambios de código.  
   - Garantizan que lo probado antes sigue funcionando.  

6. **Pruebas de humo (opcionales en CI/CD)**  
   - Comprobaciones básicas tras un build o deploy.  
   - Ejemplo: “el servidor levanta” o “la función principal responde”.  

---

## 🔹 Cobertura mínima
Configurar en `pytest.ini`:

```ini
[pytest]
addopts = --cov=src --cov-fail-under=80
testpaths = tests
