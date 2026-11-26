# API

Documentación interactiva: <http://localhost:8000/docs>. Errores: `{"codigo": "...", "mensaje": "..."}` con 401 (sin sesión), 403 (sin permiso), 404, 409 (conflicto), 422 (datos inválidos).

## Acceso (HU-01)
| Método y ruta | Descripción |
|---|---|
| `POST /api/auth/ingresar` | `{correo, contrasena}` → sesión (cookie) |
| `POST /api/auth/salir` | Cierra la sesión (204) |
| `GET /api/auth/yo` | Usuario, rol, región, permisos y menú filtrado |
| Perfil | `nombre`, `apellido_paterno`, `apellido_materno`, `nombre_completo`, correo, rol, región/delegación, permisos, menú y bloques |
| Inicio | `bloques` contiene solo las tarjetas permitidas para el rol |

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
| `GET/DELETE/PATCH /api/publicaciones/{id}/archivos/{archivo_id}` | Descargar, quitar o cambiar tipo/etiqueta de un archivo de borrador |
| `POST /api/publicaciones/{id}/publicar` | Publica un borrador (necesita PDF) |
| `GET /api/publicaciones/{id}/pdf` | Visor de la convocatoria PDF, incluso de borradores |
| Públicos `/api/publico/publicaciones/{id}/archivos/{archivo_id}` | Sirve PDF en línea y DOCX/XLSX como descarga |

## Otros
`GET /api/expedientes` (alcance por permiso) · `GET /api/dictamenes` (`dictamenes.ver`) · `GET /api/salud`.
## Solicitudes y recepción (Sprint 2)

- `GET/POST /api/solicitudes`: lista solicitudes propias / crea borrador con `programa_id` y `municipio_id`.
- `GET/PUT /api/solicitudes/{id}`: consulta propia / guarda bloques parciales `datos_501`, `datos_502` y `aviso_privacidad`.
- `GET /api/solicitudes/catalogos/programas`, `/municipios`, `/conceptos?programa=`: opciones disponibles para el asistente.
- `POST /api/solicitudes/{id}/pasos/{1..5}/validar`: valida el paso antes de avanzar.
- `GET /api/solicitudes/{id}/resumen`: estados de los pasos 1–4 y si el expediente puede enviarse.
- `GET /api/solicitudes/{id}/requisitos`: checklist numerado y filtrado por programa/tipo de persona, incluidos metadatos de archivo.
- `POST /api/solicitudes/{id}/documentos`: multipart `requisito` + `archivo` (PDF/JPG/PNG, hasta 10 MB por defecto).
- `DELETE /api/solicitudes/{id}/documentos/{requisito}` y `GET /api/solicitudes/{id}/documentos/{requisito}/archivo`: reemplazo mediante nueva carga, quitar y ver/descargar.
- `POST /api/solicitudes/{id}/enviar`: revalida 501/502 y checklist obligatorio, registra envío y bitácora.
- `GET /api/solicitudes/{id}/acuse`: descarga el acuse persistente cuando la solicitud ya fue recibida.
- `GET /api/recepcion/solicitudes?programa=&estado=&municipio=&fecha_desde=&fecha_hasta=`: bandeja de solicitudes de la región autenticada.
- `GET /api/recepcion/solicitudes/{id}`: datos 501/502 y documentos de solicitudes dentro de la región.
- `GET /api/recepcion/solicitudes/{id}/documentos/{requisito}/archivo`: ver/descargar documento desde recepción.
- `POST /api/recepcion/solicitudes/{id}/recibir`: recibe `{solicitud_completa, documentos_legibles, corresponden_al_programa, observacion, faltantes:[{requisito,observacion}]}`. Si está completa, crea folio, expediente y acuse; si faltan documentos, conserva `con_faltantes` sin folio/acuse.
- `GET /api/recepcion/solicitudes/{id}/acuse/archivo`: vista/descarga del PDF.

Todos los errores 422 incluyen `{"codigo":"datos_invalidos","mensaje":"...","campos":[{"campo":"...","mensaje":"..."}]}`. Las rutas privadas verifican propietario o región en backend.
