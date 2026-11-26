# Interfaz de historial municipal

La interfaz HTML/CSS/JavaScript se encuentra en `dist/` y solo muestra datos reales. Para instalar y ejecutar la aplicación completa con API local, consulta el [README del módulo](../../README.md).

La consulta anual incluye municipio, rango de años, tabla de superficies y cambios, mapa y línea de tiempo. Las hectáreas proceden de la cartografía pública MapBiomas; los diagnósticos CDSE se mantienen separados de esas superficies.

Las pruebas se ejecutan desde esta carpeta con `node --test tests/*.test.mjs`. El módulo de reglas conserva casos de demostración y bimestres para comprobar comportamientos internos históricos; esas opciones no están disponibles en la interfaz.
