# Seguridad del portal

## Controles incluidos
- Contraseñas guardadas con PBKDF2 y sal propia, nunca en texto plano
- Sesión en cookie HttpOnly con SameSite estricto y Secure en la nube, que se invalida al cambiar la contraseña o desactivar el usuario
- Bloqueo de 15 minutos tras 5 intentos fallidos por usuario y dirección, guardado en la base de datos y no en memoria
- Recuperación por correo con enlace de un solo uso que vence en 30 minutos, guardado como hash y límite de 3 solicitudes por hora
- Bitácora de actividad que solo se puede leer y registra inicios de sesión, cargas, borrados, exportaciones y cambios de usuarios
- Roles: admin con control total y cargador que solo agrega datos
- El público solo ve cifras agrupadas y el panel puede apagarse con PUBLIC_ONLY=1
- Sin credenciales en el código y configuración por variables de entorno

## Pendiente para producción en el INE
- Revisión del equipo de informática del INE
- Definir la base de datos y el alojamiento autorizados
- Servidor de correo institucional para la recuperación
- Respaldos diarios de la base de datos y conexión cifrada con sslmode=require
- Valorar doble factor de autenticación para los administradores

## Preguntas para el equipo de informática
1. ¿Qué motor de base de datos usa la institución y dónde se puede alojar?
2. ¿Hay un servidor SMTP institucional para enviar correos?
3. ¿Se exige que los datos queden en servidores propios o en una nube con convenio?
4. ¿Qué política de contraseñas y de respaldos debe cumplir el sistema?
