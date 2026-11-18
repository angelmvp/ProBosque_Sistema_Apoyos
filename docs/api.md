# API

Documentación interactiva: <http://localhost:8000/docs>. Errores: `{"codigo": "...", "mensaje": "..."}` con 401 (sin sesión), 403 (sin permiso), 404, 409 (conflicto), 422 (datos inválidos).

## Acceso (HU-01)
| Método y ruta | Descripción |
|---|---|
| `POST /api/auth/ingresar` | `{correo, contrasena}` → sesión (cookie) |
| `POST /api/auth/salir` | Cierra la sesión (204) |
| `GET /api/auth/yo` | Usuario, rol, región, permisos y menú filtrado |

## Portal público (HU-02, sin sesión)
| Ruta | Descripción |
|---|---|
| `GET /api/publico/regiones` · `/municipios?region_id=` | Catálogo para los filtros |
| `GET /api/publico/programas?q=&estado=` | Programas con su estado (`vigente`, `historica`, `sin_convocatoria`) |
| `GET /api/publico/programas/{clave}?municipio_id=` | Detalle: PDF, formatos y delegación del municipio |
| `GET /api/publico/delegacion?municipio_id=` | Delegación de un municipio |
| `GET /api/publico/publicaciones/{id}/pdf` | PDF (solo publicadas) |
| `GET /api/publico/formatos/{clave}` | Formato descargable |

## Publicaciones (HU-03, permiso `publicaciones.gestionar`)
| Ruta | Descripción |
|---|---|
| `GET /api/publicaciones` | Lista (incluye borradores) |
| `POST /api/publicaciones` | Form: `programa, titulo, vigencia_inicio, vigencia_fin, accion=borrador\|publicar, archivo` |
| `GET/PUT/DELETE /api/publicaciones/{id}` | Ver; editar y eliminar **solo borradores** (si no, 409) |
| `POST /api/publicaciones/{id}/publicar` | Publica un borrador (necesita PDF) |
| `GET /api/publicaciones/{id}/pdf` | PDF incluso de borradores |

## Otros
`GET /api/expedientes` (alcance por permiso) · `GET /api/dictamenes` (`dictamenes.ver`) · `GET /api/salud`.
