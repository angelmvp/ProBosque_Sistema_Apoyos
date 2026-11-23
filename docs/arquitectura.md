# Arquitectura

**Monolito modular en capas.** Un solo backend y un solo frontend, organizados en módulos independientes. Los siguientes sprints **agregan módulos o extienden los existentes; no se reestructura la base.**

## Capas del backend (`backend/app`)

```
modulos/     Historias de usuario: rutas HTTP + esquemas + definición del módulo
servicios/   Reglas de negocio y datos compartidos (con sus modelos)
nucleo/      Infraestructura: configuración, base de datos, seguridad, errores, contrato de módulos
semillas/    Datos iniciales (catálogos, roles, usuarios de prueba, demo)
```
Flujo: `ruta (modulos) → servicio (servicios) → modelo/BD`. Dependencias permitidas, **verificadas por `pruebas/test_arquitectura.py`**:

- `modulos` → `servicios` y `nucleo`. **Nunca a otro módulo.**
- `servicios` → `nucleo`. Nunca a `modulos`.
- `nucleo` → nada de negocio.

Si dos módulos necesitan lo mismo, eso va en un **servicio compartido**.

### Servicios compartidos (corresponden al backlog)
| Servicio | Carpeta | Contenido |
|---|---|---|
| SRV-01 Autenticación | `servicios/autenticacion` | usuarios, roles, permisos, sesión |
| SRV-06 Catálogo | `servicios/catalogo` | programas, regiones, municipios, formatos |
| SRV-09 Publicación | `servicios/publicacion` | publicaciones, estados, vigencia |
| SRV-07.2 Bitácora | `servicios/bitacora` | registro de acciones y accesos denegados |
| SRV-03.1 Archivos | `servicios/archivos` | PDFs (almacenamiento local, reemplazable) |
| Base de SRV-03 | `servicios/expedientes` | expediente mínimo (alcance por permiso) |

### Módulos del Sprint 1
`acceso` (HU-01) · `convocatorias` (HU-02 público y HU-03 administración) · `expedientes` y `dictamenes` (mínimos, para demostrar el control por rol).

## Cómo agregar un módulo en un sprint futuro
1. Crear `backend/app/modulos/<nombre>/` con `rutas.py`, `esquemas.py` y `definicion.py`.
2. En `definicion.py` declarar `DEFINICION = DefinicionModulo(clave, nombre, historias, routers, permisos, menu)`.
3. Agregar **una línea** en `backend/app/modulos/__init__.py` (`MODULOS`).
4. Si necesita tablas nuevas: modelo en el servicio correspondiente, importarlo en `app/modelos.py` y `alembic revision --autogenerate`.
5. Asignar sus permisos a los roles en `app/semillas/roles.py`.
6. Frontend: carpeta `src/modulos/<nombre>/` y páginas en `src/app/…`.

`main.py`, el núcleo y el menú **no se tocan**: los routers, permisos y opciones de menú se registran solos desde la definición.

## Permisos y menú
- Cada módulo declara sus **permisos** (`PermisoDef`) y sus **opciones de menú** (`OpcionMenu`, con permiso opcional).
- `GET /api/auth/yo` devuelve el menú ya filtrado por los permisos del rol: el frontend solo pinta lo recibido.
- El mismo contrato declara `bloques_inicio`; `main.py` los agrega al estado de la aplicación y `GET /api/auth/yo` los devuelve ya filtrados por rol.
- Todo endpoint protegido usa `requiere_permiso("<permiso>")`. Si falta: **403 + registro en bitácora** (HU-01-CA-2). El backend siempre decide; el frontend solo oculta.

## Sesión
JWT en cookie `httpOnly` (`sesion_probosque`), renovada en cada petición autenticada → **30 minutos de inactividad** (`MINUTOS_INACTIVIDAD`). Contraseñas con argon2.

## Frontend (`frontend/src`)
- `app/` rutas de Next.js (App Router), delgadas.
- `modulos/<modulo>/` componentes de cada módulo (`acceso`, `convocatorias`).
- `compartido/` cliente de API, tipos, encabezado, protección por sesión/permiso.
- Las llamadas van a `/api/*` en el mismo origen; `next.config.mjs` las reenvía al backend (sin CORS y la cookie funciona).

## Archivos
`servicios/archivos` guarda los PDFs a través de la interfaz `Almacenamiento`. Hoy es disco local (`DIRECTORIO_ARCHIVOS`); migrar a un almacenamiento en la nube es agregar otra clase, sin tocar los módulos.
## Sprint 2

Se agregan los módulos `solicitudes` (HU-04 a HU-06) y `recepcion` (HU-07). Ambos consumen
los servicios compartidos `solicitudes` y `requisitos`; ningún módulo importa otro módulo.
La recepción crea el expediente únicamente cuando acepta una solicitud completa.
