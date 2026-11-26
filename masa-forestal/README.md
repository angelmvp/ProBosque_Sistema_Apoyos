# Masa forestal · Historial municipal

Entrega de avance de HU-MAF-01: consulta anual de superficie forestal y cambios para los 125 municipios del Estado de México. Incluye búsqueda municipal, mapa interactivo, tabla de superficies, línea de tiempo y fuentes. La interfaz utiliza únicamente datos reales.

Este módulo se ejecuta por separado del portal de apoyos. Sirve su propia interfaz HTML/CSS/JavaScript y una API Python en `http://127.0.0.1:4173/`. No necesita arrancar el Docker Compose del proyecto principal, instalar PostgreSQL ni compilar el frontend.

## Instalar y ejecutar en Windows

Requisitos: Git y Python **3.12** de [python.org](https://www.python.org/downloads/). Internet se necesita para descargar el proyecto, instalar las dependencias y actualizar CDSE.

Clona la rama y entra al módulo:

```powershell
git clone --branch masa-forestal-sprint1 --single-branch https://github.com/angelmvp/ProBosque_Sistema_Apoyos.git
cd ProBosque_Sistema_Apoyos
cd masa-forestal
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-geospatial.txt
```

Inicia el servidor:

```powershell
.\.venv\Scripts\python.exe server/http_server.py
```

Abre **http://127.0.0.1:4173/**. Mantén la terminal abierta y detén el servidor con **Ctrl+C**. Si el puerto está ocupado, utiliza `server/http_server.py --port 4174` y abre el puerto elegido.

También puedes ejecutar `./iniciar-web.ps1` después de crear el entorno. Si PowerShell bloquea el script, utiliza el comando directo de Python anterior; no necesitas cambiar la política de ejecución.

Si ya tienes una copia de este repositorio, con los cambios locales guardados, entra a su carpeta y ejecuta `git fetch origin`, `git switch masa-forestal-sprint1` y `git pull --ff-only origin masa-forestal-sprint1`; luego entra a `masa-forestal` y sigue la instalación del entorno.

## Credenciales CDSE (opcional para consultar el historial)

**Consultar historial** lee los datos públicos incluidos y funciona sin credenciales de CDSE. **Actualizar CDSE** consulta el catálogo y la calidad de observaciones Sentinel; requiere un cliente OAuth de servidor de [Copernicus Data Space](https://shapps.dataspace.copernicus.eu/dashboard/).

Para configurar ese cliente, copia la plantilla si todavía no tienes `.env`:

```powershell
Copy-Item .env.example .env
```

Completa en ese archivo `CDSE_CLIENT_ID` y `CDSE_CLIENT_SECRET`. No uses tu contraseña de CDSE. El servidor también admite esas variables de entorno. Las credenciales se leen en el servidor y no se entregan al navegador. `.env` queda excluido de Git; no lo subas ni lo incluyas en capturas.

La primera ejecución crea una base SQLite y cachés locales en `data/servidor/`. Cada computadora guarda sus propios diagnósticos y trabajos; Git no los sincroniza. Las solicitudes a CDSE pueden consumir la cuota de la cuenta configurada.

## macOS y Linux

Con Python 3.12 instalado, desde la carpeta `masa-forestal`:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-geospatial.txt
.venv/bin/python server/http_server.py
```

Para CDSE, crea `.env` a partir de `.env.example` y completa sus valores localmente. La instalación y las pruebas de esta entrega se verifican en Windows con Python 3.12; los comandos de macOS/Linux no implican una comprobación en esos sistemas.

## Datos y alcance

- **Superficie:** hectáreas de las clases bosque templado, tropical seco, tropical húmedo y manglar de MapBiomas México, Colección 1. Se excluyen cultivos y plantaciones. La serie visible comprende 2017–2025 e incluye internamente 2016 como referencia para el primer cambio.
- **Cambios:** diferencias entre superficies cartografiadas de años consecutivos. No equivalen por sí solas a una medición validada de deforestación o recuperación.
- **Mapa:** límites municipales INEGI de diciembre de 2025, simplificados para visualización. El color muestra una proporción municipal, no píxeles clasificados de bosque. El límite territorial de MapBiomas puede diferir del límite INEGI.
- **Sentinel:** revisión de catálogo y calidad SCL mediante CDSE para los 125 municipios, en años completos desde 2017. No produce las hectáreas mostradas. El clasificador forestal propio permanece sin validación suficiente; las cifras conservan su atribución MapBiomas.
- **Integridad:** se verifican origen, unidades, clases, sumas, municipios y huellas SHA-256. Esta comprobación técnica no certifica exactitud forestal local. No edites ni reformatees los archivos de datos incluidos; sus bytes se conservan mediante `.gitattributes`.

Fuentes: [Proyecto MapBiomas México](https://mexico.mapbiomas.org/) (Colección 1, CC-BY), [Marco Geoestadístico de INEGI](https://www.inegi.org.mx/temas/mg/) y [Sentinel-2 L2A de CDSE](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html). Se conservan procedencia, fechas de consulta y manifiestos junto a los datos. Los resultados del piloto incluidos son diagnósticos históricos, no una clasificación forestal validada.

## Comprobaciones

Desde `masa-forestal`, con el entorno instalado:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Las pruebas del servidor, cartografía y operación usan bases temporales y proveedores de prueba; no requieren credenciales ni consumen la API CDSE. Para las pruebas JavaScript, instala Node.js y ejecuta:

```powershell
node --test web/prototipo/tests/*.test.mjs
```

Node.js solo se necesita para esas pruebas. El funcionamiento de la página usa JavaScript del navegador.

## Archivos del módulo

- `web/prototipo/dist/`: interfaz y copia pública de datos.
- `server/`: API local, cartografía, trabajos, caché y control de solicitudes.
- `scripts/`: cliente CDSE y cálculo de calidad temporal requeridos por el servidor.
- `config/`: metodología y límites operativos.
- `data/`: fuentes públicas y diagnósticos históricos necesarios para el arranque y las comprobaciones.
- `tests/`: pruebas de la aplicación incluida.

Este paquete no incluye modelos ni todos los experimentos de investigación del proyecto original. El dictamen histórico guardado en `data/piloto/validacion/` conserva referencias a evidencias de investigación que no forman parte de esta entrega; el servidor solo utiliza de él la huella de la metodología para reconocer los diagnósticos importados.

El servidor escucha únicamente en la computadora local. Subir esta rama a GitHub distribuye el código y los datos; no publica automáticamente un servicio web en Internet.
