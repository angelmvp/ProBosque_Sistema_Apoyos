# PROBOSQUE · Sistema de apoyos forestales

Sistema web para gestionar los programas de apoyo forestal de PROBOSQUE (Estado de México): consulta de convocatorias, publicación de reglas y acceso por rol. **Proyecto universitario, Sprint 1 (HU-01, HU-02 y HU-03).**

**Tecnologías:** FastAPI (Python) · Next.js + React (TypeScript) · PostgreSQL 16 · pgAdmin · Docker.

## Qué incluye el Sprint 1

| Historia | Qué hace | Documento |
|---|---|---|
| HU-01 | Autenticación y 4 roles (sesión de 30 min de inactividad, acceso denegado y bitácora) | [docs/hu-01.md](docs/hu-01.md) |
| HU-02 | Portal de convocatorias con filtros de región/municipio y documentos etiquetados | [docs/hu-02.md](docs/hu-02.md) |
| HU-03 | Gestión de publicaciones (borrador → publicar; lo publicado no se modifica) | [docs/hu-03.md](docs/hu-03.md) |

## Cómo correrlo en tu computadora (Windows o Mac)

### 1. Instalar (una sola vez)
- **Docker Desktop** (Windows y Mac): <https://www.docker.com/products/docker-desktop/>
  - En Windows, Docker Desktop pide **WSL 2**; el instalador lo activa. Reinicia si te lo pide.
- **Git**.

No necesitas instalar Python, Node ni PostgreSQL: todo corre en contenedores.

### 2. Clonar y levantar
```bash
git clone <URL-de-tu-repositorio> probosque-sistema-apoyos
cd probosque-sistema-apoyos
docker compose up --build
```
La primera vez tarda unos minutos. Funciona **sin crear ningún `.env`**. Cuando veas `Application startup complete` en el backend, abre:

| Qué | Dirección |
|---|---|
| Sistema (portal) | <http://localhost:3000> |
| API y documentación interactiva | <http://localhost:8000/docs> |
| pgAdmin | <http://localhost:5050> (usuario `admin@probosque.test`, contraseña `admin`) |
| PostgreSQL | `localhost:5432` · usuario/contraseña/base: `probosque` |

En pgAdmin el servidor "PROBOSQUE (local)" ya aparece; pide la contraseña `probosque`.

Para apagar: `Ctrl+C` y luego `docker compose down`. Para **borrar también los datos**: `docker compose down -v`.

### 3. Usuarios de prueba
Contraseña de todos (solo desarrollo): `Probosque2026!`

| Rol | Correo | Qué puede hacer |
|---|---|---|
| Persona solicitante | `solicitante@probosque.test` | Sofía Solicitante Prueba; consultar convocatorias |
| Delegación Regional Forestal (Toluca) | `delegacion.toluca@probosque.test` | Daniel Delegación Toluca; expedientes de su región |
| Dirección General de PROBOSQUE | `direccion.general@probosque.test` | Gabriela Dirección General; publicar convocatorias y consultar todos los expedientes |
| Dirección de Restauración y Fomento Forestal | `direccion.restauracion@probosque.test` | Raúl Restauración Forestal; dictámenes y todos los expedientes |

Prueba de acceso denegado (HU-01): entra como solicitante y abre <http://localhost:3000/dictamenes>.

Los datos de demostración (3 convocatorias y 3 expedientes ficticios) se cargan solos. Para desactivarlos: copia `.env.ejemplo` a `.env` y pon `CARGAR_DATOS_DEMO=false`.

## Correr las pruebas
Con el sistema levantado:
```bash
docker compose exec backend pytest -q
```
Hay una prueba por cada criterio de aceptación (HU-01-CA-1 … HU-03-CA-2), pruebas de validaciones y **pruebas de arquitectura** que impiden romper la estructura (por ejemplo, que un módulo importe a otro). Usan una base separada (`probosque_pruebas`), nunca la de desarrollo.

## Estructura del repositorio
```
backend/    API FastAPI (núcleo, servicios compartidos, módulos, semillas, migraciones, pruebas)
frontend/   Next.js (src/app = rutas; src/modulos = por módulo; src/compartido = común)
docs/       Documentación + formatos descargables (docs/formatos/*.docx)
docker/     Configuración de pgAdmin
docker-compose.yml
```

## Documentación
- [Arquitectura y cómo extenderla](docs/arquitectura.md) ← **empieza aquí**
- [Base de datos](docs/base-de-datos.md) · [API](docs/api.md) · [Decisiones y pendientes](docs/decisiones.md) · [Cómo contribuir](docs/contribuir.md)
- [Matriz de roles](docs/matriz-de-roles.xlsx)

## Problemas frecuentes
- **El puerto 5432/3000/8000/5050 ya está en uso:** cierra el programa que lo usa o cambia el puerto izquierdo en `docker-compose.yml`.
- **Windows: error `exec ./entrada.sh: no such file`:** el archivo quedó con saltos de línea CRLF. El repo trae `.gitattributes` para evitarlo; si ya clonaste, ejecuta `git rm --cached -r . && git reset --hard`.
- **Cambié algo y no se ve:** backend y frontend recargan solos; si cambiaste dependencias usa `docker compose up --build`.
