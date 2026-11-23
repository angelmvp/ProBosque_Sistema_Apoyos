# Decisiones y pendientes

## Decisiones tomadas
- Frontend React + Next.js; backend FastAPI; PostgreSQL en Docker con pgAdmin; todo local por ahora.
- Todo el código, nombres y documentación en español.
- Solo 4 roles. Región = Delegación Regional Forestal.
- Sesión de 30 minutos de inactividad.
- Una publicación puede contener varios archivos PDF, DOCX o XLSX. Cada archivo tiene tipo y etiqueta visible.
- Formatos descargables en `docs/formatos/` (.docx).
- Sin "masa forestal" ni sistemas externos; los módulos no se llaman entre sí.

## Por confirmar
- Nombres legales reales de los usuarios; las semillas usan personas ficticias identificables.
- Apellidos maternos reales y regla futura de edición de perfil.
- Dominio completo de etiquetas y permisos adicionales que no estén definidos por las HU actuales.
- Domicilio, teléfono y horario de las 9 delegaciones.
- Lista completa de municipios (la entregada es parcial).
- Formato FO-PB-520-B (falta); si el 502 aplica a Guardabosques.
- Fechas del sprint y responsables.
- Contraseñas reales y alta/recuperación de usuarios.

## Límites conocidos del Sprint 1
- Los usuarios y contraseñas son de prueba; la `CLAVE_SECRETA` del compose es de desarrollo.
- Expedientes y dictámenes son marcadores mínimos para demostrar roles.
- Los PDFs se guardan en disco local.
