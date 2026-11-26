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
## Sprint 2

- Los programas habilitados para solicitud en línea son Capturando Carbono, Plantaciones Sustentables y Restauración Hidrológico-Forestal. PSAHEM queda catalogado, pero no se habilita.
- El asistente omite el paso FO-PB-520-B, el programa Guardabosques y HU-08 (correo/plazo de subsanación y notificaciones).
- El folio se asigna al recibir la Delegación; usa consecutivo anual de cinco dígitos. La recepción genera el acuse PDF persistente y el expediente.
- Los archivos de solicitudes aceptan PDF/JPG/PNG, máximo configurable de 10 MB (`TAMANO_MAXIMO_DOCUMENTO_MB`). Publicaciones conservan DOCX/XLSX.
- El backend valida tipo y firma real del archivo; PDF por `%PDF`, JPG por firma JPEG, PNG por firma PNG.
- Condiciones implementadas: identificación/CURP/propiedad para todos; documentos 5 y 6 para núcleo agrario; 7 para sociedad; documento 8 opcional; 9 para RHF; 10 para Capturando Carbono y mantenimiento navideño; 11 permanece no habilitado con PSAHEM.

### Por confirmar con PROBOSQUE / profesor

- Variantes finales del FO-PB-501-A, obligatoriedad legal de campos del 501/502 y representación digital de la firma.
- Confirmar si todos los campos impresos del 502 deben ser obligatorios; en esta versión son opcionales número interior, referencias, teléfono fijo y red social. Ambos apellidos son obligatorios.
- Requisitos adicionales según especie, tipo de persona, refrendo, modalidad o convocatoria; documento 8 se muestra como opcional y no bloquea.
- Comprobante de domicilio cuando la identificación no muestra domicilio; reglas definitivas para refrendos (por ahora no se implementa sustituir anexos por folio).
- El límite/formato de 10 MB es el valor de desarrollo pedido; confirmar límites oficiales y formatos con PROBOSQUE.
- Regla de redondeo y tratamiento de superficies; se exige que los conceptos no excedan superficie total. PSAHEM mantiene año de convenio/observaciones como conceptos no habilitados.
- La pantalla de confirmación muestra el folio pendiente hasta recepción; validar el texto/estado final de acuse con operación.
- Enviar correo y establecer plazo de atención para documentos faltantes pertenecen a HU-08.
