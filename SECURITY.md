# Consideraciones de Seguridad

Este documento describe cómo protege la Pokédex API las cuentas, los datos y el propio servicio, y qué riesgos quedan abiertos.

> **HTTPS es obligatorio en producción.** Sin él, las contraseñas del login y los JWT viajan en claro y cualquiera en la red podría leerlos y suplantar al usuario. En local se usa HTTP solo para desarrollar.

## Autenticación

**Implementación JWT** (`app/auth.py`, `app/dependencies.py`):

- El login (`POST /api/v1/auth/login`) recibe un formulario OAuth2 y, si las credenciales son correctas, devuelve un JWT firmado con **HS256** y la clave `SECRET_KEY`.
- El token lleva los claims `sub` (nombre de usuario), `user_id`, `iat` (fecha de emisión) y `exp` (caducidad).
- Todos los endpoints privados dependen de `CurrentUser`, que en **cada petición**:
  1. comprueba la firma y la caducidad del token;
  2. comprueba que el usuario sigue existiendo y está activo;
  3. si algo falla, responde `401 Unauthorized` con la cabecera `WWW-Authenticate: Bearer`.
- El login responde con el **mismo mensaje** si el usuario no existe o si la contraseña es incorrecta, para no revelar qué usuarios hay registrados.
- Los intentos de login fallidos y los tokens inválidos quedan registrados en el log.

**Política de expiración de tokens**:

- El token de acceso caduca a las **24 horas** (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`). Pasado ese tiempo hay que volver a hacer login.
- No hay refresh tokens: es una mejora futura (refresh token de 7 días, distinto del de acceso y que no sirva para llamar a la API).
- Como los JWT no se guardan en el servidor, no se pueden revocar antes de caducar. Si se filtra la `SECRET_KEY`, hay que cambiarla: todos los tokens emitidos dejan de ser válidos.

## Contraseñas

**Algoritmo de hashing**: **bcrypt**, usado directamente con `bcrypt.hashpw` y `bcrypt.checkpw` (12 rondas, el valor por defecto).

- Cada contraseña lleva su propia sal aleatoria, así que dos usuarios con la misma contraseña tienen hashes distintos.
- bcrypt es lento a propósito: probar millones de contraseñas contra un hash robado es muy costoso.
- La contraseña en claro **nunca se guarda ni se devuelve**. Solo existe en el contrato de entrada `UserCreate`; la tabla guarda `hashed_password` y el contrato de salida `UserRead` no la incluye.
- No se usa `passlib`: lleva años sin mantenerse y falla con `bcrypt` 5.

**Política de contraseñas** (validada en `UserCreate`):

- Mínimo 8 caracteres.
- Al menos una letra mayúscula.
- Al menos un número.

Si no se cumple, el registro responde `422` explicando qué falta. El email se valida con `EmailStr`, y el nombre de usuario debe tener entre 3 y 50 caracteres.

## Rate Limiting

**Límites por endpoint** (por dirección IP, definidos en `app/limits.py`):

| Endpoints | Límite | Motivo |
|---|---|---|
| `POST /auth/register` | 5/hora | Evita la creación masiva de cuentas |
| `POST /auth/login` | 10/minuto | Frena los ataques de fuerza bruta y de diccionario |
| Endpoints que llaman a la PokeAPI (búsqueda, detalle, `/card`, añadir a la Pokédex, exportar equipo, `/api/v2/pokedex`) | 30/minuto | Cada petición genera otras hacia un servicio externo que también nos limita |
| Resto de endpoints autenticados | 100/minuto | Solo tocan nuestra base de datos; permiten un uso normal |
| `/health` | Sin límite | Lo usa la monitorización |

**Justificación**: los endpoints públicos son los más atacados y los más estrictos; los que dependen de la PokeAPI protegen nuestra cuota en un servicio ajeno; el resto evita que un único cliente sature la API (denegación de servicio). Al superar el límite, la API responde `429 Too Many Requests` y lo registra en el log con la ruta y la IP.

**Limitación conocida**: los contadores viven en memoria. Se reinician al reiniciar la API y no se comparten entre varias instancias. En producción con varias réplicas habría que guardarlos en Redis.

## CORS

**Orígenes permitidos**: solo los de la variable `CORS_ORIGINS` (por defecto `http://localhost:5173`, el servidor de desarrollo de Vite). En producción se añade únicamente el dominio real del frontend.

Además:

- Métodos permitidos: `GET`, `POST`, `PUT`, `PATCH` y `DELETE`.
- Cabeceras permitidas: `Authorization` y `Content-Type`.
- `max_age=3600`: el navegador recuerda la respuesta de la comprobación previa durante una hora.

**Por qué es necesario**: el navegador impide por defecto que una web de otro dominio lea las respuestas de nuestra API (política del mismo origen). CORS indica qué webs concretas sí pueden hacerlo. Con una lista cerrada, una web maliciosa no puede usar el navegador de una víctima para llamar a la API y leer sus datos. Nunca se usa `allow_origins=["*"]`. Los tests comprueban que un origen desconocido se rechaza.

## Variables de Entorno

**Qué información sensible se guarda**:

| Variable | Sensible | Contenido |
|---|---|---|
| `SECRET_KEY` | **Sí** | Firma de los JWT. Quien la tenga puede fabricar tokens de cualquier usuario |
| `DATABASE_URL` | **Sí** en producción | En PostgreSQL incluye usuario y contraseña de la base de datos |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Configuración de los JWT |
| `CORS_ORIGINS`, `POKEAPI_*` | No | Configuración del servicio |

**Cómo protegerla**:

- Los valores reales van en `.env`, que está en `.gitignore` y **nunca** se sube al repositorio. Un `.env` subido por error queda en el historial aunque se borre después, así que habría que cambiar todas las claves.
- El repositorio incluye `.env.example` con los nombres de las variables y valores de ejemplo, nunca reales.
- `SECRET_KEY` no tiene valor por defecto: si falta, la API no arranca, en lugar de arrancar con una clave insegura. Se genera con `python -c "import secrets; print(secrets.token_urlsafe(32))"`, una distinta por entorno.
- El CI usa una clave de pruebas (`clave-solo-para-ci`) que no sirve en ningún otro sitio.
- En producción, las variables se configuran en el panel de la plataforma de despliegue o en los *secrets* de GitHub, nunca en el código.

## Vulnerabilidades Conocidas

### OWASP API Security Top 10 (2023) consideradas

| Riesgo | Mitigación implementada |
|---|---|
| **API1 · Broken Object Level Authorization** | Cada consulta de la Pokédex y de los equipos filtra por el usuario del token. Las entradas y equipos de otro usuario responden `404` (no `403`), para no confirmar que existen. Al crear un equipo se comprueba que todos los Pokémon están en la Pokédex del usuario. Hay tests específicos para cada caso. |
| **API2 · Broken Authentication** | bcrypt con sal, política de contraseñas, JWT firmados y con caducidad, validación del token y del usuario en cada petición, mismo mensaje de error en el login y rate limiting en registro y login. |
| **API3 · Broken Object Property Level Authorization** | Contratos de entrada y salida separados. `UserRead` no expone `hashed_password`. `PokedexEntryUpdate` solo permite cambiar mote, notas, captura, fecha y favorito: no se puede cambiar el dueño ni el Pokémon. |
| **API4 · Unrestricted Resource Consumption** | Rate limiting por tipo de endpoint, paginación con `limit` máximo (100 en la Pokédex y 50 en la búsqueda), equipos de 6 Pokémon como máximo, longitudes máximas en los textos, timeout en las llamadas a la PokeAPI y caché acotada. |
| **API5 · Broken Function Level Authorization** | No hay funciones de administración. Todos los endpoints, salvo registro, login y `/health`, exigen `CurrentUser`. |
| **API6 · Unrestricted Access to Sensitive Business Flows** | El registro está limitado a 5 por hora y por IP. |
| **API7 · Server Side Request Forgery** | La API solo llama a la URL fija de la PokeAPI (`POKEAPI_BASE_URL`). Lo que envía el usuario se valida antes (ids numéricos y nombres `[a-z0-9-]`), así que no puede dirigir peticiones a otras direcciones. |
| **API8 · Security Misconfiguration** | CORS con lista cerrada de orígenes y métodos, `SECRET_KEY` obligatoria, `.env` fuera del repositorio. Los errores controlados usan un formato único (`{"detail": ...}`, también el 429) y un error inesperado responde `500` sin mostrar trazas internas. |
| **API9 · Improper Inventory Management** | Versionado explícito (`/api/v1`, `/api/v2`), documentación automática en `/docs` y estrategia de retirada de versiones descrita en el README. |
| **API10 · Unsafe Consumption of APIs** | Las respuestas de la PokeAPI se validan y se reducen a los campos necesarios. Sus errores se traducen a `404`, `502` o `504` controlados, y los textos que se escriben en los PDF se depuran. |

### Otras mitigaciones

- **Inyección SQL**: todas las consultas usan SQLModel con parámetros. El campo de orden (`sort`) se traduce a una columna desde una lista cerrada y nunca se inserta texto del usuario en el SQL.
- **Inyección de fórmulas en CSV**: la exportación escapa las celdas que empiezan por `=`, `+`, `-` o `@`, para que Excel no las ejecute.
- **Datos sensibles en los logs**: los errores de validación se registran sin los valores recibidos, para no guardar contraseñas en `pokedex_api.log`.
- **Dependencias**: versiones fijadas en `uv.lock`, revisadas al actualizar.

### Riesgos abiertos

- Los JWT no se pueden revocar antes de su caducidad (no hay lista de bloqueo ni logout en servidor).
- Los contadores del rate limiting están en memoria (ver «Rate Limiting»).
- Detrás de un proxy inverso, la IP que ve la API es la del proxy: habría que configurar las cabeceras `X-Forwarded-For` de confianza para que los límites sigan siendo por cliente.
- No hay cabeceras de seguridad HTTP adicionales (`Strict-Transport-Security`, `Content-Security-Policy`…); se añadirían en el proxy o servidor HTTPS de producción.

## Cómo informar de una vulnerabilidad

Si encuentras un fallo de seguridad, no abras una issue pública: escribe directamente a los miembros del equipo indicados en el README.
